"""
RAG (Retrieval-Augmented Generation) service.
Orchestrates the complete RAG pipeline: PDF parsing, chunking, embedding, and storage.
"""

from typing import Dict
import logging

from pdf_parser import pdf_parser
from chunking_service import chunking_service
from embedding_service import EmbeddingService
from pinecone_service import PineconeService

logger = logging.getLogger(__name__)


class RAGService:
    """Service for orchestrating the complete RAG pipeline."""

    def __init__(self, embedding_service: EmbeddingService, pinecone_service: PineconeService):
        """
        Initialize the RAG service.

        Args:
            embedding_service: Service for generating embeddings
            pinecone_service: Service for vector storage
        """
        self.embedding_service = embedding_service
        self.pinecone_service = pinecone_service

    async def process_pdf(self, file_content: bytes, file_name: str) -> Dict:
        """
        Process a PDF through the complete RAG pipeline.

        Pipeline steps:
        1. Parse PDF and extract text using pdfplumber
        2. Chunk text using RecursiveCharacterTextSplitter
        3. Ensure chunks are below 400 token limit
        4. Generate embeddings for each chunk
        5. Store chunks and embeddings in Pinecone

        Args:
            file_content: Raw PDF file bytes
            file_name: Name of the PDF file

        Returns:
            Dictionary with processing statistics
        """
        try:
            logger.info(f"Starting RAG pipeline for {file_name}")

            # Step 1: Parse PDF
            logger.info("Step 1: Parsing PDF")
            parsed_data = await pdf_parser.parse_pdf(file_content, file_name)

            # Step 2 & 3: Chunk text with token limits
            logger.info("Step 2-3: Chunking text with token limits")
            chunks = chunking_service.chunk_with_metadata(
                text=parsed_data["full_text"],
                file_name=file_name
            )

            # Validate token counts
            max_tokens = max([chunk["token_count"] for chunk in chunks])
            logger.info(f"Created {len(chunks)} chunks, max tokens per chunk: {max_tokens}")

            # Step 4: Generate embeddings
            logger.info("Step 4: Generating embeddings")
            chunks_with_embeddings = await self.embedding_service.embed_chunks(chunks)

            # Step 5: Store in Pinecone
            logger.info("Step 5: Storing in Pinecone")
            pinecone_result = await self.pinecone_service.upsert_chunks(
                chunks=chunks_with_embeddings,
                file_name=file_name
            )

            logger.info(f"RAG pipeline completed for {file_name}")

            return {
                "file_name": file_name,
                "total_pages": parsed_data["total_pages"],
                "character_count": parsed_data["character_count"],
                "total_chunks": len(chunks),
                "max_tokens_per_chunk": max_tokens,
                "pinecone_index": pinecone_result["index_name"],
                "upserted_count": pinecone_result["upserted_count"]
            }

        except Exception as e:
            logger.error(f"RAG pipeline failed for {file_name}: {str(e)}")
            raise Exception(f"RAG processing failed: {str(e)}")

    async def query_documents(self, query_text: str, top_k: int = 5, file_filter: str = None) -> Dict:
        """
        Query the RAG system with a text question.

        Args:
            query_text: Question or query text
            top_k: Number of results to return
            file_filter: Optional file name to filter results

        Returns:
            Dictionary with query results
        """
        try:
            # Generate embedding for query
            query_embedding = await self.embedding_service.generate_embedding(query_text)

            # Prepare filter if file_filter is provided
            metadata_filter = {"file_name": file_filter} if file_filter else None

            # Query Pinecone
            results = await self.pinecone_service.query(
                query_embedding=query_embedding,
                top_k=top_k,
                filter=metadata_filter
            )

            return {
                "query": query_text,
                "results_count": len(results),
                "results": results
            }

        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            raise Exception(f"Query processing failed: {str(e)}")
