import sys
import os
from mcp.server.fastmcp import FastMCP
from .Analyzer import Analyzer 
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.register_tools import generate_tool_registry_entry, register_tool
from fastmcp import Client
from typing import List, Optional
from dotenv import load_dotenv
from utility.model import UserProfile

load_dotenv()

mcp = FastMCP("Analyzer", stateless_http=True) 
RETRIEVER_URL = "http://127.0.0.1:10000/retrieve-data/mcp"
RETRIEVER_TOOL_NAME = "retrieve_documents"

@mcp.tool()
async def generate_analysis(schema_dict: dict, documents: Optional[str] = None) -> dict: 
    try:
        logger.info(f"[Analyzer] Received request: {schema_dict}")  
        analysis_generator = Analyzer() 
        user_profile_obj = UserProfile(**schema_dict.get("user_profile", {}))

        query_text = schema_dict.get("user_query", "")
        logger.info(f"Querying retriever with: '{query_text}'")
        
        async with Client(RETRIEVER_URL) as retriever_client:
            response = await retriever_client.call_tool(
                RETRIEVER_TOOL_NAME,
                {
                    "query": query_text,
                    "caller_tool": mcp.name,
                    "top_k": 5
                }
            )

        docs_from_retriever = response.data.result
        if not isinstance(docs_from_retriever, list):
            logger.warning("Retrieved documents were not a list; resetting to []")
            docs_from_retriever = []
        
        logger.info(f"[Analyzer] Retrieved {len(docs_from_retriever)} documents.")  # Changed

        doc_dicts = [vars(d) for d in docs_from_retriever]
        combined_content = "\n\n".join(doc.get("content", "") for doc in doc_dicts)
        logger.info(f"[Analyzer] Combined content length: {len(combined_content)}")  # Changed

        # Call the core logic with the reshaped data
        result = await analysis_generator.generate_analysis(  # Changed method name
            user_query=query_text,
            user_profile=user_profile_obj.model_dump(), 
            retrieved_documents=combined_content or None
        )
        
        return result

    except Exception as e:
        logger.error("Failed to generate analysis", exc_info=True)  # Changed
        raise UdayamitraException("Failed to generate analysis", sys)  # Changed


if __name__ == "__main__":
    tool_info = generate_tool_registry_entry()
    register_tool(tool_info)
    mcp.run(transport='streamable-http')