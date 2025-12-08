"""
Embedding service for generating vector embeddings from text.
Uses OpenAI's embedding model for high-quality embeddings.
"""

from openai import OpenAI
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings from text chunks."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        """
        Initialize the embedding service.

        Args:
            api_key: OpenAI API key
            model: Embedding model to use (default: text-embedding-3-small)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text string.

        Args:
            text: Text to generate embedding for

        Returns:
            Embedding vector as list of floats
        """
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )

            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding of dimension {len(embedding)}")

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise Exception(f"Embedding generation failed: {str(e)}")

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple text strings in a batch.

        Args:
            texts: List of texts to generate embeddings for

        Returns:
            List of embedding vectors
        """
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=self.model
            )

            embeddings = [data.embedding for data in response.data]
            logger.info(f"Generated {len(embeddings)} embeddings")

            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {str(e)}")
            raise Exception(f"Batch embedding generation failed: {str(e)}")

    async def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Generate embeddings for chunks and attach them to chunk metadata.

        Args:
            chunks: List of chunk dictionaries with metadata

        Returns:
            List of chunks with embeddings attached
        """
        texts = [chunk["chunk_text"] for chunk in chunks]
        embeddings = await self.generate_embeddings_batch(texts)

        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding

        return chunks
