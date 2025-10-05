import os
import sys
import json
import re
import time
from dotenv import load_dotenv
from typing import List, Dict
from astrapy import DataAPIClient
from collections import defaultdict

from utility.LLM import LLMClient
from utility.model import InsightGeneratorOutput
from Logging.logger import logger
from Exception.exception import UdayamitraException

load_dotenv()

class AnalysisGenerator:
    # --- [MODIFICATION] Made the example for actionable_steps more explicit ---
    JSON_FORMAT_INSTRUCTIONS = """
    {
    "insight_summary": "A concise, one-sentence summary of the key insight based on the user's query and the data.",
    "detailed_explanation": "A detailed but easy-to-understand explanation of the insight. Directly address the user's query and explain the 'why' based on the analyzed data. If the user asked for top countries, explain that the data shows top destination ports as a proxy.",
    "potential_benefits": [
        "List of potential benefits or upsides for the user based on this analysis."
    ],
    "associated_risks": [
        "List of key risks or downsides the user should consider."
    ],
    "actionable_steps": [
        "A list of concrete, practical steps the user can take next. The steps should be numbered strings within the list, e.g., [\"1. Research the top importing countries.\", \"2. Analyze market trends.\"]"
    ],
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
        if not records:
            return {}

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
                raise UdayamitraException(f"Failed to query the trade database. Filter may be unsupported: {db_filter}", sys)
            
            if not records:
                return {
                    "insight_summary": f"No data found for '{product_keyword}'.",
                    "detailed_explanation": f"The analysis could not be completed because no records matching the product '{product_keyword}' were found in the trade database.",
                    "potential_benefits": [], "associated_risks": [], "actionable_steps": [],
                    "sources": [self.collection_name]
                }

            analysis_results = self._aggregate_data(records)
            
            system_prompt = "You are 'DataAnalystBot', an expert AI assistant specializing in trade data. Your purpose is to provide clear, actionable insights based on structured data. Your entire response MUST be a single, valid JSON object."
            user_prompt = f"""
            Generate an analysis for the user's query based on the provided structured data. Infer potential benefits, risks, and actionable steps for the user based on the data summary. Follow the JSON format precisely.

            USER QUERY: {user_query}
            STRUCTURED DATA ANALYSIS (Your ONLY source of information): {json.dumps(analysis_results, indent=2)}
            REQUIRED JSON OUTPUT FORMAT: {self.JSON_FORMAT_INSTRUCTIONS}
            """

            max_retries = 3
            delay = 2
            for attempt in range(max_retries):
                try:
                    response_dict = self.llm_client.run_json(system_prompt, user_prompt)
                    validated_output = InsightGeneratorOutput(**response_dict)
                    return validated_output.model_dump()
                except Exception as llm_error:
                    if "503" in str(llm_error) or "over capacity" in str(llm_error).lower():
                        logger.warning(f"LLM is over capacity. Retrying in {delay} seconds...")
                        if attempt < max_retries - 1:
                            time.sleep(delay)
                            delay *= 2
                        else:
                            logger.error("LLM is still over capacity after all retries.")
                            raise
                    else:
                        raise llm_error
        
        except Exception as e:
            logger.error(f"AnalysisGenerator failed: {e}", exc_info=True)
            raise UdayamitraException(f"Failed to generate structured insight: {e}", sys)

