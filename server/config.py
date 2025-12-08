"""
Configuration settings for the FastAPI backend.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    s3_bucket_name: str

    openai_api_key: str
    pinecone_api_key: str
    pinecone_index_name: str = "casebase-documents"
    pinecone_dimension: int = 1536
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    allowed_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def origins_list(self) -> List[str]:
        """Convert comma-separated origins string to list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]


settings = Settings()
