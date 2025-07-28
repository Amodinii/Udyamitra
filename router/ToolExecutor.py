import sys
import json
import asyncio
from typing import Dict, Any, Union
from pydantic import BaseModel
from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import re
import ast
from router.ModelResolver import ModelResolver
from router.SchemaGenerator import SchemaGenerator
from utility.model import ExecutionPlan, ToolTask, ToolRegistryEntry, Metadata
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.register_tools import load_registry_from_file
from utility.LLM import LLMClient


class ToolExecutor:
    def __init__(self):
        try:
            logger.info("Initializing ToolExecutor")
            self.tool_registry: Dict[str, ToolRegistryEntry] = load_registry_from_file()
            if not self.tool_registry:
                raise UdayamitraException("Tool registry is empty. Ensure tools are registered properly.", sys)
            self.resolver = ModelResolver("utility.model")
            self.schema_generator = SchemaGenerator()
            self.llm_client = LLMClient(model="meta-llama/llama-4-maverick-17b-128e-instruct")

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
            return model_class
        except Exception as e:
            logger.error(f"Failed to resolve schema: {e}")
            raise UdayamitraException(f"Failed to resolve schema: {e}", sys)

    @asynccontextmanager
    async def connect_to_server_for_tool(self, tool_name: str):
        if tool_name not in self.tool_registry:
            raise UdayamitraException(f"Tool '{tool_name}' not found in registry.", sys)

        endpoint = self.tool_registry[tool_name].endpoint
        logger.info(f"Connecting to MCP server at {endpoint} for tool '{tool_name}'")

        async with streamablehttp_client(url=endpoint) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                logger.info("Initializing MCP session...")
                await session.initialize()
                logger.info(f"MCP session initialized for {endpoint}")
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
            return {"output_text": referenced_output.get("output_text")}
        return task.input

    @staticmethod
    def format_explanation(raw: str) -> str:
        """Clean and format the raw LLM explanation for frontend display."""
        cleaned = raw.strip()

        # Convert escaped \n to real newlines, if necessary
        if "\\n" in cleaned:
            cleaned = cleaned.replace("\\n", "\n")

        # Normalize excessive newlines
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # Optionally format bullets (for markdown or plain text)
        cleaned = cleaned.replace("* ", "• ")

        # Add consistent header if not present
        if not cleaned.lower().startswith("here's a simple explanation"):
            cleaned = "Here's a simple explanation:\n\n" + cleaned

        return cleaned
    
    async def run_execution_plan(
        self,
        plan: ExecutionPlan,
        metadata: Metadata,
        flatten_output: bool = False
    ) -> Union[str, Dict[str, Any]]:
        results: Dict[str, Any] = {}

        if plan.execution_type != "sequential":
            raise UdayamitraException(f"Execution type '{plan.execution_type}' not supported yet.", sys)

        for task in plan.task_list:
            async with self.connect_to_server_for_tool(task.tool_name) as session:
                try:
                    required_inputs = await self.get_required_inputs(session, task.tool_name)
                    input_data = self._resolve_input(task, results)
                    schema_class = self._get_schema(self.tool_registry[task.tool_name].input_schema)

                    full_input = self.schema_generator.generate_instance(
                        metadata=metadata.model_dump(),
                        execution_plan=plan.model_dump(),
                        model_class=schema_class,
                        user_input=input_data
                    )

                    logger.info(f"Calling tool '{task.tool_name}' with input: {full_input}")
                    wrapped_input = {"schema_dict": full_input.model_dump()}
                    response = await session.call_tool(required_inputs["server_Tool"], wrapped_input)

                    parsed = {}
                    if hasattr(response, "content") and response.content:
                        try:
                            parsed = json.loads(response.content[0].text)
                        except Exception:
                            parsed = {"output_text": response.content[0].text}

                    # Run the LLM
                    system_prompt = '''You are a helpful assistant that explains the output of a tool to the user, in an easy, detailed explainable way. 
    Ensure you explain all the keys in the output. Dont summarize it, convert it to a simple explanation suitable for a user.
    - Make sure you mention the sources at the end of the explanation.
    - Do not provide any commentary (or preamble) before the explanation, just provide the explanation.
    - You can add the follow up questions too, based on the context, make the subheading for it."
    - If you have a JSON, do not explain what the keys mean, just focus on simplifying the "content" of the JSON.
    '''
                    user_message = f"""Here is the tool's response:\n\n{json.dumps(parsed, indent=2)}\n\nPlease convert this into a simple explanation suitable for a user."""
                    final_explanation = self.llm_client.run_chat(system_prompt, user_message)

                    # Fix the \n before formatting
                    if isinstance(final_explanation, str) and '\\n' in final_explanation:
                        try:
                            final_explanation = ast.literal_eval(f"'''{final_explanation}'''")
                            logger.info(f"Evaluated explanation: {final_explanation}")
                        except Exception:
                            final_explanation = final_explanation.replace("\\n", "\n")  # fallback

                    # Now format
                    formatted = self.format_explanation(raw=final_explanation)

                    results[task.tool_name] = formatted

                except Exception as e:
                    logger.error(f"Error calling tool '{task.tool_name}': {e}")
                    results[task.tool_name] = f"Failed to process {task.tool_name}: {e}"

        if flatten_output and len(results) == 1:
            return next(iter(results.values()))

        if results:
            return {
                tool: explanation
                for tool, explanation in results.items()
            }

        return "No tools could be executed successfully."
