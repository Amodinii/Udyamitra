'''
planner.py - This module contains the logic for planning tasks.

We aim to build a queue of tasks that need to be executed, each task may or may not be dependent on the output of previous tasks.
This planner will use LLMs that will identify the tools/MCP servers that will be connected to based on the metadata of the task.
'''

import json
import sys
from utility.model import Metadata, ExecutionPlan, ToolTask, ConversationState
from typing import List
from utility.LLM import LLMClient
from Logging.logger import logger
from Exception.exception import UdayamitraException

from dotenv import load_dotenv
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
                print(f"Last entities in state manager: {last_entities}")
                context_hint = f"""
                Previous tool used: {last_tool}
                Last assistant message: {last_msg}
                Previously detected entities (if any): {json.dumps(last_entities)}
                Use this context if the current query is ambiguous or a follow-up.
                """
            system_prompt = "You are a planning assistant for an AI agent that routes user queries to tools. Your job is to plan a sequence of tasks that will be executed to answer the user's query."
            print(f"State in planner: {state}")
            user_prompt = f"""
            Given this metadata:
            {metadata.model_dump_json(indent=2)}
            {"\nConversation history:\n" + context_hint if state else ""}
            
            Generate an execution plan that includes:
            - The type of execution (sequential or parallel)
                - Sequential: Tasks are executed one after another, specifically if one task depends on the output of another
                - Parallel: Tasks can be executed simultaneously
            - The list of tasks that need to be executed
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
            Just return the JSON without any commentary.
            """

            logger.info("Generating execution plan...")
            plan_dict = self.llm_client.run_json(system_prompt, user_prompt)
            task_list: List[ToolTask] = []
            for task in plan_dict["tasks"]:
                task_list.append(
                    ToolTask(
                        tool_name=task["tool"],
                        input=task["input"],
                        input_from=task.get("input_from")
                    )
                )

            return ExecutionPlan(
                execution_type=plan_dict["execution_type"],
                task_list=task_list
            )
        except Exception as e:
            logger.error(f"Failed to build execution plan: {e}")
            raise UdayamitraException(f"Planner failed: {e}", sys)