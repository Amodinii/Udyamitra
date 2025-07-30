'''
SchemeExplainer.py - This is the source code for the MCP server that will be specifically used to explain government schemes to users.
'''

import sys
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.LLM import LLMClient
from utility.model import SchemeMetadata, SchemeExplanationResponse

class SchemeExplainer:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        try:
            logger.info("Starting SchemeExplainer...")
            logger.info(f"Initializing SchemeExplainer with model: {model}")
            self.llm_client = LLMClient(model=model)
        except Exception as e:
            logger.error(f"Failed to initialize SchemeExplainer: {e}")
            raise UdayamitraException("Failed to initialize SchemeExplainer", sys)

    def explain_scheme(self, scheme_metadata: SchemeMetadata, retrieved_documents: str = None) -> SchemeExplanationResponse:
        try:
            system_prompt = """
            ROLE
            You are a precise, compliance-first explainer of Indian government schemes.

            OUTPUT (JSON ONLY — single object, exact keys/types/order):
            {
            "scheme_name": "<echo input scheme name exactly>",
            "explanation": "<clear, actionable plain text tailored to the user's profile>",
            "sources": ["<doc ref or URL>", ...]
            }

            RULES
            - Return JSON only (no prose/markdown/code fences). Keys exactly as above; no extras.
            - Ground facts in RETRIEVED DOCUMENTS when present; if absent/insufficient, you may use fallback knowledge but avoid speculation.
            - "sources": cite specific document titles/sections/URLs used; if none, return [].
            - Do not contradict documents. Do not invent thresholds/benefits not present in documents.
            - Escape quotes properly; arrays must be [] (never null).

            CONTENT GUIDELINES (for "explanation")
            - Tailor to user profile (location, user_type, sector, category if available).
            - Be concrete and useful: cover purpose, key benefits, core eligibility (high level), how to apply, documents needed, timelines, official portals, and practical tips.
            - Use simple, direct language (no legalese); prefer short sentences; ~150–300 words.
            - No follow-up questions, no meta commentary—just the explanation.

            FORMAT EXAMPLE (structure only):
            {"scheme_name":"ABC","explanation":"...","sources":["Doc A §2.1","https://example.gov/abc"]}
            """

            user_prompt = f"""
            TASK
            Explain the scheme for the user and output ONE JSON object that strictly follows the OUTPUT block from the system message.

            INPUTS
            === SCHEME METADATA (authoritative scheme name + user profile context) ===
            {scheme_metadata.model_dump_json(indent=2)}

            === RETRIEVED DOCUMENTS (primary source of truth; may be None) ===
            {retrieved_documents if retrieved_documents else "None"}

            INSTRUCTIONS
            - If documents are provided, rely on them for facts and cite them in "sources".
            - If documents are missing/partial, use general knowledge carefully and avoid speculation.
            - Tailor the explanation to the user's profile (e.g., location, user_type) present in metadata.
            - Keep language simple and actionable; include benefits, who qualifies (at a high level), application steps, key docs, timelines/fees if available, and official portals.
            - Return only the JSON object (no extra text).
            """

            raw_response = self.llm_client.run_json(system_prompt, user_prompt)
            validated_response = SchemeExplanationResponse(**raw_response)
            return validated_response

        except Exception as e:
            logger.error(f"SchemeExplainer failed: {e}")
            raise UdayamitraException("Failed to explain scheme", sys)