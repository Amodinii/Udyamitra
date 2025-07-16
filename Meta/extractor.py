
'''
extractor.py - Extracts structured metadata from a user query using an LLM.
'''

from router.model import Metadata, UserProfile, Location
from utility.LLM import LLMClient
from Meta.location_normalizer import LocationNormalizer
import json
import re

class MetadataExtractor:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        self.llm_client = LLMClient(model=model)
        self.location_normalizer = LocationNormalizer()
    def extract_metadata(self, query: str) -> Metadata:
        system_prompt = """
        You are a metadata extraction assistant.
        Your job is to extract the following structured fields from a user query:
        - intents: A list of high-level user goals like 'explain', 'check_eligibility', 'register'
        - entities: Key entities such as the name of the scheme. If multiple schemes are mentioned, return them as a list.
        - user_profile: Includes 'user_type' (e.g., 'woman_entrepreneur', 'student') and 'location'. If no location is specified in the query, use "unknown" or "India" as a fallback.
        - If user_type is not explicitly mentioned, infer it from the context (e.g., if asking about subsidies, default to "entrepreneur").
        - Always return non-empty user_type and location if possible.

        Respond ONLY with the following JSON structure, ensure there are no additional comments or explanations:
        {
            "intents": [...],
            "entities": {
                "scheme": "..."
            },
            "user_profile": {
                "user_type": "...",
                "location": "..."
            }
        }
        """

        try:
            raw_output = self.llm_client.run_chat(system_prompt, query)
            print("Raw LLM output:", raw_output)
            json_blocks = re.findall(r'```json\s*(\{.*?\})\s*```', raw_output, re.DOTALL)
            if not json_blocks:
                json_blocks = re.findall(r'(\{.*\})', raw_output, re.DOTALL)
            if not json_blocks:
                raise ValueError("No valid JSON block found in LLM response.")
            metadata_dict = json.loads(json_blocks[-1])
            raw_loc = metadata_dict["user_profile"].get("location", "").strip().lower()
            if not raw_loc or raw_loc in ["unknown", "n/a", "India", "india"]:
                normalized_loc = {
                    "raw": raw_loc or "India",
                    "city": None,
                    "state": None,
                    "country": "India"
                }
            else:
                print(f"Getting structured location for: {raw_loc}")
                normalized_loc = self.location_normalizer.normalize(raw_loc)

            return Metadata(
                query=query,
                intents=metadata_dict["intents"],
                tools_required=[],  # will be populated later
                entities=metadata_dict["entities"],
                user_profile=UserProfile(
                    user_type=metadata_dict["user_profile"]["user_type"],
                    location=Location(**normalized_loc)
                )
            )
        except Exception as e:
            raise RuntimeError(f"Metadata extraction failed: {e}")