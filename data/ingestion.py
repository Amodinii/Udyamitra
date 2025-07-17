import os
import json
import fitz
from astrapy.db import AstraDB
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from Logging.logger import logger

PDF_DIR = "data/raw/pdfs"
TXT_DIR = "data/raw/webpages"
COLLECTION_NAME = "scheme_chunks"

embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

astra_db = AstraDB(
    api_endpoint=os.getenv("ASTRA_DB_API_ENDPOINT"),
    token=os.getenv("ASTRA_DB_APPLICATION_TOKEN")
)
collection = astra_db.collection(COLLECTION_NAME)

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

def chunk_and_embed(text, metadata):
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    chunks = splitter.split_text(text)

    return [{
        "id": f"{metadata['id']}_chunk_{i}",
        "chunk": chunk,
        "embedding": embedding_model.encode(chunk).tolist(),
        "metadata": metadata
    } for i, chunk in enumerate(chunks)]

def ingest_all():
    groups = {}

    for fname in os.listdir(PDF_DIR):
        if fname.endswith(".pdf"):
            key = os.path.splitext(fname)[0]
            groups.setdefault(key, {}).setdefault("pdfs", []).append(os.path.join(PDF_DIR, fname))

    for fname in os.listdir(TXT_DIR):
        if fname.endswith(".txt"):
            key = os.path.splitext(fname)[0]
            groups.setdefault(key, {})["txt"] = os.path.join(TXT_DIR, fname)

    for doc_id, files in groups.items():
        logger.info(f"\nProcessing document group: {doc_id}")
        text = ""

        if "txt" in files:
            text += extract_text_from_txt(files["txt"])

        for pdf_path in files.get("pdfs", []):
            text += "\n" + extract_text_from_pdf(pdf_path)

        if not text.strip():
            logger.warning("No text found for group, skipping.")
            continue

        metadata = {
            "id": doc_id,
            "source_files": list(files.values()),
            "scheme_name": doc_id.replace("_", " ").title()
        }

        chunks = chunk_and_embed(text, metadata)
        collection.insert_many(chunks)
        logger.info(f"Inserted {len(chunks)} chunks for {doc_id}")

if __name__ == "__main__":
    ingest_all()
