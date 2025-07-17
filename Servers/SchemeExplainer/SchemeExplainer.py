'''
SchemeExplainer.py - This is the source code for the MCP server that will be specifically used to explain government schemes to users.
'''

import sys
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.LLM import LLMClient
from utility.model import SchemeExplanationResponse

class SchemeExplainer:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        try:
            logger.info("Starting SchemeExplainer...")
            logger.info(f"Initializing SchemeExplainer with model: {model}")
            self.llm_client = LLMClient(model=model)
        except Exception as e:
            logger.error(f"Failed to initialize SchemeExplainer: {e}")
            raise UdayamitraException("Failed to initialize SchemeExplainer", sys)

    def explain_scheme(self, scheme_metadata: dict, retrieved_documents: str = None) -> SchemeExplanationResponse:
        try:
            system_prompt = """
                You are a knowledgeable assistant that explains government schemes in India. 
                Given a scheme name and metadata about the user's context (location, user type, etc.), 
                you must generate a clear, helpful explanation of the scheme that is customized for the user.
                You may optionally be given a list of documents or excerpts as context to help you generate the explanation.
                Always respond in a structured JSON format that follows the specified schema, we don't need any additional comments or explanations:
                {
                    "scheme_name": "<name of the scheme>",
                    "explanation": "<detailed explanation customized to the user profile>",
                    "follow_up_suggestions": ["<optional suggestion>", "..."],
                    "sources": ["<optional source links or documents>", "..."]
                }
            """

            user_prompt = f"""
                Please explain the following scheme(s) to the user:
                Metadata:
                {scheme_metadata}
                Retrieved Documents (if any):
                {retrieved_documents if retrieved_documents else "None"}

                Requirements:
                - If documents are provided, base your explanation and sources on them.
                - If not provided, respond using your general knowledge.
                - The explanation should be specific to the user's location and user type.
                - Mention key benefits, eligibility, and how the scheme is useful to them.
                - Use simple and direct language.
                - Respond only in JSON format, matching the given schema exactly.
            """

            raw_response = self.llm_client.run_json(system_prompt, user_prompt)
            validated_response = SchemeExplanationResponse(**raw_response)
            return validated_response

        except Exception as e:
            logger.error(f"SchemeExplainer failed: {e}")
            raise UdayamitraException("Failed to explain scheme", sys)