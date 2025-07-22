'''
server.py - This file provides EligibilityChecker server as a MCP server.
'''

import sys
from mcp.server.fastmcp import FastMCP
from .EligibilityChecker import EligibilityChecker
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.register_tools import generate_tool_registry_entry, register_tool
from utility.model import EligibilityCheckRequest

mcp = FastMCP("EligibilityChecker", stateless_http=True)

@mcp.tool()
async def check_eligibility(schema_dict: dict, documents: str = None) -> dict:
    try:
        logger.info(f"Received eligibility check request: {schema_dict}")
        checker = EligibilityChecker()
        request_obj = EligibilityCheckRequest(**schema_dict)
        response = checker.check_eligibility(request=request_obj, retrieved_documents=documents)
        print(f"Response [EligibilityChecker]: {response}")
        return response
    except Exception as e:
        logger.error(f"Failed to check eligibility: {e}")
        raise UdayamitraException("Failed to check eligibility", sys)

if __name__ == "__main__":
    tool_info = generate_tool_registry_entry()
    register_tool(tool_info)
    mcp.run(transport='streamable-http')