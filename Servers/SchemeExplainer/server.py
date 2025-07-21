import sys
from mcp.server.fastmcp import FastMCP
from .SchemeExplainer import SchemeExplainer
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.register_tools import generate_tool_registry_entry, register_tool
from utility.model import SchemeMetadata
from fastmcp import Client
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("SchemeExplainer", stateless_http=True)

RETRIEVER_URL = "http://127.0.0.1:10000/retrieve-scheme/mcp"
RETRIEVER_TOOL_NAME = "retrieve_documents"

@mcp.tool()
async def explain_scheme(schema_dict: dict, documents: Optional[str] = None) -> dict:
    try:
        logger.info(f"Received request to explain scheme: {schema_dict}")
        scheme_explainer = SchemeExplainer()

        reshaped_metadata = {
            "scheme_name": schema_dict.get("entities", {}).get("scheme_name", ""),
            "user_profile": schema_dict.get("user_profile", {}),
            "context_entities": schema_dict.get("entities", {}),
            "detected_intents": schema_dict.get("intents", []),
            "query": schema_dict.get("query", ""),
        }
        metadata_obj = SchemeMetadata(**reshaped_metadata)

        query = reshaped_metadata["scheme_name"].strip() or metadata_obj.model_dump_json()

        # DEBUG: confirm we're using 'chunks'
        logger.debug(f"About to call retriever with collection_type='chunks' and query='{query}'")

        async with Client(RETRIEVER_URL) as retriever_client:
            response = await retriever_client.call_tool(
                RETRIEVER_TOOL_NAME,
                {
                    "query": query,
                    "collection_type": "chunks",  
                    "top_k": 5
                }
            )

        try:
            docs = response.data.output
        except AttributeError:
            docs = getattr(response.data, "output", [])

        if not isinstance(docs, list):
            logger.warning("Retrieved documents were not a list; resetting to []")
            docs = []

        logger.info(f"Retrieved {len(docs)} documents from 'Scheme_chunks'.")

        combined_content = "\n\n".join(
            doc.get("content", "") for doc in docs if isinstance(doc, dict)
        )
        logger.info(f"Combined document content length: {len(combined_content)}")

        result = scheme_explainer.explain_scheme(
            scheme_metadata=metadata_obj,
            retrieved_documents=combined_content or None
        )
        return result

    except Exception as e:
        logger.error("Failed to explain scheme", exc_info=True)
        raise UdayamitraException("Failed to explain scheme", sys)

if __name__ == "__main__":
    tool_info = generate_tool_registry_entry()
    register_tool(tool_info)
    mcp.run(transport='streamable-http')
