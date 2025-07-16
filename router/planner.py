'''
planner.py - This module contains the logic for planning tasks.

We aim to build a queue of tasks that need to be executed, each task may or may not be dependent on the output of previous tasks.
This planner will use LLMs that will identify the tools/MCP servers that will be connected to based on the metadata of the task.
'''

from .model import Metadata, ExecutionPlan, ToolTask
from typing import List
from utility.LLM import LLMClient
import json

class Planner:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        self.llm_client = LLMClient(model=model)

    def build_plan(self, metadata: Metadata) -> ExecutionPlan:
        system_prompt = "You are a planning assistant for an AI agent that routes user queries to tools. Your job is to plan a sequence of tasks that will be executed to answer the user's query. "

        user_prompt = f"""
                        Given this metadata:
                        {metadata.model_dump_json(indent=2)}
                        
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
        try:
            print("Generating execution plan...")
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
            raise RuntimeError(f"LLM Planner failed: {e}")
