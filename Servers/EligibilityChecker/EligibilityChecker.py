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
            ROLE
            Compliance-first eligibility checker for Indian government schemes.

            OUTPUT (JSON ONLY — single object, exact keys/types):
            {
            "scheme_name": "<echo input>",
            "eligible": true | false | null,
            "reasons": ["<string>", ...],
            "missing_fields": ["<string>", ...],
            "sources": ["<doc ref or URL>", ...]
            }

            RULES
            - Return JSON only (no prose/markdown). Keys exactly as above; lowercase booleans; arrays use [] (never null).
            - Ground in RETRIEVED DOCUMENTS when present; if absent/insufficient, you may use fallback knowledge but note uncertainty.
            - Set "eligible":
            • true  → all mandatory criteria satisfied per documents  
            • false → any disqualifier met per documents  
            • null  → required user data missing OR rules unclear/contradictory (list precise field names in "missing_fields")
            - "sources": cite specific document sections/URLs used; if none, [].
            - If documents contradict, prefer the most official/specific; otherwise set eligible=null and explain in "reasons".
            - Do not invent thresholds/facts not in documents.

            PROCESS (silent)
            Extract required fields → compare with USER PROFILE → decide (true/false/null) → write brief, rule‑grounded reasons → output JSON.

            FORMAT EXAMPLE (structure only):
            {"scheme_name":"ABC","eligible":null,"reasons":["Income missing"],"missing_fields":["annual_income"],"sources":["Doc C §3.4"]}
            """

            user_prompt = f"""
            TASK
            Evaluate the user's eligibility for the scheme below and respond with a single JSON object that STRICTLY follows the OUTPUT CONTRACT from the system message.

            INPUTS
            === SCHEME ===
            {request.scheme_name}

            === USER PROFILE (JSON) ===
            {request.user_profile.model_dump_json(indent=2)}

            === CONTEXT ENTITIES (optional) ===
            {request.context_entities if request.context_entities else "{}"}

            === ORIGINAL USER QUERY (optional) ===
            {request.query or "Not provided"}

            === RETRIEVED DOCUMENTS (primary source of truth) ===
            {retrieved_documents if retrieved_documents else "None"}

            INSTRUCTIONS
            - Treat "RETRIEVED DOCUMENTS" as authoritative when present; cite the exact document references you used in "sources".
            - If documents are missing/insufficient or not provided ("None"), you may use fallback knowledge, but reflect uncertainty in "reasons" and/or set "eligible": null when appropriate.
            - If required user inputs are missing (e.g., income, age, category, geography), set "eligible": null and list those exact field names in "missing_fields".
            - If clearly eligible or ineligible, set "eligible" to true/false and provide concise rule-grounded "reasons".
            - Return only the JSON object defined in the OUTPUT CONTRACT. No extra text.

            OUTPUT
            Return exactly one JSON object. No preamble. No code fences. No trailing commentary.
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
