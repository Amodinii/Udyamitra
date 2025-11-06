import httpx
import os
import asyncio

EMBEDDING_API_URL = os.getenv(
    "EMBEDDING_API_URL",
    "https://adityapeopleplus-embedding-generator.hf.space/embed"
)

async def get_embedding(text: str):
    """Send text to the HF Space embedding API and return the vector."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(EMBEDDING_API_URL, json={"text": text})
        resp.raise_for_status()
        return resp.json()["embedding"]


class HFAPIEmbeddings:
    """Wrapper for Hugging Face API to mimic LangChain embeddings interface."""

    async def embed_documents(self, texts):
        embeddings = []
        for text in texts:
            vec = await get_embedding(text)
            embeddings.append(vec)
        return embeddings

    def embed_documents_sync(self, texts):
        """Synchronous wrapper for scripts that are not async."""
        return asyncio.run(self.embed_documents(texts))