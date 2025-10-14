import os
import sys
import json
import re
import time
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from astrapy import DataAPIClient
from collections import defaultdict

from utility.LLM import LLMClient
from utility.model import AnalysisGeneratorOutput
from Logging.logger import logger
from Exception.exception import UdayamitraException
from Meta.location_normalizer import LocationNormalizer

load_dotenv()

class AnalysisGenerator:
    JSON_FORMAT_INSTRUCTIONS = """
    {
    "insight_summary": "A concise, impactful summary of the key business opportunity for the user.",
    "detailed_explanation": "Explain what this data means for the user's business, using 'you' and 'your'.",
    "data_summary": [
        "A bulleted list of the most important data points or findings that support the insight."
    ],
    "actionable_steps": [
        "Frame this as 'Your Next Steps'. Provide a clear checklist of actions the user can take, numbered as strings."
    ],
    "data_table": "Dynamically generate an array of objects for the top destination ports using the keys: Rank, Destination Port, Country (Inferred), Total Shipments. This field should be an empty list if a table is not relevant to the user's query.",
    "sources": ["export_import_data"]
    }
    """

    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        try:
            logger.info("Starting AnalysisGenerator...")
            self.llm_client = LLMClient(model=model)
            
            self.astra_db_endpoint = os.getenv("ASTRA_DB_ENDPOINT")
            self.astra_db_token = os.getenv("ASTRA_DB_TOKEN")
            self.collection_name = "export_import_data"
            
            if not all([self.astra_db_endpoint, self.astra_db_token]):
                raise ValueError("ASTRA_DB_ENDPOINT and ASTRA_DB_TOKEN must be set.")

            client = DataAPIClient(self.astra_db_token)
            db = client.get_database(self.astra_db_endpoint)
            self.collection = db.get_collection(self.collection_name)
            logger.info(f"Successfully connected to Astra DB collection: '{self.collection_name}'")
            self.location_normalizer = LocationNormalizer()

        except Exception as e:
            logger.error(f"Failed to initialize AnalysisGenerator: {e}")
            raise UdayamitraException(e, sys)
            
    # ==============================================================================
    # NEW METHOD: To classify the user's intent first
    # ==============================================================================
    def _classify_query_intent(self, user_query: str) -> str:
        """
        Uses the LLM to classify the user's query intent.
        Returns 'table_required' or 'direct_answer'.
        """
        system_prompt = """
        You are a query analysis expert. Your task is to determine if a user's question requires a detailed table of data to be answered effectively, or if a simple, direct textual answer is sufficient.

        Classify the query into one of two categories:
        1.  'table_required': For questions asking for lists, rankings, "top N", "which countries", "what are the main ports".
        2.  'direct_answer': For yes/no questions, simple factual lookups, or definition requests.

        Respond ONLY with a JSON object containing a single key "intent".
        """
        
        user_prompt = f"""
        Analyze the following user query:
        "{user_query}"

        Example 1:
        Query: "which are the top countries importing capacitors from india"
        Correct response: {{"intent": "table_required"}}

        Example 2:
        Query: "does middle east import capacitor from india?"
        Correct response: {{"intent": "direct_answer"}}
        
        Example 3:
        Query: "List the top 5 destination ports for our products."
        Correct response: {{"intent": "table_required"}}

        Now, classify the original query.
        """
        try:
            response = self.llm_client.run_json(system_prompt, user_prompt)
            intent = response.get("intent", "table_required") # Default to table if classification fails
            if intent not in ["table_required", "direct_answer"]:
                logger.warning(f"Unexpected intent '{intent}' received. Defaulting to 'table_required'.")
                return "table_required"
            return intent
        except Exception as e:
            logger.error(f"Failed to classify query intent: {e}. Defaulting to 'table_required'.")
            return "table_required" # Safe fallback

    # ==============================================================================
    # NEW HELPER METHOD: To sanitize LLM output before validation
    # ==============================================================================
    def _sanitize_llm_list_output(self, data: Any) -> List[str]:
        """Safely converts LLM output into a list of strings."""
        if isinstance(data, list):
            return [str(item) for item in data] # Ensure all items are strings
        if isinstance(data, str):
            # Split by newline, strip whitespace/empty lines, and remove common list markers
            items = [re.sub(r'^\s*[\*\-]?\s*\d*\.\s*', '', line).strip() for line in data.split('\n')]
            return [item for item in items if item] # Filter out empty strings
        return [] # Return an empty list for other unexpected types

    def _aggregate_data(self, records: List[Dict]) -> Dict:
        if not records: return {}
        port_values = defaultdict(float)
        destination_counts = defaultdict(int)
        for rec in records:
            port_values[rec.get("indian_port")] += float(rec.get("fob_usd", 0))
            destination_counts[rec.get("destination_port")] += 1
        sorted_ports = sorted(port_values.items(), key=lambda item: item[1], reverse=True)
        top_ports = [{"port": port, "total_fob_usd": f"{value:,.2f}"} for port, value in sorted_ports[:5]]
        sorted_destinations = sorted(destination_counts.items(), key=lambda item: item[1], reverse=True)
        top_destinations = [{"destination_port": dest, "shipment_count": count} for dest, count in sorted_destinations[:5]]
        return {
            "total_records_analyzed": len(records),
            "top_indian_ports_by_value": top_ports,
            "top_destination_ports_by_shipments": top_destinations
        }

    def _build_data_table(self, top_destinations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        table = []
        for idx, item in enumerate(top_destinations):
            destination_port = item.get("destination_port") or ""
            shipment_count = item.get("shipment_count") or 0
            inferred_country = ""
            try:
                if destination_port:
                    normalized = self.location_normalizer.normalize(destination_port)
                    inferred_country = normalized.get("country") or ""
            except Exception as e:
                logger.warning(f"Failed to normalize location '{destination_port}': {e}")
                inferred_country = ""
            table.append({
                "Rank": idx + 1,
                "Destination Port": destination_port,
                "Country (Inferred)": inferred_country,
                "Total Shipments": shipment_count
            })
        return table

    def _to_markdown_table(self, data_table: List[Dict[str, Any]]) -> str:
        if not data_table:
            return ""
        headers = list(data_table[0].keys())
        header_row = "| " + " | ".join(headers) + " |"
        divider = "| " + " | ".join(["---"] * len(headers)) + " |"
        rows = []
        for row in data_table:
            cells = []
            for h in headers:
                v = row.get(h, "")
                if v is None: v = ""
                cell = str(v).replace("\n", " ")
                cells.append(cell)
            rows.append("| " + " | ".join(cells) + " |")
        return "\n".join([header_row, divider] + rows)

    def generate_structured_insight(self, user_query: str, user_profile: dict, entities: dict) -> dict:
        try:
            # STEP 1: Classify the user's intent
            intent = self._classify_query_intent(user_query)
            logger.info(f"User query classified with intent: '{intent}'")

            # STEP 2: Database query
            product_keyword = entities.get("product")
            db_filter = {}
            if product_keyword:
                logger.info(f"Filtering database records for product keyword: '{product_keyword}'")
                regex_pattern = re.compile(f".*{re.escape(product_keyword)}.*", re.IGNORECASE)
                db_filter = {"item_description": {"$regex": regex_pattern.pattern}}
            else:
                logger.warning("No 'product' entity found. Analyzing all data.")

            records = list(self.collection.find(filter=db_filter))
            logger.info(f"Found {len(records)} records in the database.")

            if not records:
                return {
                    "insight_summary": f"No data found for '{product_keyword}'.",
                    "detailed_explanation": "The analysis could not be completed because no records matching the specified product were found in the trade database.",
                    "data_summary": [],
                    "actionable_steps": ["Try searching for a different product.", "Check if the data ingestion for this product was successful."],
                    "data_table": [],
                    "sources": [self.collection_name]
                }
            
            analysis_results = self._aggregate_data(records)

            # STEP 3: Conditional logic based on intent
            if intent == "table_required":
                top_destinations = analysis_results.get("top_destination_ports_by_shipments", [])
                data_table = self._build_data_table(top_destinations)
                markdown_table = self._to_markdown_table(data_table)

                system_prompt = (
                    "You are a 'Business Growth Advisor AI'. Produce a single JSON object. "
                    "Use the provided data and markdown table to generate a detailed textual analysis. "
                    "DO NOT produce or modify a 'data_table' field."
                )
                user_prompt = f"""
                Generate the textual parts of the analysis based on the user's query and the data provided.
                USER QUERY: {user_query}
                USER PROFILE: {json.dumps(user_profile, indent=2)}
                STRUCTURED DATA ANALYSIS: {json.dumps(analysis_results, indent=2)}
                MARKDOWN_TABLE (for your reference):
                {markdown_table}
                Output MUST be a single JSON object with the keys: insight_summary, detailed_explanation, data_summary, actionable_steps, sources.
                """
            else: # intent == "direct_answer"
                data_table = []
                markdown_table = ""
                system_prompt = (
                    "You are a 'Business Growth Advisor AI'. Your goal is to directly answer the user's question based on the provided data summary. "
                    "Do not suggest presenting a table. Formulate a concise and direct answer. "
                    "Respond in a single JSON object."
                )
                user_prompt = f"""
                Directly answer the user's question using the provided data.
                USER QUERY: {user_query}
                USER PROFILE: {json.dumps(user_profile, indent=2)}
                STRUCTURED DATA ANALYSIS: {json.dumps(analysis_results, indent=2)}
                For example, if the query is "does the middle east import capacitors?" and the data shows shipments to Dubai, a good insight summary would be "Yes, there is evidence of capacitor exports to the Middle East, specifically to ports like Dubai."
                Output MUST be a single JSON object with the keys: insight_summary, detailed_explanation, data_summary, actionable_steps, sources.
                Set `data_summary` to a few key points that support your answer.
                """
            
            # STEP 4: LLM call
            max_retries = 3
            delay = 2
            textual_response = None
            for attempt in range(max_retries):
                try:
                    textual_response = self.llm_client.run_json(system_prompt, user_prompt)
                    break
                except Exception as llm_error:
                    logger.warning(f"LLM attempt {attempt+1} failed: {llm_error}")
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.error("LLM failed after retries; falling back to deterministic text.")
                        textual_response = None
            
            # STEP 5: Assemble response, using fallback if necessary
            if not textual_response or not isinstance(textual_response, dict):
                # Fallback logic
                insight_summary = f"Analysis for your query on '{product_keyword}'."
                detailed_explanation = "Based on the data, here are the key findings."
                data_summary = [f"Total records analyzed: {analysis_results.get('total_records_analyzed', 0)}"]
                if data_table:
                    detailed_explanation += "\n\n" + markdown_table
                    data_summary.extend([f"{row['Rank']}. {row['Destination Port']} — {row['Total Shipments']} shipments" for row in data_table][:3])
                actionable_steps = ["Review the data summary to inform your next business decision."]
                sources = [self.collection_name]
                combined = {
                    "insight_summary": insight_summary,
                    "detailed_explanation": detailed_explanation,
                    "data_summary": data_summary,
                    "actionable_steps": actionable_steps,
                    "data_table": data_table,
                    "sources": sources
                }
            else:
                # ==============================================================================
                # MODIFIED SECTION: Sanitize LLM response before combining
                # ==============================================================================
                insight_summary = str(textual_response.get("insight_summary") or "")
                detailed_explanation = str(textual_response.get("detailed_explanation") or "")
                
                # Use the new helper to sanitize list outputs
                data_summary = self._sanitize_llm_list_output(textual_response.get("data_summary"))
                actionable_steps = self._sanitize_llm_list_output(textual_response.get("actionable_steps"))
                
                sources = self._sanitize_llm_list_output(textual_response.get("sources"))
                if not sources:
                    sources = [self.collection_name]

                combined = {
                    "insight_summary": insight_summary,
                    "detailed_explanation": detailed_explanation,
                    "data_summary": data_summary,
                    "actionable_steps": actionable_steps,
                    "data_table": data_table, 
                    "sources": sources
                }
            
            validated_output = AnalysisGeneratorOutput(**combined)
            return validated_output.model_dump()

        except Exception as e:
            logger.error(f"AnalysisGenerator failed: {e}", exc_info=True)
            raise UdayamitraException(f"Failed to generate structured insight: {e}", sys)