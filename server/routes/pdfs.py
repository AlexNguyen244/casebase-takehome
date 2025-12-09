"""
PDF management endpoints for upload, list, delete, and viewing PDFs.
"""

import logging
import io
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pdfs", tags=["PDFs"])


def init_pdf_routes(s3_service, rag_service, pinecone_service, settings):
    """
    Initialize PDF routes with service dependencies.

    Args:
        s3_service: S3 service instance
        rag_service: RAG service instance
        pinecone_service: Pinecone service instance
        settings: Application settings
    """

    @router.post("/upload", status_code=status.HTTP_201_CREATED)
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

            # Process through RAG pipeline using S3 key for uniqueness
            rag_result = await rag_service.process_pdf(
                file_content=content,
                file_name=s3_result["s3_key"]
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

    @router.post("/upload-multiple", status_code=status.HTTP_201_CREATED)
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

    @router.get("")
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

    @router.delete("/{s3_key:path}")
    async def delete_pdf(s3_key: str):
        """
        Delete a PDF file from S3 and remove its vectors from Pinecone.

        Args:
            s3_key: S3 key of the file to delete

        Returns:
            dict: Confirmation message
        """
        try:
            # Delete from S3
            await s3_service.delete_pdf(s3_key)

            # Delete from Pinecone using the full S3 key
            pinecone_result = await pinecone_service.delete_by_file(s3_key)

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

    @router.get("/{s3_key:path}/download-url")
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
            # Return a proxy URL through our backend instead of presigned URL
            proxy_url = f"{settings.backend_url}/api/pdfs/view/{s3_key}"

            return {
                "message": "Download URL generated successfully",
                "url": proxy_url,
                "expires_in": expiration
            }

        except Exception as e:
            logger.error(f"Failed to generate download URL: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate download URL: {str(e)}"
            )

    @router.get("/view/{s3_key:path}")
    async def view_pdf(s3_key: str):
        """
        Stream PDF directly from S3 through the backend.

        Args:
            s3_key: S3 key of the file

        Returns:
            StreamingResponse: PDF file stream
        """
        try:
            logger.info(f"[PDF VIEW] Requesting PDF from S3: {s3_key}")

            # Get the PDF from S3
            response = s3_service.s3_client.get_object(
                Bucket=s3_service.bucket_name,
                Key=s3_key
            )

            # Stream the PDF
            pdf_content = response['Body'].read()
            logger.info(f"[PDF VIEW] Retrieved PDF from S3: {s3_key}, size={len(pdf_content)} bytes")

            return StreamingResponse(
                io.BytesIO(pdf_content),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename={s3_key.split('/')[-1]}",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )

        except Exception as e:
            logger.error(f"Failed to stream PDF: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to stream PDF: {str(e)}"
            )

    return router
