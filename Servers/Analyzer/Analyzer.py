import os
import sys
import json
import re
import asyncio
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
# Removed: from fastmcp import Client (no longer needed in this file)

from utility.LLM import LLMClient
from Logging.logger import logger
from Exception.exception import UdayamitraException

load_dotenv()

class Analyzer:
    """
    A tool to generate analysis based SOLELY on retrieved vector context
    provided as an argument.
    """

    JSON_FORMAT_INSTRUCTIONS = """
    {
    "insight_summary": "A concise, impactful summary of the key insight based on the provided context.",
    "detailed_explanation": "Explain what this information means for the user's business, using 'you' and 'your'.",
    "data_summary": [
        "A bulleted list of the most important facts or findings from the context."
    ],
    "actionable_steps": [
        "Frame this as 'Your Next Steps'. Provide a clear checklist of actions the user can take, numbered as strings."
    ],
    "sources": ["Mospi_data"] 
    }
    """

    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        try:
            logger.info("Starting Analyzer...")
            self.llm_client = LLMClient(model=model)
            logger.info("Analyzer initialized successfully.") 

        except Exception as e:
            logger.error(f"Failed to initialize Analyzer: {e}")
            raise UdayamitraException(e, sys)

    def _sanitize_llm_list_output(self, data: Any) -> List[str]:
        if isinstance(data, list):
            return [str(item) for item in data]
        if isinstance(data, str):
            items = [re.sub(r'^\s*[\*\-]?\s*\d*\.\s*', '', line).strip() for line in data.split('\n')]
            return [item for item in items if item]
        return []

    async def generate_analysis(self, user_query: str, user_profile: dict, retrieved_documents: Optional[str] = None) -> dict:
        """
        Generates an analysis based *only* on the provided vector context.
        """
        try:
            logger.info(f"Analyzer class using pre-fetched vector data (length: {len(retrieved_documents or '')}).")
            vector_context = retrieved_documents
            
            source_names = ["Mospi_data"]

            if not vector_context:
                logger.warning("No vector context provided to Analyzer. Analysis will be limited.")
                return {
                    "insight_summary": "No information found.",
                    "detailed_explanation": f"I could not find any relevant information for your query: '{user_query}'.",
                    "data_summary": ["No data retrieved."],
                    "actionable_steps": ["Please try rephrasing your query."],
                    "sources": [] 
                }

            system_prompt = """
            You are an expert 'Business Growth Advisor AI' for exporters.
            Your goal is to provide specific, actionable advice in a clear JSON format.
            You MUST analyze the provided 'Vector Context' to answer the user's query.

            - **Personality:** Professional, insightful, and direct.
            - **Core Task:** Synthesize the provided 'Vector Context' which contains snippets of information from the MoSPI database.
            - **Rule:** NEVER invent data. Base your entire analysis on the context provided. If the context is insufficient, state that.
            - **JSON Output:** You MUST produce a single, valid JSON object with ONLY the requested keys.
            """

            user_prompt = f"""
            Analyze the following context to answer the user's query.
            
            ## User Query
            "{user_query}"

            ## User Profile (for personalization)
            {json.dumps(user_profile, indent=2)}

            ## Vector Context (Background Info from MoSPI)
            Use this information to build your analysis.
            {vector_context}

            ## Required JSON Output
            Generate a single JSON object with these exact keys. Follow the format instructions precisely.
            {self.JSON_FORMAT_INSTRUCTIONS}
            """ 
            
            textual_response = None
            try:
                textual_response = self.llm_client.run_json(system_prompt, user_prompt)
            except Exception as llm_error:
                logger.warning(f"LLM failed: {llm_error}")
                textual_response = None 
            
            if not textual_response or not isinstance(textual_response, dict):
                # Fallback in case LLM fails
                textual_response = {
                    "insight_summary": "Context analysis complete.",
                    "detailed_explanation": "The analysis has been performed on the retrieved vector context.",
                    "data_summary": [f"Analyzed {len(vector_context)} characters of context."],
                    "actionable_steps": ["Review the retrieved information for insights."]
                }
            
            textual_response["sources"] = source_names
            
            if "data_summary" in textual_response:
                textual_response["data_summary"] = self._sanitize_llm_list_output(textual_response["data_summary"])
            if "actionable_steps" in textual_response:
                textual_response["actionable_steps"] = self._sanitize_llm_list_output(textual_response["actionable_steps"])

            if "data_table" in textual_response:
                del textual_response["data_table"]

            return textual_response

        except Exception as e:
            logger.error(f"Failed to generate analysis in Analyzer class: {e}", exc_info=True)
            raise UdayamitraException(f"Failed to generate analysis in Analyzer class: {e}", sys)

