import os
import json
import fitz 
import sys 
from dotenv import load_dotenv
from Logging.logger import logger
from sentence_transformers import SentenceTransformer 
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_astradb import AstraDBVectorStore
from langchain_core.documents import Document

load_dotenv()

PDF_DIR = "data/raw/pdfs/new" 
#TXT_DIR = "data/raw/webpages" 
COLLECTION_NAME = "Export_Chunks" 

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore = AstraDBVectorStore(
    embedding=embedding_model,
    collection_name=COLLECTION_NAME,
    api_endpoint=os.getenv("ASTRA_DB_ENDPOINT"),
    token=os.getenv("ASTRA_DB_TOKEN"),
)

def extract_text_from_pdf(filepath):
    """Extracts text from a PDF file using fitz (PyMuPDF)."""
    try:
        if not hasattr(fitz, 'open'):
             logger.error("fitz module does not have 'open' attribute. Is PyMuPDF installed correctly?")
             raise ImportError("fitz.open not found. Check PyMuPDF installation.")

        logger.debug(f"Loading PDF with fitz: {filepath}")
        doc = fitz.open(filepath) 
        full_text = "\n".join(page.get_text() for page in doc)
        doc.close() 
        logger.debug(f"Extracted {len(full_text)} characters from {filepath}")
        return full_text
    except ImportError as ie: 
         logger.error(f"ImportError reading {filepath}: {ie}")
         return "" 
    except Exception as e:
        logger.error(f"Error reading {filepath} with fitz: {e}", exc_info=True)
        return ""

def extract_text_from_txt(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return ""

def chunk_text(text, metadata):
    """Chunks text and returns LangChain Document objects with metadata."""
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
    """Finds PDFs in PDF_DIR, chunks them, and adds them to the vector store."""
    groups = {}
    all_pdf_paths = []

    if not os.path.isdir(PDF_DIR):
        logger.error(f"PDF directory not found: {os.path.abspath(PDF_DIR)}")
        return

    for fname in os.listdir(PDF_DIR):
        if fname.lower().endswith(".pdf"):
            pdf_path = os.path.join(PDF_DIR, fname)
            all_pdf_paths.append(pdf_path)
            key = os.path.splitext(fname)[0]
            groups[key] = {"pdfs": [pdf_path]}

    logger.info(f"Found {len(all_pdf_paths)} PDF files to process in '{PDF_DIR}': {all_pdf_paths}")

    if not groups:
        logger.warning(f"No PDF files found in '{PDF_DIR}'. Ingestion will not proceed.")
        return

    processed_chunks_count = 0
    for doc_id, files in groups.items():
        logger.info(f"\nProcessing document: {doc_id}")
        text = ""

        pdf_path = files["pdfs"][0] 
        pdf_content = extract_text_from_pdf(pdf_path)
        if pdf_content:
            text += pdf_content 
            logger.info(f"  - Extracted text from PDF: {pdf_path}")
        else:
            logger.warning(f"  - Failed to extract text from PDF: {pdf_path}. Skipping.")
            continue 
        if not text.strip():
            logger.warning(f"No text extracted for document '{doc_id}', skipping.")
            continue

        metadata = {
            "id": doc_id,
            "source_file": os.path.abspath(pdf_path), 
            "original_filename": os.path.basename(pdf_path) 
        }

        documents = chunk_text(text, metadata)
        logger.info(f"  - Split text into {len(documents)} chunks.")

        if documents:
            try:
                # Add documents TO THE EXISTING COLLECTION
                vectorstore.add_documents(documents)
                logger.info(f"  - Successfully embedded and ADDED {len(documents)} chunks for '{doc_id}' to '{COLLECTION_NAME}'.")
                processed_chunks_count += len(documents)
            except Exception as e:
                logger.error(f"  - Failed to insert chunks for '{doc_id}': {e}", exc_info=True)
        else:
            logger.warning(f"  - No chunks generated for '{doc_id}', nothing to insert.")

    logger.info(f"\nIngestion finished. Total new chunks added: {processed_chunks_count}")


if __name__ == "__main__":
    logger.info(f"Starting ingestion process to ADD documents to collection '{COLLECTION_NAME}'...")
    logger.info(f"Proceeding with ingestion into existing collection '{COLLECTION_NAME}'...")
    ingest_all() 
    logger.info("Ingestion process complete.")