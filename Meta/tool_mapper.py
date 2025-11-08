from utility.model import Metadata, ToolRegistryEntry
from utility.register_tools import load_registry_from_file
from Logging.logger import logger
from Exception.exception import UdayamitraException
from typing import Dict
import sys
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from utility.Embedder import HFAPIEmbeddings
import asyncio
import nest_asyncio
nest_asyncio.apply()

class ToolMapper:
    def __init__(self, description_weight: float = 0.7, intent_weight: float = 0.3):
        """
        Initializes the ToolMapper and precomputes embeddings for all tools using HF API.
        """
        try:
            logger.info("Initializing ToolMapper")
            self.tool_registry: Dict[str, ToolRegistryEntry] = load_registry_from_file()
            self.description_weight = description_weight
            self.intent_weight = intent_weight

            # Use HF API embeddings instead of local model
            self.embedding_model = HFAPIEmbeddings()

            # Precompute embeddings for tool descriptions and intents
            self.tool_embeddings: Dict[str, Dict[str, np.ndarray]] = {}
            loop = asyncio.get_event_loop()
            for tool_name, entry in self.tool_registry.items():
                desc_emb, intent_emb = loop.run_until_complete(
                    asyncio.gather(
                        self.embedding_model.embed_documents([entry.description]),
                        self.embedding_model.embed_documents([" ".join(entry.intents)])
                    )
                )
                self.tool_embeddings[tool_name] = {
                    "description": np.array(desc_emb[0]),
                    "intents": np.array(intent_emb[0])
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

            # Embed query and intents using HF API (synchronously via async wrapper)
            loop = asyncio.get_event_loop()
            query_emb, intents_emb = loop.run_until_complete(
                asyncio.gather(
                    self.embedding_model.embed_documents([metadata.query]),
                    self.embedding_model.embed_documents([" ".join(metadata.intents)])
                )
            )
            query_emb = np.array(query_emb[0])
            intents_emb = np.array(intents_emb[0])

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