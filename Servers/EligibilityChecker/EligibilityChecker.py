'''
EligibilityChecker.py - This is the source code for the MCP server that checks user eligibility for government schemes.
'''

import sys
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.LLM import LLMClient
from utility.model import EligibilityCheckRequest, EligibilityCheckResponse
from .QuestionGenerator import QuestionGenerator  

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
                You are provided with user details, a target scheme, and optionally related scheme documents.
                Your job is to evaluate if the user qualifies, and respond in strict JSON format as below:
                {
                    "scheme_name": "<same as input>",
                    "eligible": true or false or null,
                    "reasons": ["<reason 1>", "<reason 2>"],
                    "missing_fields": ["<what data is missing>"],
                    "suggestions": ["<follow-up questions or next steps>"],
                    "sources": ["<any references used>"]
                }
                Do not add any other commentary or formatting. JSON only.
            """

            user_prompt = f"""
                Scheme: {request.scheme_name}
                User Profile:
                {request.user_profile.model_dump_json(indent=2)}

                Known Context (Entities):
                {request.context_entities if request.context_entities else "{}"}

                Original Query:
                {request.query or "Not provided"}

                Documents (if any):
                {retrieved_documents if retrieved_documents else "None"}

                Instructions:
                - If documents are present, use them to derive rules.
                - If not, use general knowledge but admit uncertainty.
                - If user data is missing to decide, set eligible to null and list what's missing.
                - If user is eligible, mention exactly why.
                - Same for ineligibility.
                - Do not respond with anything except the required JSON.
            """

            raw_response = self.llm_client.run_json(system_prompt, user_prompt)
            eligibility = EligibilityCheckResponse(**raw_response)

            # If eligibility is uncertain, generate follow-up questions
            if eligibility.eligible is None and eligibility.missing_fields:
                follow_ups = self.question_generator.generate_questions(
                    missing_fields=eligibility.missing_fields,
                    scheme_name=eligibility.scheme_name
                )

                return {
                    "eligibility": eligibility.model_dump(),
                    "follow_up_questions": follow_ups
                }

            return eligibility.model_dump()

        except Exception as e:
            logger.error(f"EligibilityChecker failed: {e}")
            raise UdayamitraException("Failed to check eligibility", sys)
