import sys
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

from Logging.logger import logger
from Exception.exception import UdayamitraException

from astrapy import DataAPIClient
from astrapy.constants import VectorMetric
from astrapy.info import CollectionDefinition, CollectionVectorOptions

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

load_dotenv()


class AstraDB:
    DEFAULT_DIMENSION = 384
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, collection_name: str, dimension: int = DEFAULT_DIMENSION):
        try:
            logger.info("Initializing AstraDB client and embedding model...")
            self.client = DataAPIClient()
            self.database = self.client.get_database(
                api_endpoint=os.getenv("ASTRA_DB_ENDPOINT"),
                token=os.getenv("ASTRA_DB_TOKEN"),
            )
            self.collection_name = collection_name
            self.dimension = dimension
            self.model = SentenceTransformer(self.EMBEDDING_MODEL)
            logger.info(f"Using local embedding model: {self.EMBEDDING_MODEL} ({self.dimension}D)")
        except Exception as e:
            logger.error(f"Failed to initialize AstraDB client or model: {e}")
            raise UdayamitraException("Failed to initialize AstraDB", sys)

    def create_collection(self):
        try:
            if self.collection_name in self.database.list_collection_names():
                logger.info(f"Collection '{self.collection_name}' already exists. Skipping creation.")
                return
            definition = CollectionDefinition(
                vector=CollectionVectorOptions(
                    dimension=self.dimension,
                    metric=VectorMetric.COSINE,
                ),
            )
            self.database.create_collection(self.collection_name, definition=definition)
            logger.info(f"Collection '{self.collection_name}' created successfully ({self.dimension}D).")
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise UdayamitraException("Failed to create collection", sys)

    def load_and_chunk_pdf(self, file_path: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[Dict[str, Any]]:
        try:
            logger.info(f"Loading and splitting PDF: {file_path}")
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", ".", "!", "?"]
            )
            split_docs = splitter.split_documents(documents)
            chunks = []
            for doc in split_docs:
                chunks.append({
                    "file_name": os.path.basename(file_path),
                    "text": doc.page_content.strip(),
                    "metadata": doc.metadata,
                })
            logger.info(f"Split {os.path.basename(file_path)} into {len(chunks)} chunks.")
            return chunks
        except Exception as e:
            logger.error(f"Failed to load or split PDF '{file_path}': {e}")
            raise UdayamitraException("Failed to load or split PDF", sys)

    def vectorize_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            logger.info(f"Vectorizing {len(chunks)} text chunks...")
            texts = [chunk["text"] for chunk in chunks]
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            vectorized_docs = []
            for i, chunk in enumerate(chunks):
                doc = {
                    "file_name": chunk["file_name"],
                    "metadata": chunk.get("metadata", {}),
                    "text": chunk["text"],
                    "$vector": embeddings[i].tolist()
                }
                vectorized_docs.append(doc)
            logger.info(f"Generated {len(vectorized_docs)} embeddings ({self.dimension}D each).")
            return vectorized_docs
        except Exception as e:
            logger.error(f"Failed to vectorize chunks: {e}")
            raise UdayamitraException("Failed to vectorize chunks", sys)

    def push_to_collection(self, data: List[Dict[str, Any]]):
        try:
            self.create_collection()
            collection = self.database.get_collection(self.collection_name)
            if not data:
                logger.warning("No data to insert. Skipping push.")
                return
            result = collection.insert_many(data, ordered=False)
            logger.info(f"Inserted documents into '{self.collection_name}'.")
        except Exception as e:
            logger.error(f"Failed to push data to AstraDB: {e}")
            raise UdayamitraException("Failed to push data to AstraDB", sys)

    def process_and_push_directory(self, directory_path: str):
        try:
            pdf_files = [
                os.path.join(directory_path, f)
                for f in os.listdir(directory_path)
                if f.lower().endswith(".pdf")
            ]
            logger.info(f"Found {len(pdf_files)} PDFs in {directory_path}.")
            all_docs = []
            for file in pdf_files:
                chunks = self.load_and_chunk_pdf(file)
                vectorized = self.vectorize_chunks(chunks)
                all_docs.extend(vectorized)
            self.push_to_collection(all_docs)
            logger.info(f"Successfully ingested {len(all_docs)} chunks from {len(pdf_files)} PDFs into AstraDB.")
        except Exception as e:
            logger.error(f"Failed to process directory '{directory_path}': {e}")
            raise UdayamitraException("Failed to process directory", sys)