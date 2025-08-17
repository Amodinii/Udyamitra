import sys
from mcp.server.fastmcp import FastMCP
from .InsightGenerator import InsightGenerator
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.register_tools import generate_tool_registry_entry, register_tool
from fastmcp import Client
from typing import List
from dotenv import load_dotenv
from model import UserProfile, RetrievedDoc, InsightGeneratorInput, InsightGeneratorOutput
from pydantic import BaseModel

load_dotenv()

mcp = FastMCP("InsightGenerator", stateless_http = True)
RETRIEVER_URL = "http://127.0.0.1:10000/retrieve-docs/mcp"
RETRIEVER_TOOL_NAME = "retrieve_documents"

class GenerateInsightToolInput(BaseModel):
    user_query: str
    user_profile: UserProfile

@mcp.tool()
async def generate_insight(data: GenerateInsightToolInput) -> InsightGeneratorOutput:
    try:
        logger.info("Received request to generate insights")
        insight_generator = InsightGenerator()

        logger.info(f"Querying retriever with: '{data.user_query}'")
        async with Client(RETRIEVER_URL) as retriever_client:
            response = await retriever_client.call_tool(
                RETRIEVER_TOOL_NAME,
                {
                    "query": data.user_query,
                    "top_k": 5
                }
            )

        docs_from_retriever = response.data.result
        if not isinstance(docs_from_retriever, list):
            logger.warning("Retrieved documents were not a list; resetting to []")
            docs_from_retriever = []
        
        validated_docs = [RetrievedDoc(**doc) for doc in docs_from_retriever]
        logger.info(f"Retrieved and validated {len(validated_docs)} documents")

        generator_input = InsightGeneratorInput(
            user_query=data.user_query,
            user_profile=data.user_profile,
            retrieved_documents=validated_docs
        )

        result = insight_generator.generate_insight(generator_input)
        
        return result

    except Exception as e:
        logger.error("Failed to generate insight", exc_info=True)
        raise UdayamitraException("Failed to generate insight", sys)


if __name__ == "__main__":
    tool_info = generate_tool_registry_entry()
    register_tool(tool_info)
    mcp.run(transport='streamable-http')