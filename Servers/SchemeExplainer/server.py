'''
server.py - This file provides SchemeExplainer server as a MCP server. 
'''

import sys
from mcp.server.fastmcp import FastMCP
from .SchemeExplainer import SchemeExplainer
from Logging.logger import logger
from Exception.exception import UdayamitraException

mcp = FastMCP("SchemeExplainer", stateless_http=True)

@mcp.tool()
async def explain_scheme(schema_dict: dict, documents: str = None) -> dict:
    try:
        logger.info(f"Received request to explain scheme: {schema_dict}")
        scheme_explainer = SchemeExplainer()
        response = scheme_explainer.explain_scheme(scheme_metadata=schema_dict, retrieved_documents=documents)
        return response
    except Exception as e:
        logger.error(f"Failed to explain scheme: {e}")
        raise UdayamitraException("Failed to explain scheme", sys)