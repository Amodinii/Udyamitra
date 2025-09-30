import os
import sys
import json
from dotenv import load_dotenv
from typing import List, Dict
from astrapy import DataAPIClient
from collections import defaultdict
from utility.LLM import LLMClient
from utility.model import InsightGeneratorOutput # Reusing the same output model
from Logging.logger import logger
from Exception.exception import UdayamitraException

# Load environment variables from .env file
load_dotenv()

class AnalysisGenerator:
    JSON_FORMAT_INSTRUCTIONS = """
    {
    "insight_summary": "A concise, one-sentence summary of the key insight based on the user's query and the data.",
    "detailed_explanation": "A detailed but easy-to-understand explanation of the insight. Directly address the user's query and explain the 'why' based on the analyzed data.",
    "data_summary": [
        "A list of the key data points that support the insight.",
        "Example: 1. Nhava Sheva Sea: $1,540,320.50 USD in total FOB value.",
        "Example: 2. Hamburg was the top destination port with 5,230 shipments."
    ],
    "potential_actions": [
        "List of potential actions or further questions the user might consider based on this analysis.",
        "Each action should be a separate string in this list."
    ],
    "sources": [
        "Should always contain the name of the data collection used, e.g., 'export_import_data'."
    ]
    }
    """

    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        try:
            logger.info("Starting AnalysisGenerator...")
            # Initialize LLM Client
            self.llm_client = LLMClient(model=model)
            
            # Initialize Astra DB Client for JSON API
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
        """
        A private function to perform analysis on the retrieved records.
        This is where you can add more complex logic like calculating totals, averages, etc.
        """
        if not records:
            return {"top_ports_by_value": [], "top_destinations_by_shipments": []}

        port_values = defaultdict(float)
        destination_counts = defaultdict(int)

        for rec in records:
            port_values[rec.get("indian_port")] += float(rec.get("fob_usd", 0))
            destination_counts[rec.get("destination_port")] += 1
        
        # Sort by value (descending) and take top 5
        sorted_ports = sorted(port_values.items(), key=lambda item: item[1], reverse=True)
        top_ports = [{"port": port, "total_fob_usd": value} for port, value in sorted_ports[:5]]

        # Sort by count (descending) and take top 5
        sorted_destinations = sorted(destination_counts.items(), key=lambda item: item[1], reverse=True)
        top_destinations = [{"destination": dest, "shipment_count": count} for dest, count in sorted_destinations[:5]]

        return {
            "total_records_analyzed": len(records),
            "top_ports_by_value": top_ports,
            "top_destinations_by_shipments": top_destinations
        }

    def generate_structured_insight(self, user_query: str, user_profile: dict) -> dict:
        try:
            # Simple keyword-based filtering.
            # A more advanced version could use an LLM to generate this filter.
            # For now, we'll just get all documents. A real implementation would filter.
            logger.info("Fetching records from the database...")
            records = list(self.collection.find()) # In a real app, add a filter here
            
            if not records:
                return {"insight_summary": "No data found to generate an analysis.", "detailed_explanation": "The required data collection was empty or could not be accessed.", "data_summary": [], "potential_actions": [], "sources": [self.collection_name]}

            # Perform analysis on the raw data
            analysis_results = self._aggregate_data(records)
            
            # --- Prompt for the LLM ---
            system_prompt = """
            You are 'DataAnalystBot', an expert AI assistant specializing in trade data analysis. Your purpose is to provide clear, data-driven insights based on structured query results from a database.

            You MUST adhere to the following principles:
            1.  **Strictly Data-Bound:** Your analysis MUST be based ONLY on the data provided in the "STRUCTURED DATA ANALYSIS" section. Do not invent facts or provide information not present in the data.
            2.  **Clarity and Simplicity:** Explain the findings in simple terms that a business owner or entrepreneur can easily understand.
            3.  **Strict JSON Output:** Your entire response MUST be a single, valid JSON object without any text or markdown formatting before or after it.
            """

            user_prompt = f"""
            Generate a clear and concise analysis based on the user's query and the provided data. Personalize the tone for the user's profile. Follow the required JSON output format precisely.

            === USER QUERY ===
            {user_query}

            === USER PROFILE ===
            {json.dumps(user_profile, indent=2)}

            === STRUCTURED DATA ANALYSIS (Your ONLY source of information) ===
            {json.dumps(analysis_results, indent=2)}

            === REQUIRED JSON OUTPUT FORMAT ===
            {self.JSON_FORMAT_INSTRUCTIONS}
            """

            response_dict = self.llm_client.run_json(system_prompt, user_prompt)
            
            # Validate and return as a dictionary
            validated_output = InsightGeneratorOutput(**response_dict)
            return validated_output.model_dump()
        
        except Exception as e:
            logger.error(f"AnalysisGenerator failed: {e}")
            raise UdayamitraException("Failed to generate structured insight", sys)