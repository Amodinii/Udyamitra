"""
server.py - This file provides SchemeDB Retriever server as a MCP server.
"""

import sys
import os
import dotenv
from astrapy import DataAPIClient
from mcp.server.fastmcp import FastMCP
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.register_tools import generate_tool_registry_entry, register_tool

dotenv.load_dotenv()

# Create the MCP server
mcp = FastMCP("SchemeDBRetriever", stateless_http=True)

# Setup Astra DB client and collection
client = DataAPIClient()
database = client.get_database(
    os.getenv("ASTRA_DB_ENDPOINT"),
    token=os.getenv("ASTRA_DB_APPLICATION_TOKEN")
)

@mcp.tool()
def retrieve_documents(query: str, collection_name: str, top_k: int = 5) -> list[dict]:
    """
    Search a given Astra DB collection using vector similarity via $vectorize.
    You must pass the target collection name (e.g., Schemes_metadata or Schemes_chunks).
    """
    try:
        logger.info(f"Querying '{collection_name}' for: {query}")
        collection = database.get_collection(collection_name)
        cursor = collection.find({}, sort={"$vectorize": query}, options={"limit": top_k})
        return [
            {
                "scheme_name": doc.get("scheme_name"),
                "content": doc.get("chunk", ""),
                "metadata": doc.get("metadata", {}),
                "source": doc.get("source_files", []),
            }
            for doc in cursor
        ]
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise UdayamitraException("Failed to retrieve documents", sys)

if __name__ == "__main__":
    tool_info = generate_tool_registry_entry()
    register_tool(tool_info)
    mcp.run(transport='streamable-http')
