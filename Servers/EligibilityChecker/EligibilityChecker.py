'''
EligibilityChecker.py - This is the source code for the MCP server that checks user eligibility for government schemes.
'''

import sys
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.LLM import LLMClient
from utility.model import EligibilityCheckRequest, EligibilityCheckResponse
from .QuestionGenerator import QuestionGenerator
from typing import Optional


class EligibilityChecker:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        try:
            logger.info("Starting EligibilityChecker...")
            logger.info(f"Initializing EligibilityChecker with model: {model}")
            self.llm_client = LLMClient(model=model)
            self.question_generator = QuestionGenerator(model=model)
        except Exception as e:
            logger.error(f"Failed to initialize EligibilityChecker: {e}")
            raise UdayamitraException("Failed to initialize EligibilityChecker", sys)

    def check_eligibility(self, request: EligibilityCheckRequest, retrieved_documents: str = None) -> dict:
        """
        Returns:
            - If complete: dict of `EligibilityCheckResponse`
            - If missing fields: dict with `eligibility` + `follow_up_questions`
        """
        try:
            system_prompt = """
            You are a strict and detail-oriented assistant that checks whether a user is eligible for an Indian government scheme.

            Your job:
            - You will receive a scheme name, user profile data, and optionally scheme-related documents.
            - Your task is to evaluate the user's eligibility **based strictly on document content** (if provided), or fallback knowledge if not.

            Your response **must** be a clean, valid JSON object with this exact structure:

            {
            "scheme_name": "<same as input>",
            "eligible": true | false | null,
            "reasons": ["<reason 1>", "<reason 2>"],
            "missing_fields": ["<required user inputs that are missing>"],
            "suggestions": ["<follow-up questions or next steps>"],
            "sources": ["<source links or document references>"]
            }

            Important:
            - Do NOT include any prose, markdown, explanations, or notes — JSON only.
            - `eligible` must be `null` if required user data is incomplete.
            - `reasons` must explain *why* the user is eligible/ineligible.
            - `sources` must refer to documents or URLs if used.
            - Be honest about uncertainty if information is missing.

            If documents are provided, you MUST prioritize them over your own knowledge.
            """

            user_prompt = f"""
            Evaluate user eligibility for the following scheme.

            === SCHEME ===
            {request.scheme_name}

            === USER PROFILE ===
            {request.user_profile.model_dump_json(indent=2)}

            === CONTEXT ENTITIES ===
            {request.context_entities if request.context_entities else "{}"}

            === ORIGINAL USER QUERY ===
            {request.query or "Not provided"}

            === RETRIEVED DOCUMENTS ===
            {retrieved_documents if retrieved_documents else "None"}

            Instructions:
            - Use the documents above as your **primary source** of rules and requirements.
            - If documents are not present or are incomplete, fallback to general knowledge and clearly mention uncertainty.
            - If you cannot determine eligibility, set "eligible": null and list what's missing.
            - If eligible or ineligible, clearly explain the reasons based on rules.
            - Output must strictly follow the JSON schema. No extra commentary.
            """

            raw_response = self.llm_client.run_json(system_prompt, user_prompt)
            eligibility = EligibilityCheckResponse(**raw_response)

            response = {
                "eligibility": eligibility.model_dump()
            }

            if eligibility.eligible is None and eligibility.missing_fields:
                follow_ups = self.question_generator.generate_questions(
                    missing_fields=eligibility.missing_fields,
                    scheme_name=eligibility.scheme_name
                )
                response["follow_up_questions"] = follow_ups

            return response

        except Exception as e:
            logger.error(f"EligibilityChecker failed: {e}")
            raise UdayamitraException("Failed to check eligibility", sys)
