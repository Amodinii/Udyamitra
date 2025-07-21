import os
import sys
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from Logging.logger import logger
from Exception.exception import UdayamitraException
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_astradb import AstraDBVectorStore
from utility.register_tools import generate_tool_registry_entry, register_tool

load_dotenv()

ASTRA_DB_ENDPOINT = os.getenv("ASTRA_DB_ENDPOINT")
ASTRA_DB_TOKEN = os.getenv("ASTRA_DB_TOKEN")

# Embedding model (LangChain wrapper for HuggingFace)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Vector store for chunks and metadata
vectorstore_chunks = AstraDBVectorStore(
    embedding=embeddings,
    collection_name="Scheme_chunks",
    api_endpoint=ASTRA_DB_ENDPOINT,
    token=ASTRA_DB_TOKEN,
)

vectorstore_metadata = AstraDBVectorStore(
    embedding=embeddings,
    collection_name="Schemes_metadata",
    api_endpoint=ASTRA_DB_ENDPOINT,
    token=ASTRA_DB_TOKEN,
)

# Initialize MCP server
mcp = FastMCP("SchemeDB", stateless_http=True)

@mcp.tool()
async def retrieve_documents(query: str, collection_type: str = "chunks", top_k: int = 5) -> list[dict]:
    """
    Retrieve documents from either Scheme_chunks or Schemes_metadata using vector search.
    collection_type = "chunks" | "metadata"
    """
    logger.info(f"Retrieving from collection: {collection_type} | Query: {query} | TopK: {top_k}")
    try:
        store = {
            "chunks": vectorstore_chunks,
            "metadata": vectorstore_metadata
        }.get(collection_type)

        if not store:
            raise ValueError(f"Invalid collection_type: {collection_type}. Must be 'chunks' or 'metadata'.")

        docs = store.similarity_search(query=query, k=top_k)

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in docs
        ]

    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        raise UdayamitraException("Failed to retrieve documents", sys)

# Run server and register tool
if __name__ == "__main__":
    tool_info = generate_tool_registry_entry()
    register_tool(tool_info)
    mcp.run(transport='streamable-http')
