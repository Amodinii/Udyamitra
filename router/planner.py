import json
import re
import sys
from typing import List
from dotenv import load_dotenv

from utility.model import Metadata, ExecutionPlan, ToolTask, ConversationState
from utility.LLM import LLMClient
from router.ToolExecutor import safe_json_parse
from Logging.logger import logger
from Exception.exception import UdayamitraException

load_dotenv()

class Planner:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        try:
            logger.info(f"Initializing Planner with model: {model}")
            self.llm_client = LLMClient(model=model)
        except Exception as e:
            logger.error(f"Failed to initialize Planner: {e}")
            raise UdayamitraException("Failed to initialize Planner", sys)

    def build_plan(self, metadata: Metadata, state: ConversationState | None = None) -> ExecutionPlan:
        try:
            logger.info(f"Building execution plan for metadata: {metadata}")
            context_hint = ""

            if state:
                last_tool = state.last_tool_used or ""
                last_msg = state.messages[-1].content if state.messages else ""
                last_entities = state.context_entities or {}

                context_hint = f"""
Conversation History:
- Previous tool used: {last_tool}
- Last assistant message: {last_msg}
- Previously detected entities: {json.dumps(last_entities, indent=2)}
Use this context if the current query is ambiguous or a follow-up.
""".strip()

            user_prompt = f"""
Given the following metadata:
{metadata.model_dump_json(indent=2)}

{context_hint}

Generate an execution plan that includes:
- The type of execution (sequential or parallel)
- The list of tasks that need to be executed in this JSON format:

{{
  "execution_type": "sequential",
  "tasks": [
    {{
      "tool": "ToolName",
      "input": {{ ... }},
      "input_from": "OptionalPreviousTool"
    }}
  ]
}}

Only return a valid JSON object, no explanation.
Make sure all keys are enclosed in double quotes and properly comma-separated.
""".strip()

            system_prompt = "You are a planning assistant for an AI agent that routes user queries to tools."

            raw_output = self.llm_client.run_chat(system_prompt, user_prompt)
            logger.info(f"Raw output from LLM:\n{raw_output}")

            # using safe_json_parse to handle invalid JSON
            plan_dict = safe_json_parse(raw_output)

            logger.info(f"Parsed execution plan:\n{json.dumps(plan_dict, indent=2)}")

            task_list: List[ToolTask] = [
                ToolTask(
                    tool_name=task["tool"],
                    input=task["input"],
                    input_from=task.get("input_from")
                )
                for task in plan_dict["tasks"]
            ]

            return ExecutionPlan(
                execution_type=plan_dict["execution_type"],
                task_list=task_list
            )

        except Exception as e:
            logger.error(f"Failed to build execution plan: {e}")
            raise UdayamitraException(f"Planner failed: {e}", sys)