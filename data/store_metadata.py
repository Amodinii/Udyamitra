import os
import json
from astrapy import DataAPIClient
from Logging.logger import logger
from dotenv import load_dotenv

load_dotenv()

client = DataAPIClient()
db = client.get_database(
    os.getenv("ASTRA_DB_ENDPOINT"),
    token=os.getenv("ASTRA_DB_TOKEN")
)

collection_name = "Schemes_metadata"
if collection_name not in db.list_collections():
    db.create_collection(collection_name)
    logger.info(f"Created collection: {collection_name}")
else:
    logger.info(f"Using existing collection: {collection_name}")

collection = db.get_collection(collection_name)


def load_metadata_json(json_path: str) -> dict:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {json_path}: {e}")
        return {}

def store_metadata_documents(json_folder: str):
    for filename in os.listdir(json_folder):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(json_folder, filename)
        metadata = load_metadata_json(path)
        if not metadata:
            continue

        if "id" not in metadata:
            metadata["id"] = metadata.get("scheme_name", filename).lower().replace(" ", "_")

        try:
            collection.insert_one(metadata)
            logger.info(f"Inserted metadata from {filename}")
        except Exception as e:
            logger.error(f"Failed to insert {filename}: {e}")

if __name__ == "__main__":
    metadata_dir = "output"
    store_metadata_documents(metadata_dir)
