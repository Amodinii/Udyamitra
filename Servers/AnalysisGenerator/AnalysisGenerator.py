import os
import sys
import json
import re
import asyncio
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from fastmcp import Client
from astrapy import DataAPIClient
from collections import defaultdict

from utility.LLM import LLMClient
from utility.model import AnalysisGeneratorOutput
from Logging.logger import logger
from Exception.exception import UdayamitraException
from Meta.location_normalizer import LocationNormalizer

load_dotenv()

# --- ADDED: URLs for data sources ---
RETRIEVER_URL = "http://127.0.0.1:10000/retrieve-scheme/mcp"
RETRIEVER_TOOL_NAME = "retrieve_documents"


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
    "sources": ["export_import_data", "exp_scheme_chunks"]
    }
    """

    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        try:
            logger.info("Starting AnalysisGenerator...")
            self.llm_client = LLMClient(model=model)
            self.location_normalizer = LocationNormalizer()

            # --- ADDED: Connection to structured data collection ---
            self.astra_db_endpoint = os.getenv("ASTRA_DB_ENDPOINT")
            self.astra_db_token = os.getenv("ASTRA_DB_TOKEN")
            self.structured_collection_name = "export_import_data"
            
            if not all([self.astra_db_endpoint, self.astra_db_token]):
                raise ValueError("ASTRA_DB_ENDPOINT and ASTRA_DB_TOKEN must be set.")

            client = DataAPIClient(self.astra_db_token)
            db = client.get_database(self.astra_db_endpoint)
            self.structured_collection = db.get_collection(self.structured_collection_name)
            logger.info(f"Successfully connected to Astra DB collection: '{self.structured_collection_name}'")
            # --- END ADDED ---

        except Exception as e:
            logger.error(f"Failed to initialize AnalysisGenerator: {e}")
            raise UdayamitraException(e, sys)

    def _classify_query_intent(self, user_query: str) -> str:
        # (This function remains unchanged)
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

        Now, classify the original query.
        """
        try:
            response = self.llm_client.run_json(system_prompt, user_prompt)
            intent = response.get("intent", "table_required")
            if intent not in ["table_required", "direct_answer"]:
                return "table_required"
            return intent
        except Exception:
            return "table_required"

    def _sanitize_llm_list_output(self, data: Any) -> List[str]:
        # (This function remains unchanged)
        if isinstance(data, list):
            return [str(item) for item in data]
        if isinstance(data, str):
            items = [re.sub(r'^\s*[\*\-]?\s*\d*\.\s*', '', line).strip() for line in data.split('\n')]
            return [item for item in items if item]
        return []

    def _aggregate_data(self, records: List[Dict]) -> Dict:
        # (This function remains unchanged)
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

    def _build_data_table(self, top_destinations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # (This function remains unchanged)
        table = []
        for idx, item in enumerate(top_destinations):
            destination_port = item.get("destination_port") or ""
            shipment_count = item.get("shipment_count") or 0
            inferred_country = ""
            try:
                if destination_port:
                    normalized = self.location_normalizer.normalize(destination_port)
                    inferred_country = normalized.get("country") or ""
            except Exception:
                inferred_country = ""
            table.append({
                "Rank": idx + 1,
                "Destination Port": destination_port,
                "Country (Inferred)": inferred_country,
                "Total Shipments": shipment_count
            })
        return table

    def _to_markdown_table(self, data_table: List[Dict[str, Any]]) -> str:
        # (This function remains unchanged)
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
                cell = str(v).replace("\n", " ")
                cells.append(cell)
            rows.append("| " + " | ".join(cells) + " |")
        return "\n".join([header_row, divider] + rows)

    # --- ADDED: Helper to fetch vector data ---
    async def _fetch_vector_data(self, user_query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        logger.info(f"Querying retriever with: '{user_query}'")
        try:
            async with Client(RETRIEVER_URL) as retriever_client:
                response = await retriever_client.call_tool(
                    RETRIEVER_TOOL_NAME,
                    {
                        "query": user_query,
                        "caller_tool": "AnalysisGenerator",
                        "top_k": top_k
                    }
                )
            docs_from_retriever = response.data.result
            if not isinstance(docs_from_retriever, list):
                docs_from_retriever = []
            
            logger.info(f"[AnalysisGenerator] Retrieved {len(docs_from_retriever)} vector documents.")
            return [vars(d) for d in docs_from_retriever]
        except Exception as e:
            logger.error(f"Failed to fetch vector documents: {e}", exc_info=True)
            return [] # Return empty list on failure

    # --- ADDED: Helper to fetch structured data ---
    async def _fetch_structured_data(self, entities: dict) -> List[Dict[str, Any]]:
        product_keyword = entities.get("item") or entities.get("product") # Check for 'item' or 'product'
        db_filter = {}
        if product_keyword:
            logger.info(f"Filtering structured database for product keyword: '{product_keyword}'")
            # Using $regex with re.IGNORECASE equivalent
            db_filter = {"item_description": {"$regex": f"(?i){re.escape(product_keyword)}"}}
        else:
            logger.warning("No 'product' or 'item' entity found. Analyzing all structured data.")

        try:
            # .find() from astrapy is not async, run in default executor
            loop = asyncio.get_running_loop()
            records = await loop.run_in_executor(
                None, 
                lambda: list(self.structured_collection.find(filter=db_filter, limit=1000)) # Added limit
            )
            logger.info(f"Found {len(records)} structured records in the database.")
            return records
        except Exception as e:
            logger.error(f"Failed to fetch structured documents: {e}", exc_info=True)
            return [] # Return empty list on failure

    # --- ENTIRE FUNCTION REWRITTEN ---
    async def generate_structured_insight(self, user_query: str, user_profile: dict, entities: dict) -> dict:
        try:
            # Step 1: Classify intent (this is fast, can be sync)
            intent = self._classify_query_intent(user_query)
            logger.info(f"User query classified with intent: '{intent}'")

            # Step 2: Fetch data in parallel
            logger.info("Fetching vector and structured data in parallel...")
            vector_docs, structured_records = await asyncio.gather(
                self._fetch_vector_data(user_query=user_query),
                self._fetch_structured_data(entities=entities)
            )
            
            # Combine vector doc content for the LLM prompt
            vector_context = "\n\n".join([doc.get("content", "") for doc in vector_docs])
            source_names = list(set([doc.get("metadata", {}).get("source", "exp_scheme_chunks") for doc in vector_docs]))
            if structured_records and self.structured_collection_name not in source_names:
                source_names.append(self.structured_collection_name)

            # Step 3: Analyze structured data
            if not structured_records:
                logger.warning("No structured records found. Analysis will be limited.")
                return {
                    "insight_summary": f"No structured trade data found for '{entities.get('item','product')}'",
                    "detailed_explanation": "The analysis could not be completed because no structured records matching the specified product were found in the trade database.",
                    "data_summary": [f"Vector search for context returned {len(vector_docs)} related documents.", vector_context[:500] + "..."],
                    "actionable_steps": ["Try searching for a different product.", "Check if the data ingestion for this product was successful."],
                    "data_table": [],
                    "sources": source_names
                }
            
            analysis_results = self._aggregate_data(structured_records)

            # Step 4: Build Data Table if needed
            data_table = []
            markdown_table = ""
            if intent == "table_required":
                top_destinations = analysis_results.get("top_destination_ports_by_shipments", [])
                data_table = self._build_data_table(top_destinations)
                markdown_table = self._to_markdown_table(data_table)

            # Step 5: Generate LLM Prompts
            if intent == "table_required":
                system_prompt = (
                    "You are a 'Business Growth Advisor AI'. Produce a single JSON object. "
                    "Use the provided structured data, markdown table, and vector context to generate a detailed textual analysis. "
                    "DO NOT produce or modify a 'data_table' field."
                )
                # --- MODIFICATION: Added 'sources' to the output keys and 'AVAILABLE SOURCES' to the prompt ---
                user_prompt = f"""
                Generate the textual parts of the analysis based on the user's query and the data provided.
                USER QUERY: {user_query}
                USER PROFILE: {json.dumps(user_profile, indent=2)}
                
                STRUCTURED DATA ANALYSIS (From 'export_import_data'): 
                {json.dumps(analysis_results, indent=2)}
                
                MARKDOWN_TABLE (for your reference):
                {markdown_table}

                VECTOR CONTEXT (From 'exp_scheme_chunks' for background info):
                {vector_context if vector_context else "No vector context found."}
                
                AVAILABLE SOURCES:
                {json.dumps(source_names)}

                Output MUST be a single JSON object with the keys: insight_summary, detailed_explanation, data_summary, actionable_steps, sources.
                The 'sources' field MUST be a list of strings, populated from the AVAILABLE SOURCES list.
                """
            else: # direct_answer
                system_prompt = (
                    "You are a 'Business Growth Advisor AI'. Your goal is to directly answer the user's question. "
                    "Base your answer on the STRUCTURED DATA ANALYSIS and use the VECTOR CONTEXT for background. "
                    "Do not suggest presenting a table. Respond in a single JSON object."
                )
                # --- MODIFICATION: Added 'sources' to the output keys and 'AVAILABLE SOURCES' to the prompt ---
                user_prompt = f"""
                Directly answer the user's question using the provided data.
                USER QUERY: {user_query}
                USER PROFILE: {json.dumps(user_profile, indent=2)}

                STRUCTURED DATA ANALYSIS (From 'export_import_data'): 
                {json.dumps(analysis_results, indent=2)}

                VECTOR CONTEXT (From 'exp_scheme_chunks' for background info):
                {vector_context if vector_context else "No vector context found."}
                
                AVAILABLE SOURCES:
                {json.dumps(source_names)}
                
                Output MUST be a single JSON object with the keys: insight_summary, detailed_explanation, data_summary, actionable_steps, sources.
                The 'sources' field MUST be a list of strings, populated from the AVAILABLE SOURCES list.
                """

            # Step 6: Call LLM
            textual_response = None
            try:
                textual_response = self.llm_client.run_json(system_prompt, user_prompt)
            except Exception as llm_error:
                logger.warning(f"LLM failed: {llm_error}")
                textual_response = None

            # Step 7: Assemble Final Response
            if not textual_response or not isinstance(textual_response, dict):
                # Fallback in case LLM fails
                # --- MODIFICATION: Added 'sources' to the fallback dictionary ---
                textual_response = {
                    "insight_summary": "Data analysis complete.",
                    "detailed_explanation": "The analysis has been performed on the structured data.",
                    "data_summary": [f"Analyzed {analysis_results.get('total_records_analyzed', 0)} structured records."],
                    "actionable_steps": ["Review the generated data table for insights."],
                    "sources": source_names
                }

            textual_response["data_table"] = data_table
            
            # --- REMOVED: No longer needed, LLM or fallback handles this ---
            # textual_response["sources"] = source_names 
            
            # Sanitize lists just in case
            if "data_summary" in textual_response:
                textual_response["data_summary"] = self._sanitize_llm_list_output(textual_response["data_summary"])
            if "actionable_steps" in textual_response:
                textual_response["actionable_steps"] = self._sanitize_llm_list_output(textual_response["actionable_steps"])
            # --- ADDED: Sanitizer for the 'sources' field ---
            if "sources" in textual_response:
                textual_response["sources"] = self._sanitize_llm_list_output(textual_response["sources"])

            return textual_response

        except Exception as e:
            logger.error(f"Failed to generate structured insight: {e}", exc_info=True)
            raise UdayamitraException(f"Failed to generate structured insight: {e}", sys)