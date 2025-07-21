import sys
import json
import asyncio
from typing import Dict, Any
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from utility.model import ExecutionPlan, ToolTask, ToolRegistryEntry
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.register_tools import load_registry_from_file


class ToolExecutor:
    def __init__(self):
        try:
            logger.info("Initializing ToolExecutor")
            self.tool_registry: Dict[str, ToolRegistryEntry] = load_registry_from_file()
            if not self.tool_registry:
                raise UdayamitraException("Tool registry is empty. Ensure tools are registered properly.", sys)
        except Exception as e:
            logger.error(f"Failed to initialize ToolExecutor: {e}")
            raise UdayamitraException("Failed to initialize ToolExecutor", sys)

    @asynccontextmanager
    async def connect_to_server_for_tool(self, tool_name: str):
        """
        Connects to the MCP server endpoint for the given tool, using context managers.
        """
        if tool_name not in self.tool_registry:
            raise UdayamitraException(f"Tool '{tool_name}' not found in registry.", sys)

        endpoint = self.tool_registry[tool_name].endpoint
        logger.info(f"Connecting to MCP server at {endpoint} for tool '{tool_name}'")

        async with streamablehttp_client(url=endpoint) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                logger.info("Initializing MCP session...")
                await session.initialize()
                logger.info(f"MCP session initialized successfully for endpoint {endpoint}")
                yield session

    async def get_required_inputs(self, session: ClientSession, tool_name: str) -> dict:
        try:
            response = await session.list_tools()
            for tool in response.tools:
                return {"server_Tool": tool.name, "required_input": tool.inputSchema.get("required", [])}
            logger.warning(f"Tool '{tool_name}' not found in list_tools response.")
            return {"server_Tool": None, "required_input": []}
        except Exception as e:
            logger.error(f"Failed to fetch input schema for tool '{tool_name}': {e}")
            return {"server_Tool": None, "required_input": []}

    def _resolve_input(self, task: ToolTask, previous_outputs: Dict[str, Any]) -> Dict[str, Any]:
        if task.input_from:
            referenced_output = previous_outputs.get(task.input_from)
            if not referenced_output:
                raise UdayamitraException(
                    f"No output found from '{task.input_from}' to resolve input for '{task.tool_name}'", sys
                )
            return {
                "output_text": referenced_output.get("output_text")
            }
        return task.input

    def _prompt_for_missing_inputs(self, required_keys: list, provided_input: dict, tool_name: str) -> dict:
        for input_name in required_keys:
            if input_name not in provided_input:
                logger.warning(f"Missing required input '{input_name}'. Prompting user...")
                user_input = input(f"\nInput required for tool '{tool_name}': please enter value for '{input_name}': ")
                try:
                    provided_input[input_name] = json.loads(user_input)
                except json.JSONDecodeError:
                    provided_input[input_name] = user_input
        return provided_input

    async def run_execution_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """
        Executes the given execution plan (only sequential supported).
        """
        results: Dict[str, Any] = {}

        if plan.execution_type != "sequential":
            raise UdayamitraException(f"Execution type '{plan.execution_type}' not supported yet.", sys)

        for task in plan.task_list:
            async with self.connect_to_server_for_tool(task.tool_name) as session:
                try:
                    required_inputs = await self.get_required_inputs(session, task.tool_name)
                    input_data = self._resolve_input(task, results)
                    full_input = self._prompt_for_missing_inputs(required_inputs["required_input"], input_data, task.tool_name)

                    logger.info(f"Calling tool '{task.tool_name}' with input: {full_input}")
                    response = await session.call_tool(required_inputs["server_Tool"], full_input)

                    logger.info(f"Tool '{task.tool_name}' executed successfully.")
                    output_text = None
                    if hasattr(response, "content") and response.content:
                        output_text = response.content[0].text

                    results[task.tool_name] = {
                        "tool": task.tool_name,
                        "output_text": output_text,
                        "raw_output": response.model_dump() if hasattr(response, "model_dump") else str(response),
                    }
                except Exception as e:
                    logger.error(f"Error calling tool '{task.tool_name}': {e}")
                    results[task.tool_name] = {"tool": task.tool_name, "error": str(e)}

        return results


# Final run function
async def run_plan(plan_dict: dict) -> Dict[str, Any]:
    """
    Takes raw plan dict, converts to ExecutionPlan model, and runs it.
    """
    try:
        tasks = []
        for t in plan_dict.get("tasks", []):
            task = ToolTask(
                tool_name=t["tool"],
                input=t.get("input", {}),
                input_from=t.get("input_from")
            )
            tasks.append(task)

        plan = ExecutionPlan(
            execution_type=plan_dict.get("execution_type", "sequential"),
            task_list=tasks
        )

        executor = ToolExecutor()
        return await executor.run_execution_plan(plan)

    except Exception as e:
        logger.error(f"Failed to run plan: {e}")
        raise