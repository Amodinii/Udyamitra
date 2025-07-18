from astrapy import DataAPIClient
from mcp.server.fastmcp import FastMCP
from Logging.logger import logger
import os
import dotenv

dotenv.load_dotenv()

client = DataAPIClient()
database = client.get_database(
    os.getenv("ASTRA_DB_ENDPOINT"),
    token=os.getenv("ASTRA_DB_APPLICATION_TOKEN")
)

COLLECTION_NAME = "Schemes_metadata"
collection = database.get_collection(COLLECTION_NAME)

mcp = FastMCP("scheme-db")

@mcp.tool()
def retrieve_documents(query: str, top_k: int = 5) -> list[dict]:
    """Search Astra DB using vector similarity via $vectorize sort."""
    logger.info(f"Searching '{COLLECTION_NAME}' for query: {query}")
    try:
        cursor = collection.find({}, sort={"$vectorize": query}, options={"limit": top_k})
        return [
            {
                "scheme_name": doc.get("scheme_name"),
                "content": doc.get("chunk", ""),  # for schemes_chunks
                "metadata": doc.get("metadata", {}),
                "source": doc.get("source_files", []),
            }
            for doc in cursor
        ]
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise
