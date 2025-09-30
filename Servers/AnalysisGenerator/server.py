import sys
import argparse
import uvicorn  # Import the uvicorn library
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from typing import Optional

from .AnalysisGenerator import AnalysisGenerator
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.model import UserProfile
from utility.register_tools import generate_tool_registry_entry, register_tool

# Load environment variables from .env file
load_dotenv()

# Define the MCP server for this specific tool
# This object is a standard ASGI application that uvicorn can run
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
    # Standard argument parsing to get host and port
    parser = argparse.ArgumentParser(description="Run the AnalysisGenerator MCP Server.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to run the server on.")
    parser.add_argument("--port", type=int, default=8001, help="Port to run the server on.")
    args = parser.parse_args()

    # Register the tool (if your framework requires it)
    #tool_info = generate_tool_registry_entry()
    #register_tool(tool_info)
    
    # --- FIXED: Use uvicorn to run the server directly ---
    # This gives us full control over the host and port, bypassing the limited mcp.run()
    uvicorn.run(mcp, host=args.host, port=args.port)
