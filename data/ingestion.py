import os
<<<<<<< HEAD
import json
import fitz
from dotenv import load_dotenv
from Logging.logger import logger
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_astradb import AstraDBVectorStore
from langchain_core.documents import Document

load_dotenv()

PDF_DIR = "data/Policy/New"
#TXT_DIR = "data/raw/webpages"
COLLECTION_NAME = "Investor_policies"

# Embedding model (LangChain wrapper)
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Vector Store setup
vectorstore = AstraDBVectorStore(
    embedding=embedding_model,
    collection_name=COLLECTION_NAME,
    api_endpoint=os.getenv("ASTRA_DB_ENDPOINT"),
    token=os.getenv("ASTRA_DB_TOKEN"),
)

def extract_text_from_pdf(filepath):
    try:
        doc = fitz.open(filepath)
        return "\n".join(page.get_text() for page in doc)
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return ""

def extract_text_from_txt(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return ""

def chunk_text(text, metadata):
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    chunks = splitter.split_text(text)

    documents = []
    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk,
            metadata={
                **metadata,
                "chunk_index": i
            }
        )
        documents.append(doc)
    return documents

def ingest_all():
    groups = {}

    for root, _, files in os.walk(PDF_DIR):
        for fname in files:
            if fname.endswith(".pdf"):
                key = os.path.splitext(fname)[0]
                pdf_path = os.path.join(root, fname)
                groups.setdefault(key, {}).setdefault("pdfs", []).append(pdf_path)

    #for fname in os.listdir(TXT_DIR):
        #if fname.endswith(".txt"):
            #key = os.path.splitext(fname)[0]
            #groups.setdefault(key, {})["txt"] = os.path.join(TXT_DIR, fname)

    for doc_id, files in groups.items():
        logger.info(f"\nProcessing document group: {doc_id}")
        text = ""

        if "txt" in files:
            text += extract_text_from_txt(files["txt"])

        for pdf_path in files.get("pdfs", []):
            text += "\n" + extract_text_from_pdf(pdf_path)

        if not text.strip():
            logger.warning(f"No text found for group {doc_id}, skipping.")
            continue

        metadata = {
            "id": doc_id,
            "source_files": list(files.values()),
            "scheme_name": doc_id.replace("_", " ").title()
        }

        documents = chunk_text(text, metadata)
        try:
            vectorstore.add_documents(documents)
            logger.info(f"Inserted {len(documents)} chunks for {doc_id}")
        except Exception as e:
            logger.error(f"Failed to insert chunks for {doc_id}: {e}")

if __name__ == "__main__":
    ingest_all()
=======
import uuid
import asyncio
import uuid
import asyncio
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from logging import getLogger, INFO, StreamHandler, Formatter
from datetime import datetime
from astrapy import DataAPIClient

# --- 1. Basic Logging Setup ---
logger = getLogger(__name__)
logger.setLevel(INFO)
handler = StreamHandler()
formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

# --- 2. Load Environment Variables ---
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from logging import getLogger, INFO, StreamHandler, Formatter
from datetime import datetime
from astrapy import DataAPIClient

# --- 1. Basic Logging Setup ---
logger = getLogger(__name__)
logger.setLevel(INFO)
handler = StreamHandler()
formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

# --- 2. Load Environment Variables ---
load_dotenv()

ASTRA_DB_ENDPOINT = os.getenv("ASTRA_DB_ENDPOINT") 
ASTRA_DB_TOKEN = os.getenv("ASTRA_DB_TOKEN")
COLLECTION_NAME = "export_import_data"
TARGET_URL = "https://www.exportimportdata.in/export-8532-hs-code"
ASTRA_DB_ENDPOINT = os.getenv("ASTRA_DB_ENDPOINT") 
ASTRA_DB_TOKEN = os.getenv("ASTRA_DB_TOKEN")
COLLECTION_NAME = "export_import_data"
TARGET_URL = "https://www.exportimportdata.in/export-8532-hs-code"

# --- 3. Async Scraping and Parsing Functions ---

def parse_table_data(html_content):
    """Parses the HTML of the table body and extracts structured row data."""
    soup = BeautifulSoup(html_content, 'html.parser')
    rows = soup.find_all('tr')
    scraped_data = []
    for row in rows:
        cols = [ele.text.strip() for ele in row.find_all('td')]
        if len(cols) == 9:
            try:
                scraped_data.append({
                    "_id": str(uuid.uuid4()),
                    "trade_date": cols[0],
                    "indian_port": cols[1],
                    "cth": int(cols[2]),
                    "item_description": cols[3],
                    "quantity": int(cols[4].replace(',', '')),
                    "uqc": cols[5],
                    "unit_price_usd": float(cols[6].replace(',', '')),
                    "fob_usd": float(cols[7].replace(',', '')),
                    "destination_port": cols[8]
                })
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse row: {cols}. Error: {e}")
    return scraped_data

async def scrape_all_pages(url, max_pages=100):
    """Uses Playwright's async API to navigate and scrape pages up to a limit."""
    all_records = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        logger.info(f"Navigating to {url}")
        await page.goto(url, wait_until="networkidle", timeout=60000)

        page_num = 1
        while True:
            if page_num > max_pages:
                logger.info(f"Reached the maximum page limit of {max_pages}. Stopping scrape.")
                break
            
            logger.info(f"Scraping page {page_num}...")
            table_body_html = await page.inner_html('div#datamodule tbody')
            records_on_page = parse_table_data(table_body_html)
            all_records.extend(records_on_page)
            logger.info(f"Found {len(records_on_page)} records. Total: {len(all_records)}")
            
            next_button = page.locator("a#nextpage")
            style = await next_button.get_attribute("style")
            if style and "display: none" in style:
                logger.info("Reached the end of the data.")
                break
                
            try:
                await next_button.click()
                await page.wait_for_load_state("networkidle", timeout=30000)
                await asyncio.sleep(2)
                page_num += 1
            except Exception as e:
                logger.error(f"Could not click next button. Assuming end of data. Error: {e}")
                break

        await browser.close()
    return all_records

# --- 4. Main Async Function ---

async def main():
    """Main function to orchestrate the scraping and ingestion process."""
    if not all([ASTRA_DB_ENDPOINT, ASTRA_DB_TOKEN]):
        logger.error("Missing environment variables. Check your .env file.")
        return

    try:
        # --- Connect to Astra DB using DataAPIClient ---
        client = DataAPIClient(ASTRA_DB_TOKEN)
        db = client.get_database(ASTRA_DB_ENDPOINT)

        # --- Ensure collection exists ---
        existing_collections = [c.name for c in db.list_collections()]
        if COLLECTION_NAME not in existing_collections:
            collection = db.create_collection(COLLECTION_NAME)
            logger.info(f"Created collection '{COLLECTION_NAME}'")
        else:
            collection = db.get_collection(COLLECTION_NAME)
            logger.info(f"Using existing collection '{COLLECTION_NAME}'")

        # --- Scrape the data ---
        scraped_records = await scrape_all_pages(TARGET_URL, max_pages=100)
        
        if not scraped_records:
            logger.warning("No records were scraped.")
            return

        # --- Normalize and Insert Data in Batches ---
        docs_to_insert = []
        for record in scraped_records:
            try:
                trade_date_obj = datetime.strptime(record['trade_date'], '%d-%b-%Y')
                record['trade_date'] = trade_date_obj.isoformat()
                docs_to_insert.append(record)
            except ValueError:
                logger.warning(f"Invalid date format for {record['trade_date']}. Skipping record.")

        logger.info(f"Ingesting {len(docs_to_insert)} records in batches...")
        if docs_to_insert:
            batch_size = 500
            for i in range(0, len(docs_to_insert), batch_size):
                batch = docs_to_insert[i:i + batch_size]
                # --- FIXED: Removed 'await' from the next line ---
                collection.insert_many(batch)
                logger.info(f"  ... inserted batch {i//batch_size + 1}")
        logger.info("Ingestion complete.")

# --- 3. Async Scraping and Parsing Functions ---

def parse_table_data(html_content):
    """Parses the HTML of the table body and extracts structured row data."""
    soup = BeautifulSoup(html_content, 'html.parser')
    rows = soup.find_all('tr')
    scraped_data = []
    for row in rows:
        cols = [ele.text.strip() for ele in row.find_all('td')]
        if len(cols) == 9:
            try:
                scraped_data.append({
                    "_id": str(uuid.uuid4()),
                    "trade_date": cols[0],
                    "indian_port": cols[1],
                    "cth": int(cols[2]),
                    "item_description": cols[3],
                    "quantity": int(cols[4].replace(',', '')),
                    "uqc": cols[5],
                    "unit_price_usd": float(cols[6].replace(',', '')),
                    "fob_usd": float(cols[7].replace(',', '')),
                    "destination_port": cols[8]
                })
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse row: {cols}. Error: {e}")
    return scraped_data

async def scrape_all_pages(url, max_pages=100):
    """Uses Playwright's async API to navigate and scrape pages up to a limit."""
    all_records = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        logger.info(f"Navigating to {url}")
        await page.goto(url, wait_until="networkidle", timeout=60000)

        page_num = 1
        while True:
            if page_num > max_pages:
                logger.info(f"Reached the maximum page limit of {max_pages}. Stopping scrape.")
                break
            
            logger.info(f"Scraping page {page_num}...")
            table_body_html = await page.inner_html('div#datamodule tbody')
            records_on_page = parse_table_data(table_body_html)
            all_records.extend(records_on_page)
            logger.info(f"Found {len(records_on_page)} records. Total: {len(all_records)}")
            
            next_button = page.locator("a#nextpage")
            style = await next_button.get_attribute("style")
            if style and "display: none" in style:
                logger.info("Reached the end of the data.")
                break
                
            try:
                await next_button.click()
                await page.wait_for_load_state("networkidle", timeout=30000)
                await asyncio.sleep(2)
                page_num += 1
            except Exception as e:
                logger.error(f"Could not click next button. Assuming end of data. Error: {e}")
                break

        await browser.close()
    return all_records

# --- 4. Main Async Function ---

async def main():
    """Main function to orchestrate the scraping and ingestion process."""
    if not all([ASTRA_DB_ENDPOINT, ASTRA_DB_TOKEN]):
        logger.error("Missing environment variables. Check your .env file.")
        return

    try:
        # --- Connect to Astra DB using DataAPIClient ---
        client = DataAPIClient(ASTRA_DB_TOKEN)
        db = client.get_database(ASTRA_DB_ENDPOINT)

        # --- Ensure collection exists ---
        existing_collections = [c.name for c in db.list_collections()]
        if COLLECTION_NAME not in existing_collections:
            collection = db.create_collection(COLLECTION_NAME)
            logger.info(f"Created collection '{COLLECTION_NAME}'")
        else:
            collection = db.get_collection(COLLECTION_NAME)
            logger.info(f"Using existing collection '{COLLECTION_NAME}'")

        # --- Scrape the data ---
        scraped_records = await scrape_all_pages(TARGET_URL, max_pages=100)
        
        if not scraped_records:
            logger.warning("No records were scraped.")
            return

        # --- Normalize and Insert Data in Batches ---
        docs_to_insert = []
        for record in scraped_records:
            try:
                trade_date_obj = datetime.strptime(record['trade_date'], '%d-%b-%Y')
                record['trade_date'] = trade_date_obj.isoformat()
                docs_to_insert.append(record)
            except ValueError:
                logger.warning(f"Invalid date format for {record['trade_date']}. Skipping record.")

        logger.info(f"Ingesting {len(docs_to_insert)} records in batches...")
        if docs_to_insert:
            batch_size = 500
            for i in range(0, len(docs_to_insert), batch_size):
                batch = docs_to_insert[i:i + batch_size]
                # --- FIXED: Removed 'await' from the next line ---
                collection.insert_many(batch)
                logger.info(f"  ... inserted batch {i//batch_size + 1}")
        logger.info("Ingestion complete.")

    except Exception as e:
        logger.error(f"The process failed: {e}", exc_info=True)

# --- 5. Run the main async function ---
        logger.error(f"The process failed: {e}", exc_info=True)

# --- 5. Run the main async function ---
if __name__ == "__main__":
    asyncio.run(main())
>>>>>>> Amodini
