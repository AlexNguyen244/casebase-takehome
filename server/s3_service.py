"""
AWS S3 service for handling PDF uploads and management.
"""

import boto3
from botocore.exceptions import ClientError
from typing import List, Optional
from datetime import datetime
import logging

from config import settings

logger = logging.getLogger(__name__)


class S3Service:
    """Service class for AWS S3 operations."""

    def __init__(self):
        """Initialize S3 client with AWS credentials."""
        from botocore.config import Config

        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
            config=Config(signature_version='s3v4')
        )
        self.bucket_name = settings.s3_bucket_name

    async def upload_pdf(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str = "application/pdf"
    ) -> dict:
        """
        Upload a PDF file to S3.

        Args:
            file_content: Binary content of the PDF file
            file_name: Name of the file to upload
            content_type: MIME type of the file

        Returns:
            dict: Information about the uploaded file

        Raises:
            ClientError: If upload fails
        """
        try:
            # Generate unique key with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            s3_key = f"pdfs/{timestamp}_{file_name}"

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'original_filename': file_name,
                    'upload_timestamp': timestamp
                }
            )

            # Get file size
            file_size = len(file_content)

            logger.info(f"Successfully uploaded {file_name} to S3 as {s3_key}")

            return {
                "s3_key": s3_key,
                "file_name": file_name,
                "file_size": file_size,
                "uploaded_at": datetime.utcnow().isoformat(),
                "s3_url": f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
            }

        except ClientError as e:
            logger.error(f"Failed to upload {file_name}: {str(e)}")
            raise

    async def list_pdfs(self) -> List[dict]:
        """
        List all PDFs in the S3 bucket.

        Returns:
            List[dict]: List of PDF metadata
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix="pdfs/"
            )

            if 'Contents' not in response:
                return []

            pdfs = []
            for obj in response['Contents']:
                # Get object metadata
                head_response = self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=obj['Key']
                )

                metadata = head_response.get('Metadata', {})
                original_filename = metadata.get('original_filename', obj['Key'].split('/')[-1])

                pdfs.append({
                    "s3_key": obj['Key'],
                    "file_name": original_filename,
                    "file_size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "s3_url": f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{obj['Key']}"
                })

            return pdfs

        except ClientError as e:
            logger.error(f"Failed to list PDFs: {str(e)}")
            raise

    async def delete_pdf(self, s3_key: str) -> bool:
        """
        Delete a PDF from S3.

        Args:
            s3_key: S3 key of the file to delete

        Returns:
            bool: True if deletion was successful

        Raises:
            ClientError: If deletion fails
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            logger.info(f"Successfully deleted {s3_key} from S3")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete {s3_key}: {str(e)}")
            raise

    async def get_pdf_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for downloading a PDF.

        Args:
            s3_key: S3 key of the file
            expiration: URL expiration time in seconds (default: 1 hour)

        Returns:
            str: Presigned URL

        Raises:
            ClientError: If URL generation fails
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )

            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {str(e)}")
            raise


# Global S3 service instance
s3_service = S3Service()
