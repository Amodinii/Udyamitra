import os
import sys
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from Logging.logger import logger
from Exception.exception import UdayamitraException
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_astradb import AstraDBVectorStore
from utility.register_tools import generate_tool_registry_entry, register_tool
from utility.model import RetrievedDoc, RetrieverOutput

load_dotenv()
ASTRA_DB_ENDPOINT = os.getenv("ASTRA_DB_ENDPOINT")
ASTRA_DB_TOKEN    = os.getenv("ASTRA_DB_TOKEN")
if not ASTRA_DB_ENDPOINT or not ASTRA_DB_TOKEN:
    raise RuntimeError("ASTRA_DB_ENDPOINT and ASTRA_DB_TOKEN must be set")

logger.info("Initializing embeddings and vector stores for Retriever…")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore_chunks = AstraDBVectorStore(
    embedding=embeddings,
    collection_name="Scheme_chunks",
    namespace=os.getenv("ASTRA_DB_KEYSPACE"),
    api_endpoint=ASTRA_DB_ENDPOINT,
    token=ASTRA_DB_TOKEN,
)
vectorstore_metadata = AstraDBVectorStore(
    embedding=embeddings,
    collection_name="Schemes_metadata",
    namespace=os.getenv("ASTRA_DB_KEYSPACE"),
    api_endpoint=ASTRA_DB_ENDPOINT,
    token=ASTRA_DB_TOKEN,
)
logger.info("Retriever vector stores ready.")

mcp = FastMCP("SchemeDB", stateless_http=True)

@mcp.tool()
async def retrieve_documents(query: str, collection_type: str = "chunks", top_k: int = 5) -> RetrieverOutput:
    logger.info(f"[Retriever] Query received → collection: '{collection_type}' | query: '{query}' | top_k: {top_k}")
    store = {"chunks": vectorstore_chunks, "metadata": vectorstore_metadata}.get(collection_type)
    if store is None:
        raise UdayamitraException(f"Invalid collection_type: {collection_type}", sys)

    try:
        docs = store.similarity_search(query=query, k=top_k)
        logger.info(f"[Retriever] Found {len(docs)} matching docs.")
        for i, doc in enumerate(docs):
            logger.debug(f"[Retriever] Doc {i+1}: {doc.page_content[:120]!r} | Metadata: {doc.metadata}")
        return RetrieverOutput(result=[
        RetrievedDoc(content=d.page_content, metadata=d.metadata) for d in docs
    ])
    except Exception as e:
        logger.error(f"[Retriever] Error fetching docs: {e}", exc_info=True)
        raise UdayamitraException("Failed to retrieve documents", sys)

if __name__ == "__main__":
    tool_info = generate_tool_registry_entry()
    register_tool(tool_info)
    mcp.run(transport="streamable-http")
