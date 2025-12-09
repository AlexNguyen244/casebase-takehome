"""
FastAPI backend for CaseBase PDF management - Refactored Structure.

This is a refactored version of main.py with better organization:
- Models in models.py
- Helper functions in utils/helpers.py
- Routes split into routes/ directory
- Chat logic remains in main (to be further refactored)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import logging
import io

# Config and Services
from config import settings
from s3_service import s3_service
from embedding_service import EmbeddingService
from pinecone_service import PineconeService
from rag_service import RAGService
from chat_service import ChatService
from pdf_generator import pdf_generator
from email_service import EmailService

# Models
from models import ChatRequest, PDFGenerateRequest

# Routes
from routes.health import router as health_router
from routes.pdfs import init_pdf_routes
from routes.chat import init_chat_routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CaseBase API",
    description="API for managing PDF documents with AWS S3 storage and AI chat",
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

chat_service = ChatService(
    openai_api_key=settings.openai_api_key,
    embedding_service=embedding_service,
    pinecone_service=pinecone_service,
    model="gpt-4o-mini"
)

# Initialize email service
email_service = None
try:
    sendgrid_api_key = settings.sendgrid_api_key
    email_service = EmailService(
        api_key=sendgrid_api_key,
        from_email=settings.sendgrid_from_email
    )
    logger.info("Email service initialized successfully")
except Exception as e:
    logger.warning(f"Email service not initialized: {str(e)}. Email features will be disabled.")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Initializing Pinecone index...")
    await pinecone_service.initialize_index()
    logger.info("Pinecone index initialized successfully")


# Include routers
app.include_router(health_router)

# Initialize and include PDF routes
pdf_router = init_pdf_routes(s3_service, rag_service, pinecone_service, settings)
app.include_router(pdf_router)

# Initialize and include Chat routes
chat_router = init_chat_routes(
    rag_service,
    chat_service,
    s3_service,
    pdf_generator,
    email_service,
    embedding_service,
    pinecone_service,
    settings
)
app.include_router(chat_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
