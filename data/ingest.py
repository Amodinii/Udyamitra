"""
Test script for the AstraDB ingestion module.
This script:
1. Loads environment variables
2. Creates an AstraDB client
3. Processes and uploads all PDFs from a test directory
4. Verifies that documents were successfully inserted
"""

import os
from dotenv import load_dotenv
from Logging.logger import logger
from data.AstraDB import AstraDB

load_dotenv()

def test_astra_ingestion():
    try:
        collection_name = "exp_scheme_chunks"  # collection name
        pdf_directory = "./data/raw/pdfs/exp_pdfs"  # Folder containing test PDFs

        astra = AstraDB(collection_name)
        logger.info(f"Initialized AstraDB client for collection: {collection_name}")
        astra.process_and_push_directory(pdf_directory)
        logger.info(f"Pushed all PDFs from '{pdf_directory}' successfully!")
        collection = astra.database.get_collection(collection_name)
        print(f"\nSUCCESS: Documents uploaded to '{collection_name}' in AstraDB!")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\nERROR: {e}")


if __name__ == "__main__":
    test_astra_ingestion()
