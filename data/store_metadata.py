import os
import json
from dotenv import load_dotenv
from Logging.logger import logger
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_astradb import AstraDBVectorStore
from langchain_core.documents import Document

load_dotenv()

# === Config ===
ASTRA_DB_API_ENDPOINT = os.getenv("ASTRA_DB_ENDPOINT")
ASTRA_DB_TOKEN = os.getenv("ASTRA_DB_TOKEN")
COLLECTION_NAME = "Schemes_metadata"
METADATA_DIR = "output"

# === Embeddings ===
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# === Vector Store ===
vectorstore = AstraDBVectorStore(
    embedding=embedding_model,
    collection_name=COLLECTION_NAME,
    api_endpoint=ASTRA_DB_API_ENDPOINT,
    token=ASTRA_DB_TOKEN,
)

# === Helper Functions ===
def load_metadata_json(json_path: str) -> dict:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {json_path}: {e}")
        return {}

def store_metadata_documents(json_folder: str):
    documents = []

    for filename in os.listdir(json_folder):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(json_folder, filename)
        metadata = load_metadata_json(path)
        if not metadata:
            continue

        # Generate unique ID if missing
        if "id" not in metadata:
            metadata["id"] = metadata.get("scheme_name", filename).lower().replace(" ", "_")

        try:
            doc = Document(page_content=json.dumps(metadata), metadata=metadata)
            documents.append(doc)
            logger.info(f"Prepared document from {filename}")
        except Exception as e:
            logger.error(f"Failed to prepare {filename}: {e}")

    if documents:
        try:
            vectorstore.add_documents(documents)
            logger.info(f"Inserted {len(documents)} metadata documents into Astra DB.")
        except Exception as e:
            logger.error(f"Failed to insert documents: {e}")

# === Main ===
if __name__ == "__main__":
    store_metadata_documents(METADATA_DIR)
