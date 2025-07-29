from utility.model import Metadata, UserProfile, Location, ConversationState
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.LLM import LLMClient
from Meta.location_normalizer import LocationNormalizer
import json
import sys
import re

class MetadataExtractor:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        try:
            logger.info(f"Initializing MetadataExtractor with model: {model}")
            self.llm_client = LLMClient(model=model)
            self.location_normalizer = LocationNormalizer()
        except Exception as e:
            logger.error(f"Failed to initialize MetadataExtractor: {e}")
            raise UdayamitraException("Failed to initialize MetadataExtractor", sys)

    def extract_metadata(self, query: str, state: ConversationState | None = None) -> Metadata:
        try:
            logger.info(f"Extracting metadata from query: {query}")

            context_hint = ""
            if state:
                last_tool = state.last_tool_used or ""
                last_msg = state.messages[-1].content if state.messages else ""
                last_entities = state.context_entities or {}

                context_hint = f"""
Previous tool used: {last_tool}
Last assistant message: {last_msg}
Previously detected entities (if any): {json.dumps(last_entities)}
Use this context if the current query is ambiguous or a follow-up.
""".strip()

            # Final user query with context injected
            contextual_query = f"{context_hint}\n\nCurrent query: {query}" if context_hint else query

            system_prompt = """
You are a metadata extraction assistant.
Your job is to extract the following structured fields from a user query:
- intents: A list of high-level user goals like 'explain', 'check_eligibility', 'register'
- entities: Key entities such as the name of the scheme. If multiple schemes are mentioned, return them as a list.
- user_profile: Includes 'user_type' (e.g., 'woman_entrepreneur', 'student') and 'location'. If no location is specified in the query, use "unknown" or "India" as a fallback.
- If user_type is not explicitly mentioned, infer it from the context (e.g., if asking about subsidies, default to "entrepreneur").
- Always return non-empty user_type and location if possible.

Respond ONLY with the following JSON structure:
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

- Make sure all keys are enclosed in double quotes and properly comma-separated.
""".strip()

            raw_output = self.llm_client.run_chat(system_prompt, contextual_query)
            logger.info(f"Raw output from LLM:\n{raw_output}")

            # Clean output to strip ```json and ``` wrappers if present
            def clean_json(raw: str) -> str:
                raw = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE)
                raw = raw.replace("```", "").strip()
                json_match = re.search(r"\{.*\}", raw, re.DOTALL)
                if not json_match:
                    raise ValueError("No valid JSON object found in LLM response")
                return json_match.group(0)

            cleaned_json = clean_json(raw_output)
            metadata_dict = json.loads(cleaned_json)

            logger.info(f"Metadata extracted:\n{json.dumps(metadata_dict, indent=2)}")

            # Normalize location
            raw_loc = metadata_dict["user_profile"].get("location", "").strip().lower()
            if not raw_loc or raw_loc in ["unknown", "n/a", "india"]:
                normalized_loc = {
                    "raw": raw_loc or "India",
                    "city": None,
                    "state": None,
                    "country": "India"
                }
            else:
                normalized_loc = self.location_normalizer.normalize(raw_loc)

            metadata = Metadata(
                query=query,
                intents=metadata_dict["intents"],
                tools_required=[],  # will be added later by planner
                entities=metadata_dict["entities"],
                user_profile=UserProfile(
                    user_type=metadata_dict["user_profile"]["user_type"],
                    location=Location(**normalized_loc)
                )
            )

            # Update conversation state for follow-ups
            if state:
                state.context_entities.update(metadata_dict["entities"])

            return metadata

        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            raise UdayamitraException(f"Metadata extraction failed: {e}", sys)