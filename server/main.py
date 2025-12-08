"""
FastAPI backend for CaseBase PDF management.
Handles PDF uploads to AWS S3 and provides endpoints for CRUD operations.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
import logging

from config import settings
from s3_service import s3_service
from embedding_service import EmbeddingService
from pinecone_service import PineconeService
from rag_service import RAGService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CaseBase API",
    description="API for managing PDF documents with AWS S3 storage",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG services
embedding_service = EmbeddingService(
    api_key=settings.openai_api_key,
    model="text-embedding-3-small"
)

pinecone_service = PineconeService(
    api_key=settings.pinecone_api_key,
    index_name=settings.pinecone_index_name,
    dimension=settings.pinecone_dimension,
    cloud=settings.pinecone_cloud,
    region=settings.pinecone_region
)

rag_service = RAGService(
    embedding_service=embedding_service,
    pinecone_service=pinecone_service
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Initializing Pinecone index...")
    await pinecone_service.initialize_index()
    logger.info("Pinecone index initialized successfully")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "CaseBase API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/pdfs/upload", status_code=status.HTTP_201_CREATED)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file to S3.

    Args:
        file: PDF file to upload

    Returns:
        dict: Information about the uploaded file
    """
    # Validate file type
    if not file.content_type == "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )

    # Validate file extension
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have .pdf extension"
        )

    try:
        # Read file content
        content = await file.read()

        # Upload to S3
        s3_result = await s3_service.upload_pdf(
            file_content=content,
            file_name=file.filename,
            content_type=file.content_type
        )

        logger.info(f"Successfully uploaded {file.filename} to S3")

        # Process through RAG pipeline
        rag_result = await rag_service.process_pdf(
            file_content=content,
            file_name=file.filename
        )

        logger.info(f"Successfully processed {file.filename} through RAG pipeline")

        return {
            "message": "PDF uploaded and processed successfully",
            "s3_data": s3_result,
            "rag_data": rag_result
        }

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload PDF: {str(e)}"
        )


@app.post("/api/pdfs/upload-multiple", status_code=status.HTTP_201_CREATED)
async def upload_multiple_pdfs(files: List[UploadFile] = File(...)):
    """
    Upload multiple PDF files to S3.

    Args:
        files: List of PDF files to upload

    Returns:
        dict: Information about all uploaded files
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )

    results = []
    errors = []

    for file in files:
        # Validate file type
        if not file.content_type == "application/pdf" or not file.filename.lower().endswith('.pdf'):
            errors.append({
                "file_name": file.filename,
                "error": "Only PDF files are allowed"
            })
            continue

        try:
            # Read file content
            content = await file.read()

            # Upload to S3
            result = await s3_service.upload_pdf(
                file_content=content,
                file_name=file.filename,
                content_type=file.content_type
            )

            results.append(result)
            logger.info(f"Successfully uploaded {file.filename}")

        except Exception as e:
            logger.error(f"Failed to upload {file.filename}: {str(e)}")
            errors.append({
                "file_name": file.filename,
                "error": str(e)
            })

    return {
        "message": f"Uploaded {len(results)} of {len(files)} files",
        "successful_uploads": results,
        "errors": errors
    }


@app.get("/api/pdfs")
async def list_pdfs():
    """
    List all PDF files in S3.

    Returns:
        dict: List of all PDFs with metadata
    """
    try:
        pdfs = await s3_service.list_pdfs()

        return {
            "message": "PDFs retrieved successfully",
            "count": len(pdfs),
            "data": pdfs
        }

    except Exception as e:
        logger.error(f"Failed to list PDFs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve PDFs: {str(e)}"
        )


@app.delete("/api/pdfs/{s3_key:path}")
async def delete_pdf(s3_key: str):
    """
    Delete a PDF file from S3 and remove its vectors from Pinecone.

    Args:
        s3_key: S3 key of the file to delete

    Returns:
        dict: Confirmation message
    """
    try:
        # Extract file name from s3_key
        file_name = s3_key.split('/')[-1] if '/' in s3_key else s3_key

        # Delete from S3
        await s3_service.delete_pdf(s3_key)

        # Delete from Pinecone
        pinecone_result = await pinecone_service.delete_by_file(file_name)

        return {
            "message": "PDF deleted successfully from S3 and Pinecone",
            "s3_key": s3_key,
            "pinecone_result": pinecone_result
        }

    except Exception as e:
        logger.error(f"Failed to delete PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete PDF: {str(e)}"
        )


@app.get("/api/pdfs/{s3_key:path}/download-url")
async def get_download_url(s3_key: str, expiration: int = 3600):
    """
    Get a presigned URL for downloading a PDF.

    Args:
        s3_key: S3 key of the file
        expiration: URL expiration time in seconds (default: 1 hour)

    Returns:
        dict: Presigned download URL
    """
    try:
        url = await s3_service.get_pdf_url(s3_key, expiration)

        return {
            "message": "Download URL generated successfully",
            "url": url,
            "expires_in": expiration
        }

    except Exception as e:
        logger.error(f"Failed to generate download URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )


@app.post("/api/rag/query")
async def query_documents(query: str, top_k: int = 5, file_name: str = None):
    """
    Query the RAG system with a natural language question.

    Args:
        query: Question or query text
        top_k: Number of results to return (default: 5)
        file_name: Optional file name to filter results

    Returns:
        dict: Query results with relevant document chunks
    """
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter is required"
        )

    try:
        results = await rag_service.query_documents(
            query_text=query,
            top_k=top_k,
            file_filter=file_name
        )

        return {
            "message": "Query completed successfully",
            "data": results
        }

    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
