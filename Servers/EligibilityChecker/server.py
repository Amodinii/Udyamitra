import sys
from mcp.server.fastmcp import FastMCP
from .EligibilityChecker import EligibilityChecker
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.register_tools import generate_tool_registry_entry, register_tool
from utility.model import EligibilityCheckRequest
from fastmcp import Client
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("EligibilityChecker", stateless_http=True)

RETRIEVER_URL = "http://127.0.0.1:10000/retrieve-scheme/mcp"
RETRIEVER_TOOL_NAME = "retrieve_documents"

@mcp.tool()
async def check_eligibility(schema_dict: dict) -> dict:
    try:
        logger.info(f"[EligibilityChecker] Received eligibility check request: {schema_dict}")
        checker = EligibilityChecker()
        request_obj = EligibilityCheckRequest(**schema_dict)

        # Extract query string from scheme_name or fallback to full object
        query = request_obj.scheme_name.strip() or request_obj.model_dump_json()
        logger.debug(f"[EligibilityChecker] Querying retriever with: '{query}'")

        # Retrieve relevant documents
        async with Client(RETRIEVER_URL) as retriever_client:
            response = await retriever_client.call_tool(
                RETRIEVER_TOOL_NAME,
                {
                    "query": query,
                    "collection_type": "chunks",
                    "top_k": 5
                }
            )

        logger.debug(f"[EligibilityChecker] Retriever response: {response}")
        docs = response.data.result
        if not isinstance(docs, list):
            logger.warning("[EligibilityChecker] Retrieved documents were not a list; resetting to []")
            docs = []

        # Convert to text
        doc_dicts = [vars(d) for d in docs]
        combined_content = "\n\n".join(doc.get("content", "") for doc in doc_dicts)
        logger.info(f"[EligibilityChecker] Combined content length: {len(combined_content)}")

        # Run eligibility checker with documents
        response = checker.check_eligibility(request=request_obj, retrieved_documents=combined_content or None)
        return response

    except Exception as e:
        logger.error("Failed to check eligibility", exc_info=True)
        raise UdayamitraException("Failed to check eligibility", sys)

if __name__ == "__main__":
    tool_info = generate_tool_registry_entry()
    register_tool(tool_info)
    mcp.run(transport='streamable-http')
