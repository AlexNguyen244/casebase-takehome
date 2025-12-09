"""
Helper functions for conversation processing and PDF tracking.
"""

import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def extract_most_recent_email_from_history(history: List[Dict]) -> Optional[str]:
    """
    Extract the most recent email address mentioned in the conversation history.

    Args:
        history: List of conversation messages

    Returns:
        The most recent email address found, or None
    """
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    # Search from most recent to oldest
    for msg in reversed(history):
        content = msg.get('content', '')
        emails = re.findall(email_pattern, content)
        if emails:
            # Return the first (most recent) email found
            logger.info(f"Found remembered email from history: {emails[0]}")
            return emails[0]

    return None


def extract_generated_pdfs_from_history(history: List[Dict]) -> List[Dict]:
    """
    Extract all generated PDF S3 keys from the conversation history.

    Args:
        history: List of conversation messages

    Returns:
        List of dicts with 's3_key' and 'timestamp' for each generated PDF (chronological order)
    """
    generated_pdfs = []
    s3_key_pattern = r'/api/pdfs/view/(generated_pdfs/[^\s\)]+\.pdf)'

    for msg in history:
        if msg.get('role') == 'assistant':
            content = msg.get('content', '')
            # Look for PDF download links
            if 'Download PDF' in content or '/api/pdfs/view/' in content:
                # Extract S3 key from the URL
                matches = re.findall(s3_key_pattern, content)
                for s3_key in matches:
                    # Extract timestamp from the S3 key format: generated_pdfs/20251209_195408_document_content.pdf
                    timestamp_match = re.search(r'generated_pdfs/(\d{8}_\d{6})_', s3_key)
                    timestamp = timestamp_match.group(1) if timestamp_match else None

                    generated_pdfs.append({
                        's3_key': s3_key,
                        'timestamp': timestamp,
                        'filename': s3_key.split('/')[-1]
                    })

    logger.info(f"Found {len(generated_pdfs)} generated PDFs in conversation history")
    return generated_pdfs


def get_source_documents_for_pdf(s3_service, pdf_s3_key: str) -> List[str]:
    """
    Retrieve source document S3 keys from a generated PDF's metadata.

    Args:
        s3_service: S3 service instance
        pdf_s3_key: S3 key of the generated PDF

    Returns:
        List of source document S3 keys
    """
    try:
        # Get the PDF metadata from S3
        response = s3_service.s3_client.head_object(
            Bucket=s3_service.bucket_name,
            Key=pdf_s3_key
        )

        # Extract source_documents from metadata
        metadata = response.get('Metadata', {})
        source_docs_str = metadata.get('source_documents', '')

        if source_docs_str:
            # Split comma-separated string into list
            source_docs = [doc.strip() for doc in source_docs_str.split(',') if doc.strip()]
            logger.info(f"Found {len(source_docs)} source documents for PDF {pdf_s3_key}: {source_docs}")
            return source_docs
        else:
            logger.info(f"No source documents found in metadata for PDF {pdf_s3_key}")
            return []

    except Exception as e:
        logger.error(f"Failed to get source documents for PDF {pdf_s3_key}: {str(e)}")
        return []
