"""
InsightGenerator.py - MCP server for generating personalized investor insights.
Uses external embedding and reranker APIs to avoid loading heavy models locally.
"""

import sys
import json
import asyncio
import httpx
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.LLM import LLMClient
from typing import List, Dict

from utility.model import InsightGeneratorInput, InsightGeneratorOutput, RetrievedDoc
import nest_asyncio
nest_asyncio.apply()


# URL for your deployed reranker API
RERANKER_API_URL = "https://adityapeopleplus-embedding-generator.hf.space/rerank"

class InsightGenerator:
    JSON_FORMAT_INSTRUCTIONS = """
    {
        "insight_summary": "A concise, one-sentence summary of the key insight based on the user's query.",
        "detailed_explanation": "A detailed but easy-to-understand explanation of the insight. Directly address the user's query and reference their profile. Explain the 'why' behind the insight.",
        "potential_benefits": [
            "List of potential benefits or upsides of acting on this insight.",
            "Each benefit should be a separate string in this list."
        ],
        "associated_risks": [
            "List of key risks or downsides the user must consider.",
            "Each risk should be a separate string in this list."
        ],
        "actionable_steps": [
            "A numbered list of concrete, practical steps the user can take next.",
            "Example: 1. Research Company X's Q4 earnings report.",
            "Example: 2. Consider diversifying with an ETF that tracks the S&P 500."
        ],
        "sources": [
            "List the specific document titles or identifiers used for this analysis.",
            "If no documents were used, return an empty list: []"
        ]
    }
    """

    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        try:
            logger.info("Starting InsightGenerator...")
            logger.info(f"Initializing InsightGenerator with model: {model}")
            self.llm_client = LLMClient(model=model)
            logger.info("InsightGenerator initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize InsightGenerator: {e}")
            raise UdayamitraException("Failed to initialize InsightGenerator", sys)

    async def _rerank_documents(self, query: str, documents: List[Dict]) -> List[Dict]:
        """Rerank documents using external reranker API."""
        if not documents:
            return []

        # Prepare payload for API
        payload = {
            "query": query,
            "documents": [{"content": doc.get("content", ""), **doc} for doc in documents]
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(RERANKER_API_URL, json=payload)
                resp.raise_for_status()
                ranked_docs = resp.json().get("documents", [])

            return sorted(ranked_docs, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        except Exception as e:
            logger.error(f"Reranker API call failed: {e}", exc_info=True)
            # fallback: return original order
            return documents

    async def generate_insight(self, user_query: str, user_profile: dict, retrieved_documents: str = None) -> dict:
        try:
            system_prompt = """
            You are 'InsightBot', an expert financial analyst AI assistant. Your purpose is to provide clear, data-driven, and personalized investment insights to investors.

            You MUST adhere to the following principles:
            1.  **Data-First:** Your analysis MUST be based on the information provided in the "RETRIEVED DOCUMENTS". If the documents are insufficient, state that clearly in your explanation. Never invent facts.
            2.  **User-Centric:** Personalize the insight by considering the "USER PROFILE" (e.g., their risk tolerance, investment goals).
            3.  **Strict JSON Output:** Your entire response MUST be a single, valid JSON object. Do not include any text, explanations, or markdown formatting before or after the JSON object.
            """

            user_prompt = f"""
            Generate a personalized investment insight based on the user's request and the provided context. Follow the required JSON output format precisely.

            === USER QUERY ===
            {user_query}

            === USER PROFILE ===
            {json.dumps(user_profile, indent=2)}

            === RETRIEVED DOCUMENTS (Primary Source of Truth) ===
            {retrieved_documents if retrieved_documents else "No documents provided."}

            === REQUIRED JSON OUTPUT FORMAT ===
            {self.JSON_FORMAT_INSTRUCTIONS}
            """

            # Run through your LLM client
            response_dict = await asyncio.to_thread(self.llm_client.run_json, system_prompt, user_prompt)

            validated_output = InsightGeneratorOutput(**response_dict)
            return validated_output.model_dump()
        except Exception as e:
            logger.error(f"InsightGenerator failed: {e}")
            raise UdayamitraException("Failed to generate insights", sys)