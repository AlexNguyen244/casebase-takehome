"""
Chunking service using LangChain's RecursiveCharacterTextSplitter.
Implements semantic, structure-aware chunking with token limit enforcement.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import GPT2TokenizerFast
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service for chunking text into semantically meaningful segments with token limits."""

    def __init__(self, target_tokens: int = 400, overlap_tokens: int = 50):
        """
        Initialize the chunking service.

        Args:
            target_tokens: Maximum number of tokens per chunk (default: 400)
            overlap_tokens: Number of overlapping tokens between chunks (default: 50)
        """
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        self.tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")

        # Phase 1: LangChain semantic-aware splitting
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,  # Large initial size, will trim by tokens later
            chunk_overlap=200,
            separators=[
                "\n\n",  # Paragraph breaks
                "\n",    # Line breaks
                ". ",    # Sentences
                " ",     # Words
                ""       # Characters
            ]
        )

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.tokenizer.encode(text))

    def hybrid_chunk(self, text: str) -> List[str]:
        """
        Perform hybrid chunking: semantic splitting followed by token-based trimming.

        Step 1: Use LangChain's RecursiveCharacterTextSplitter for semantic chunking
        Step 2: Ensure each chunk is below token limit (400 tokens)
        Step 3: If chunk is too long, split it again by tokens

        Args:
            text: Full text to chunk

        Returns:
            List of text chunks, each under the token limit
        """
        # Phase 1: Initial semantic-aware splitting
        initial_chunks = self.text_splitter.split_text(text)
        final_chunks = []

        # Phase 2: Token-based trimming
        for chunk in initial_chunks:
            tokens = self.tokenizer.encode(chunk)

            # If chunk is within token limit, keep it
            if len(tokens) <= self.target_tokens:
                final_chunks.append(chunk)
                continue

            # If chunk is too long, split it into token-sized pieces with overlap
            for i in range(0, len(tokens), self.target_tokens - self.overlap_tokens):
                sub_tokens = tokens[i : i + self.target_tokens]
                sub_text = self.tokenizer.decode(sub_tokens)
                final_chunks.append(sub_text)

        logger.info(f"Chunked text into {len(final_chunks)} chunks from {len(initial_chunks)} initial chunks")

        return final_chunks

    def chunk_with_metadata(self, text: str, file_name: str, page_number: int = None) -> List[Dict]:
        """
        Chunk text and attach metadata to each chunk.

        Args:
            text: Text to chunk
            file_name: Name of the source file
            page_number: Optional page number for the text

        Returns:
            List of dictionaries containing chunk text and metadata
        """
        chunks = self.hybrid_chunk(text)

        chunks_with_metadata = []
        for idx, chunk_text in enumerate(chunks):
            metadata = {
                "chunk_id": idx,
                "file_name": file_name,
                "chunk_text": chunk_text,
                "token_count": self.count_tokens(chunk_text)
            }

            if page_number is not None:
                metadata["page_number"] = page_number

            chunks_with_metadata.append(metadata)

        return chunks_with_metadata


chunking_service = ChunkingService(target_tokens=400, overlap_tokens=50)
