import sys
import json
import asyncio
from typing import Dict, Any
from pydantic import BaseModel
from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from router.ModelResolver import ModelResolver
from router.SchemaGenerator import SchemaGenerator
from utility.model import ExecutionPlan, ToolTask, ToolRegistryEntry, Metadata
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
            self.resolver = ModelResolver("utility.model")
            self.schema_generator = SchemaGenerator()
            logger.info("ToolExecutor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ToolExecutor: {e}")
            raise UdayamitraException("Failed to initialize ToolExecutor", sys)

    def _get_schema(self, tool_schema_name: str):
        try:
            logger.info(f"Resolving schema: {tool_schema_name}")
            model_class = self.resolver.resolve(tool_schema_name)
            logger.info(f"Resolved class: {model_class.__name__}")
            assert issubclass(model_class, BaseModel)
            return model_class  # MUST return the resolved class
        except Exception as e:
            logger.error(f"Failed to resolve schema: {e}")
            raise UdayamitraException(f"Failed to resolve schema: {e}", sys)

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

    async def run_execution_plan(self, plan: ExecutionPlan, metadata: Metadata) -> Dict[str, Any]:
        """
        Executes the given execution plan (only sequential supported).
        """
        results: Dict[str, Any] = {}
        if plan.execution_type != "sequential":
            raise UdayamitraException(f"Execution type '{plan.execution_type}' not supported yet.", sys)

        for task in plan.task_list:
            async with self.connect_to_server_for_tool(task.tool_name) as session:
                try:
                    # 1. Discover tool and get server-side required input
                    required_inputs = await self.get_required_inputs(session, task.tool_name)

                    # 2. Resolve inputs from metadata or previous outputs
                    input_data = self._resolve_input(task, results)

                    # 3. Resolve Pydantic model class
                    schema_class = self._get_schema(self.tool_registry[task.tool_name].input_schema)

                    # 4. Generate final validated input using LLM
                    full_input = self.schema_generator.generate_instance(
                        metadata=metadata.model_dump(),
                        execution_plan=plan.model_dump(),
                        model_class=schema_class,
                        user_input=input_data
                    )
                    print(f"full_input: {full_input}")
                    print(f"full input type {type(full_input)}")

                    # 5. Call the actual tool
                    logger.info(f"Calling tool '{task.tool_name}' with input: {full_input}")
                    wrapped_input = {"schema_dict": full_input.model_dump()}
                    response = await session.call_tool(required_inputs["server_Tool"], wrapped_input)

                    # 6. Updated response handling
                    parsed_output = {}
                    if hasattr(response, "content") and response.content:
                        try:
                            parsed_output = json.loads(response.content[0].text)
                        except Exception as e:
                            logger.warning(f"Failed to parse response as JSON. Using raw text: {e}")
                            parsed_output = {"output_text": response.content[0].text}

                    results[task.tool_name] = {
                        "tool": task.tool_name,
                        "output_text": parsed_output.get("output_text") or parsed_output.get("explanation"),
                        "eligibility": parsed_output.get("eligibility"),
                        "follow_up_questions": parsed_output.get("follow_up_questions"),
                        "raw_output": response.model_dump() if hasattr(response, "model_dump") else str(response),
                    }

                except Exception as e:
                    logger.error(f"Error calling tool '{task.tool_name}': {e}")
                    results[task.tool_name] = {"tool": task.tool_name, "error": str(e)}

        return results
