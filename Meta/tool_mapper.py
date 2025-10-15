from utility.model import Metadata, ToolRegistryEntry
from utility.register_tools import load_registry_from_file
from Logging.logger import logger
from Exception.exception import UdayamitraException
from typing import Dict
import sys
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class ToolMapper:
    def __init__(self, description_weight: float = 0.7, intent_weight: float = 0.3, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initializes the ToolMapper and precomputes embeddings for all tools.
        """
        try:
            logger.info("Initializing ToolMapper")
            self.tool_registry: Dict[str, ToolRegistryEntry] = load_registry_from_file()
            self.description_weight = description_weight
            self.intent_weight = intent_weight

            # Load the sentence transformer model
            self.model = SentenceTransformer(model_name)

            # Precompute embeddings for tool descriptions and intents
            self.tool_embeddings: Dict[str, Dict[str, np.ndarray]] = {}
            for tool_name, entry in self.tool_registry.items():
                desc_emb = self.model.encode(entry.description, convert_to_numpy=True)
                intent_emb = self.model.encode(" ".join(entry.intents), convert_to_numpy=True)
                self.tool_embeddings[tool_name] = {
                    "description": desc_emb,
                    "intents": intent_emb
                }

        except Exception as e:
            logger.error(f"Failed to initialize ToolMapper: {e}")
            raise UdayamitraException("Failed to initialize ToolMapper", sys)

    def map_tools(self, metadata: Metadata, top_k: int = 1) -> Metadata:
        """
        Maps the metadata to the most relevant tools based on semantic similarity.
        Returns updated metadata with `tools_required` populated.
        """
        try:
            if not metadata.intents and not metadata.query:
                logger.warning("No intents or expanded query found in metadata; skipping tool mapping.")
                return metadata

            # Embed the expanded query
            query_emb = self.model.encode(metadata.query, convert_to_numpy=True)
            # Embed query intents as a single text
            intents_text = " ".join(metadata.intents)
            intents_emb = self.model.encode(intents_text, convert_to_numpy=True)

            tool_scores = {}

            for tool_name, embeddings in self.tool_embeddings.items():
                # Compute cosine similarity
                desc_sim = cosine_similarity(query_emb.reshape(1, -1), embeddings["description"].reshape(1, -1))[0][0]
                intent_sim = cosine_similarity(intents_emb.reshape(1, -1), embeddings["intents"].reshape(1, -1))[0][0]

                # Weighted combination
                score = self.description_weight * desc_sim + self.intent_weight * intent_sim
                tool_scores[tool_name] = score

            # Pick top_k tools
            sorted_tools = sorted(tool_scores.items(), key=lambda x: x[1], reverse=True)
            metadata.tools_required = [tool for tool, _ in sorted_tools[:top_k]]

            logger.info(f"Tools mapped for query '{metadata.query}': {metadata.tools_required}")
            return metadata

        except Exception as e:
            logger.error(f"Error mapping tools with semantic similarity: {e}")
            raise UdayamitraException("Failed to map tools", sys)