"""
PDF parsing service using pdfplumber.
Extracts text content from PDF files.
"""

import pdfplumber
from io import BytesIO
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class PDFParser:
    """Service for parsing PDF files and extracting text content."""

    @staticmethod
    async def parse_pdf(file_content: bytes, file_name: str) -> Dict[str, any]:
        """
        Parse PDF file and extract text content.

        Args:
            file_content: Raw PDF file bytes
            file_name: Name of the PDF file

        Returns:
            Dict containing parsed metadata and text content
        """
        try:
            # Create BytesIO object from file content
            pdf_file = BytesIO(file_content)

            # Extract text from PDF
            pages_content = []
            total_pages = 0

            with pdfplumber.open(pdf_file) as pdf:
                total_pages = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract text from page
                    text = page.extract_text()

                    if text:
                        pages_content.append({
                            "page_number": page_num,
                            "text": text.strip()
                        })

            # Combine all pages into single text
            full_text = "\n\n".join([page["text"] for page in pages_content])

            logger.info(f"Successfully parsed {file_name}: {total_pages} pages, {len(full_text)} characters")

            return {
                "file_name": file_name,
                "total_pages": total_pages,
                "pages": pages_content,
                "full_text": full_text,
                "character_count": len(full_text)
            }

        except Exception as e:
            logger.error(f"Failed to parse PDF {file_name}: {str(e)}")
            raise Exception(f"PDF parsing failed: {str(e)}")


pdf_parser = PDFParser()
