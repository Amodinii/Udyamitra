import os
import sys
import argparse
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from typing import Optional

from .AnalysisGenerator import AnalysisGenerator
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.model import UserProfile
from utility.register_tools import generate_tool_registry_entry, register_tool

load_dotenv()

mcp = FastMCP("AnalysisGenerator", stateless_http=True)

@mcp.tool()
async def generate_analysis(schema_dict: dict) -> dict:
    """
    This tool takes a user query and profile, queries a structured trade database,
    and returns an analytical insight.
    """
    try:
        logger.info(f"[AnalysisGenerator] Received request: {schema_dict}")
        
        analysis_generator = AnalysisGenerator()

        user_query = schema_dict.get("user_query", "Provide a general analysis of the export data.")
        user_profile_data = schema_dict.get("user_profile", {})
        
        result = analysis_generator.generate_structured_insight(
            user_query=user_query,
            user_profile=user_profile_data
        )
        
        return result

    except Exception as e:
        logger.error("Failed to generate analysis", exc_info=True)
        raise UdayamitraException("Failed to generate analysis", sys)


if __name__ == "__main__":
    # 1. Get the port from the command line
    parser = argparse.ArgumentParser(description="Run the AnalysisGenerator MCP Server.")
    parser.add_argument("--port", type=int, default=8001, help="Port to run the server on.")
    args = parser.parse_args()

    # 2. Set the environment variable for the MCP server to read
    os.environ['MCP_PORT'] = str(args.port)
    os.environ['MCP_HOST'] = '127.0.0.1'

    # 3. Register the tool
    #tool_info = generate_tool_registry_entry()
    #register_tool(tool_info)
    
    # 4. Run the server, which will pick up the port from the environment variable
    mcp.run(transport='streamable-http')