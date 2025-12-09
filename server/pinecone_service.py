"""
Pinecone service for vector database operations.
Handles storing and querying document embeddings.
"""

from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Optional
import logging
import uuid

logger = logging.getLogger(__name__)

class PineconeService:
    """Service for managing vector storage in Pinecone."""

    def __init__(self, api_key: str, index_name: str, dimension: int = 1536, cloud: str = "aws", region: str = "us-east-1"):
        """
        Initialize the Pinecone service.

        Args:
            api_key: Pinecone API key
            index_name: Name of the Pinecone index
            dimension: Dimension of the embeddings (default: 1536 for text-embedding-3-small)
            cloud: Cloud provider (default: aws)
            region: Cloud region (default: us-east-1)
        """
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.dimension = dimension
        self.cloud = cloud
        self.region = region
        self.index = None

    async def initialize_index(self):
        """
        Initialize or connect to Pinecone index.
        Creates the index if it doesn't exist.
        """
        try:
            # Check if index exists
            existing_indexes = [index.name for index in self.pc.list_indexes()]

            if self.index_name not in existing_indexes:
                logger.info(f"Creating new Pinecone index: {self.index_name}")

                # Create new index
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud=self.cloud,
                        region=self.region
                    )
                )

                logger.info(f"Index {self.index_name} created successfully")
            else:
                logger.info(f"Connecting to existing index: {self.index_name}")

            # Connect to index
            self.index = self.pc.Index(self.index_name)

        except Exception as e:
            logger.error(f"Failed to initialize Pinecone index: {str(e)}")
            raise Exception(f"Pinecone initialization failed: {str(e)}")

    async def upsert_chunks(self, chunks: List[Dict], file_name: str) -> Dict:
        """
        Upload chunks with embeddings to Pinecone.

        Args:
            chunks: List of chunks with embeddings and metadata
            file_name: Name of the source file

        Returns:
            Dictionary with upload statistics
        """
        try:
            if not self.index:
                await self.initialize_index()

            vectors = []

            for chunk in chunks:
                # Generate unique ID for each chunk
                chunk_id = f"{file_name}_{chunk['chunk_id']}_{uuid.uuid4().hex[:8]}"

                # Prepare metadata (exclude embedding from metadata)
                metadata = {
                    "file_name": file_name,
                    "chunk_id": chunk["chunk_id"],
                    "chunk_text": chunk["chunk_text"],
                    "token_count": chunk["token_count"]
                }

                if "page_number" in chunk:
                    metadata["page_number"] = chunk["page_number"]

                # Prepare vector tuple (id, embedding, metadata)
                vectors.append({
                    "id": chunk_id,
                    "values": chunk["embedding"],
                    "metadata": metadata
                })

            # Upsert vectors to Pinecone in batches
            batch_size = 100
            total_upserted = 0

            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
                total_upserted += len(batch)

            logger.info(f"Upserted {total_upserted} vectors to Pinecone for file: {file_name}")

            return {
                "total_chunks": len(chunks),
                "upserted_count": total_upserted,
                "index_name": self.index_name
            }

        except Exception as e:
            logger.error(f"Failed to upsert chunks to Pinecone: {str(e)}")
            raise Exception(f"Pinecone upsert failed: {str(e)}")

    async def query(self, query_embedding: List[float], top_k: int = 5, filter: Optional[Dict] = None) -> List[Dict]:
        """
        Query Pinecone index for similar vectors.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of matching results with metadata
        """
        try:
            if not self.index:
                await self.initialize_index()

            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter
            )

            matches = []
            for match in results.matches:
                matches.append({
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata
                })

            logger.info(f"Query returned {len(matches)} results")

            return matches

        except Exception as e:
            logger.error(f"Failed to query Pinecone: {str(e)}")
            raise Exception(f"Pinecone query failed: {str(e)}")

    async def delete_by_file(self, file_name: str) -> Dict:
        """
        Delete all vectors associated with a specific file.

        Args:
            file_name: Name of the file to delete vectors for

        Returns:
            Dictionary with deletion confirmation
        """
        try:
            if not self.index:
                await self.initialize_index()

            # First, query to get all vector IDs for this file
            # We need to fetch ALL vectors for this file, not just top matches
            # Use a dummy query vector and filter by file_name
            dummy_vector = [0.0] * self.dimension

            # Query with high top_k to get all vectors for this file
            # Pinecone serverless has a max of 10,000 results per query
            results = self.index.query(
                vector=dummy_vector,
                top_k=10000,
                include_metadata=True,
                filter={"file_name": file_name}
            )

            # Extract vector IDs
            vector_ids = [match.id for match in results.matches]

            if not vector_ids:
                logger.warning(f"No vectors found for file: {file_name}")
                return {
                    "message": f"No vectors found for {file_name}",
                    "file_name": file_name,
                    "deleted_count": 0
                }

            # Delete by IDs in batches (Pinecone recommends batches of 1000)
            batch_size = 1000
            total_deleted = 0

            for i in range(0, len(vector_ids), batch_size):
                batch = vector_ids[i:i + batch_size]
                self.index.delete(ids=batch)
                total_deleted += len(batch)

            logger.info(f"Deleted {total_deleted} vectors for file: {file_name}")

            return {
                "message": f"Deleted {total_deleted} vectors for {file_name}",
                "file_name": file_name,
                "deleted_count": total_deleted
            }

        except Exception as e:
            logger.error(f"Failed to delete vectors from Pinecone: {str(e)}")
            raise Exception(f"Pinecone deletion failed: {str(e)}")
