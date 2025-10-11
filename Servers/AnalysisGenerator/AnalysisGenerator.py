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
from utility.model import AnalysisGeneratorOutput # Use the new, dedicated output model
from Logging.logger import logger
from Exception.exception import UdayamitraException

load_dotenv()

class AnalysisGenerator:
    # New instructions that match the new AnalysisGeneratorOutput model
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
    "data_table": "Dynamically generate an array of objects for the top destination ports using the keys: Rank, Destination Port, Country (Inferred), Total Shipments",
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

        except Exception as e:
            logger.error(f"Failed to initialize AnalysisGenerator: {e}")
            raise UdayamitraException(e, sys)
            
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
        """
        Build a dynamic data_table (no hardcoding) from top_destinations list.
        Each row will have: Rank, Destination Port, Country (Inferred), Total Shipments.
        Country (Inferred) left empty here to avoid incorrect inference; LLM can mention it in explanation if helpful.
        """
        table = []
        for idx, item in enumerate(top_destinations):
            destination_port = item.get("destination_port") or ""
            shipment_count = item.get("shipment_count") or 0
            # Ensure values are safe for frontend rendering
            table.append({
                "Rank": idx + 1,
                "Destination Port": destination_port,
                "Country (Inferred)": "",  # leave blank (or fill if you have a mapping)
                "Total Shipments": shipment_count
            })
        return table

    def _to_markdown_table(self, data_table: List[Dict[str, Any]]) -> str:
        """
        Convert data_table (list of dicts) into a GitHub-Flavored Markdown table string.
        This is deterministic and safe (no LLM required).
        """
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
                if v is None:
                    v = ""
                # sanitize newlines so JSON stays safe
                cell = str(v).replace("\n", " ")
                cells.append(cell)
            rows.append("| " + " | ".join(cells) + " |")

        return "\n".join([header_row, divider] + rows)


    def generate_structured_insight(self, user_query: str, user_profile: dict, entities: dict) -> dict:
        try:
            product_keyword = entities.get("product")
            db_filter = {}
            if product_keyword:
                logger.info(f"Filtering database records for product keyword: '{product_keyword}'")
                regex_pattern = re.compile(f".*{re.escape(product_keyword)}.*", re.IGNORECASE)
                db_filter = {"item_description": {"$regex": regex_pattern.pattern}}
            else:
                logger.warning("No 'product' entity found. Analyzing all data.")

            try:
                logger.info(f"Executing DB find with filter: {db_filter}")
                records = list(self.collection.find(filter=db_filter))
                logger.info(f"Found {len(records)} records in the database.")
            except Exception as db_error:
                logger.error(f"Database query failed: {db_error}", exc_info=True)
                raise UdayamitraException(f"Failed to query trade database: {db_filter}", sys)

            if not records:
                # Return a valid JSON object that matches the new model (data_table as empty list)
                return {
                    "insight_summary": f"No data found for '{product_keyword}'.",
                    "detailed_explanation": "The analysis could not be completed because no records matching the specified product were found in the trade database.",
                    "data_summary": [],
                    "actionable_steps": ["Try searching for a different product.", "Check if the data ingestion for this product was successful."],
                    "data_table": [],
                    "sources": [self.collection_name]
                }

            # Aggregate DB results (existing logic)
            analysis_results = self._aggregate_data(records)
            top_destinations = analysis_results.get("top_destination_ports_by_shipments", [])

            # --- Build deterministic data_table from DB results (no hardcoding) ---
            data_table = self._build_data_table(top_destinations)
            # Create a markdown table string (deterministic) so frontend can show Markdown if needed
            markdown_table = self._to_markdown_table(data_table)

            # --- Ask LLM to produce textual narrative only (not the data_table) ---
            system_prompt = (
                "You are a 'Business Growth Advisor AI'. "
                "Produce a single JSON object containing ONLY these fields: "
                "insight_summary, detailed_explanation, data_summary (array of strings), actionable_steps (array of strings), sources (array). "
                "DO NOT produce or modify a 'data_table' field — the caller will provide the table separately. "
                "detailed_explanation may optionally reference the provided 'markdown_table' but must still be valid JSON strings (no raw objects)."
            )

            user_prompt = f"""
            Generate the textual parts of the analysis (insight_summary, detailed_explanation, data_summary, actionable_steps).
            Use the structured information to make these answers actionable and tailored to the user's profile.
            Do NOT output or modify 'data_table'; that will be merged by the caller.

            USER QUERY: {user_query}
            USER PROFILE: {json.dumps(user_profile, indent=2)}
            STRUCTURED DATA ANALYSIS: {json.dumps(analysis_results, indent=2)}
            TOP DESTINATIONS (raw): {json.dumps(top_destinations, indent=2)}
            MARKDOWN_TABLE (for your reference only - you should not reproduce it as JSON): 
            {markdown_table}

            Output MUST be a single JSON object with the keys:
            - insight_summary (string)
            - detailed_explanation (string)  -- you may include readable references to the table but avoid inserting raw JSON objects
            - data_summary (array of short strings)
            - actionable_steps (array of short strings)
            - sources (array of strings)
            """

            # Try asking the LLM to fill textual fields; if it fails, we will fallback to a deterministic summary
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

            # If LLM failed or returned unexpected, create deterministic textual fallback
            if not textual_response or not isinstance(textual_response, dict):
                # Deterministic fallback content (useful and safe)
                insight_summary = f"Top destination ports identified for your query ({len(data_table)} entries)."
                detailed_explanation = "Below is a table summarizing top destination ports and shipment counts.\n\n" + markdown_table
                data_summary = [
                    f"{row['Rank']}. {row['Destination Port']} — {row['Total Shipments']} shipments"
                    for row in data_table
                ][:5]
                actionable_steps = [
                    "1. Validate demand in the top destinations by contacting potential buyers.",
                    "2. Investigate regulatory/import requirements for the top countries.",
                    "3. Prioritize market-entry research for the top 1-2 ports."
                ]
                sources = [self.collection_name]
                combined = {
                "insight_summary": insight_summary,
                "detailed_explanation": detailed_explanation,  
                "data_summary": data_summary,
                "actionable_steps": actionable_steps,
                "data_table": data_table, 
                "sources": sources
                }
                # Validate with the Pydantic model if you want
                validated_output = AnalysisGeneratorOutput(**{k: combined[k] for k in ["insight_summary","detailed_explanation","data_summary","actionable_steps","data_table","sources"]})
                return validated_output.model_dump()

            # Merge deterministic data_table with the LLM textual output
            # LLM response must contain textual keys as per instructions; defensively extract them
            insight_summary = textual_response.get("insight_summary", "").strip() if isinstance(textual_response.get("insight_summary"), str) else str(textual_response.get("insight_summary") or "")
            detailed_explanation = textual_response.get("detailed_explanation", "").strip() if isinstance(textual_response.get("detailed_explanation"), str) else str(textual_response.get("detailed_explanation") or "")
            data_summary = textual_response.get("data_summary") or []
            actionable_steps = textual_response.get("actionable_steps") or []
            sources = textual_response.get("sources") or [self.collection_name]

            combined = {
                "insight_summary": insight_summary,
                "detailed_explanation": detailed_explanation + ("\n\n" + markdown_table if markdown_table and "table" not in detailed_explanation.lower() else ""),
                "data_summary": data_summary,
                "actionable_steps": actionable_steps,
                "data_table": data_table,
                "sources": sources
            }

            # Validate against the output model and return
            validated_output = AnalysisGeneratorOutput(**combined)
            return validated_output.model_dump()

        except Exception as e:
            logger.error(f"AnalysisGenerator failed: {e}", exc_info=True)
            raise UdayamitraException(f"Failed to generate structured insight: {e}", sys)
