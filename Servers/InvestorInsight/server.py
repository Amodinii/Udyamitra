import sys
from mcp.server.fastmcp import FastMCP
from .InsightGenerator import InsightGenerator
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.register_tools import generate_tool_registry_entry, register_tool
from fastmcp import Client
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("InsightGenerator", stateless_http = True)
RETRIEVER_URL = "http://127.0.0.1:10000/retrieve-docs/mcp"
RETRIEVER_TOOL_NAME = "retrieve_documents"

@mcp.tool()
async def generate_insight(query: dict, documents: Optional[str] = None):
    try:
        logger.info("Received request to generate insights")
        insight_generator = InsightGenerator()

        logger.info(f"[Explainer] Querying retriever with: '{query}', with type: {type(query)}")
        logger.debug(f"[Explainer] Calling retriever with query: '{query}' | Collection: 'chunks'")

        async with Client(RETRIEVER_URL) as retriever_client:
            response = await retriever_client.call_tool(
                RETRIEVER_TOOL_NAME,
                {
                    "query": query["query"],
                    "collection_type": "chunks",  
                    "top_k": 5
                }
            )

        logger.debug(f"[Explainer] Raw retriever response: {response}")
        logger.warning(f"[Explainer] response.data → {response.data} (type={type(response.data)})")

        docs = response.data.result
        if not isinstance(docs, list):
            logger.warning("[Explainer] Retrieved documents were not a list; resetting to []")
            docs = []
        
        for d in docs:
            logger.debug(f"[Explainer] Raw doc object: {d} | type={type(d)} | keys={vars(d).keys()}")

        logger.info(f"[Explainer] Retrieved {len(docs)} documents")

        doc_dicts = [vars(d) for d in docs]
        combined_content = "\n\n".join(doc.get("content", "") for doc in doc_dicts)
        logger.info(f"[Explainer] Combined content length: {len(combined_content)}")

        result = insight_generator.generate_insight(
            retrieved_documents=combined_content or None
        )
        return result

    except Exception as e:
        logger.error("Failed to generate insight", exc_info=True)
        raise UdayamitraException("Failed to generate insight", sys)


if __name__ == "__main__":
    tool_info = generate_tool_registry_entry()
    register_tool(tool_info)
    mcp.run(transport='streamable-http')