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
            You are a knowledgeable assistant that explains government schemes in India.

            Your goals-
            Very Important:
            - If documents are provided, you **must rely primarily on them** for facts, structure, and sources.
            - Use your own knowledge **only when necessary** to fill small gaps — never contradict or override the documents.
            - Cite the document sources where possible.
            - If documents are not given, use your own knowledge.

            You must respond in **valid JSON** with this exact schema:

            {
            "scheme_name": "<name of the scheme>",
            "explanation": "<detailed explanation customized to the user profile>",
            "sources": ["<optional source links or documents>", "..."]
            }

            Important:
            - Escape all quotes properly. Ensure the output is clean, well-structured, and parseable.
            """


            user_prompt = f"""
            Please explain the following scheme for a user.

            === SCHEME METADATA ===
            {scheme_metadata.model_dump_json(indent=2)}

            === RETRIEVED DOCUMENTS (optional) ===
            {retrieved_documents if retrieved_documents else "None"}

            Your explanation must:
            - Be detailed and packed with helpful, real information.
            - Tailor content to the user's profile (especially their location and user_type).
            - Mention key benefits, eligibility, application process (if relevant), and practical value.
            - If documents are provided, ground the explanation and sources in them. Otherwise, use your knowledge.
            - Use simple and direct language (no legalese or fluff).
            - Highlight actionable next steps if appropriate and also highlight the sources.

            Strictl Requirement:
            - Don't mention Follow-up questions.
            """

            raw_response = self.llm_client.run_json(system_prompt, user_prompt)
            validated_response = SchemeExplanationResponse(**raw_response)
            return validated_response

        except Exception as e:
            logger.error(f"SchemeExplainer failed: {e}")
            raise UdayamitraException("Failed to explain scheme", sys)