"""
FastAPI backend for CaseBase PDF management.
Handles PDF uploads to AWS S3 and provides endpoints for CRUD operations.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import logging

from config import settings
from s3_service import s3_service
from embedding_service import EmbeddingService
from pinecone_service import PineconeService
from rag_service import RAGService
from chat_service import ChatService
from pdf_generator import pdf_generator
from email_service import EmailService
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import io

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

chat_service = ChatService(
    openai_api_key=settings.openai_api_key,
    embedding_service=embedding_service,
    pinecone_service=pinecone_service,
    model="gpt-4o-mini"
)

# Initialize email service (will use env variable for API key)
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
        # Return a proxy URL through our backend instead of presigned URL
        proxy_url = f"http://localhost:8000/api/pdfs/view/{s3_key}"

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


@app.get("/api/pdfs/view/{s3_key:path}")
async def view_pdf(s3_key: str):
    """
    Stream PDF directly from S3 through the backend.

    Args:
        s3_key: S3 key of the file

    Returns:
        StreamingResponse: PDF file stream
    """
    try:
        from fastapi.responses import StreamingResponse
        import io

        # Get the PDF from S3
        response = s3_service.s3_client.get_object(
            Bucket=s3_service.bucket_name,
            Key=s3_key
        )

        # Stream the PDF
        pdf_content = response['Body'].read()

        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename={s3_key.split('/')[-1]}"
            }
        )

    except Exception as e:
        logger.error(f"Failed to stream PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stream PDF: {str(e)}"
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


# Pydantic models for chat endpoint
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    file_filter: Optional[str] = None
    top_k: Optional[int] = 5


class PDFGenerateRequest(BaseModel):
    prompt: str = None
    response: str = None
    conversation_history: Optional[List[ChatMessage]] = []
    title: Optional[str] = None


@app.post("/api/chat")
async def chat_with_documents(request: ChatRequest):
    """
    Chat with the AI assistant using RAG.
    Also detects PDF creation requests and handles them automatically.

    Args:
        request: Chat request with message and optional history

    Returns:
        dict: AI response with sources and metadata, or PDF generation result
    """
    try:
        # Convert Pydantic models to dicts for the chat service
        history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]

        # Check if user wants to email the PDF
        email_intent = await chat_service.detect_email_intent(request.message)

        # Check if user is requesting PDF creation using semantic detection
        pdf_intent = await chat_service.detect_pdf_creation_intent(request.message)

        if pdf_intent["is_pdf_request"]:
            logger.info(f"PDF creation request detected. Type: {pdf_intent['type']}, Confidence: {pdf_intent.get('confidence', 0):.3f}")

            # Generate the PDF based on type
            if pdf_intent["type"] == "history":
                # Create PDF from conversation history
                if not history or len(history) == 0:
                    return {
                        "success": True,
                        "data": {
                            "message": "I'd love to create a PDF of our conversation, but we don't have any chat history yet. Please have a conversation with me first!",
                            "sources": [],
                            "is_pdf_response": False
                        }
                    }

                # Generate AI summary of the conversation
                logger.info("Generating AI summary of conversation history")

                # Build conversation context for summarization
                conversation_text = []
                for msg in history:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    if role == 'user':
                        conversation_text.append(f"User: {content}")
                    elif role == 'assistant':
                        conversation_text.append(f"Assistant: {content}")

                conversation_context = "\n\n".join(conversation_text)

                # Create summarization prompt
                summary_prompt = f"""You are tasked with creating a comprehensive summary document of a conversation between a user and an AI assistant.

CONVERSATION HISTORY:
{conversation_context}

Please create a well-structured summary document that includes:

1. **Overview** - A brief overview of what was discussed (2-3 sentences)

2. **Key Topics Discussed** - List the main topics or questions that were covered in bullet points

3. **Important Information** - Highlight any important facts, findings, or insights that were shared

4. **Action Items or Conclusions** (if any) - Note any decisions made, recommendations given, or next steps mentioned

Format your response in clean markdown with proper headers (##), bullet points, and bold text where appropriate. Make it professional and easy to read."""

                # Generate summary using OpenAI
                summary_response = await chat_service.client.chat.completions.create(
                    model=chat_service.model,
                    messages=[
                        {"role": "system", "content": "You are a professional document summarizer. Create clear, well-structured summaries."},
                        {"role": "user", "content": summary_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )

                conversation_summary = summary_response.choices[0].message.content

                logger.info("Summary generated successfully")

                # Create PDF from the summary
                pdf_bytes = pdf_generator.generate_from_prompt(
                    prompt="Conversation Summary",
                    response=conversation_summary
                )
                filename = "conversation_summary.pdf"

            elif pdf_intent["type"] == "vector_content":
                # Create PDF from vector storage content
                # First, get the actual query by removing PDF-related phrases
                query = request.message

                # Generate response to get the content from vector store
                logger.info(f"Retrieving content from vector store for: {query}")

                # Get embedding for the query
                query_embedding = await embedding_service.generate_embedding(query)

                # Retrieve relevant chunks from Pinecone
                metadata_filter = {"file_name": request.file_filter} if request.file_filter else None
                results = await pinecone_service.query(
                    query_embedding=query_embedding,
                    top_k=10,  # Get more chunks for comprehensive PDF
                    filter=metadata_filter
                )

                if not results or len(results) == 0:
                    return {
                        "success": True,
                        "data": {
                            "message": "I couldn't find any relevant content in the documents to create a PDF. Please try a different query or upload documents first.",
                            "sources": [],
                            "is_pdf_response": False
                        }
                    }

                # Build context from retrieved chunks
                context_parts = []
                for result in results:
                    metadata = result.get("metadata", {})
                    chunk_text = metadata.get("chunk_text", "")
                    context_parts.append(chunk_text)

                context = "\n\n".join(context_parts)

                # Generate AI summary of the content
                system_prompt = f"""You are an AI assistant. Provide a comprehensive summary and analysis based on the following document content.

DOCUMENT CONTENT:
{context}

Create a well-structured response that summarizes and explains the key information."""

                response = await chat_service.client.chat.completions.create(
                    model=chat_service.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )

                ai_summary = response.choices[0].message.content

                # Create PDF with the query and AI summary
                pdf_bytes = pdf_generator.generate_from_prompt(
                    prompt=query,
                    response=ai_summary
                )
                filename = "document_content.pdf"

            else:
                # Fallback - shouldn't reach here
                return {
                    "success": True,
                    "data": {
                        "message": "I couldn't determine what type of PDF you want. Please specify if you want a PDF of our conversation or content from the documents.",
                        "sources": [],
                        "is_pdf_response": False
                    }
                }

            # Check if user wants to email the PDF
            if email_intent["wants_email"] and email_intent["email_address"]:
                # Email the PDF
                email_address = email_intent["email_address"]

                # Check if email service is available
                if not email_service:
                    return {
                        "success": True,
                        "data": {
                            "message": "I created the PDF, but email service is not configured. Please contact your administrator to enable email features.",
                            "sources": [],
                            "is_pdf_response": False
                        }
                    }

                try:
                    # Determine email subject based on PDF type
                    if pdf_intent["type"] == "history":
                        subject = "Your CaseBase Conversation Summary"
                    else:
                        subject = "Your CaseBase Document Report"

                    # Send email with PDF attachment
                    await email_service.send_pdf_email(
                        to_email=email_address,
                        subject=subject,
                        pdf_bytes=pdf_bytes,
                        pdf_filename=filename
                    )

                    logger.info(f"PDF successfully emailed to {email_address}")

                    return {
                        "success": True,
                        "data": {
                            "message": f"✅ Perfect! I've created your PDF and sent it to **{email_address}**. Please check your inbox (and spam folder just in case).",
                            "sources": [],
                            "is_pdf_response": True,
                            "email_sent": True,
                            "email_address": email_address
                        }
                    }

                except Exception as e:
                    logger.error(f"Failed to send email: {str(e)}")
                    # Fallback to download if email fails - still upload to S3
                    from datetime import datetime
                    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    s3_key = f"generated_pdfs/{timestamp}_{filename}"

                    s3_service.s3_client.put_object(
                        Bucket=s3_service.bucket_name,
                        Key=s3_key,
                        Body=pdf_bytes,
                        ContentType="application/pdf",
                        Metadata={
                            'generated_at': timestamp,
                            'type': pdf_intent["type"]
                        }
                    )

                    download_url = f"http://localhost:8000/api/pdfs/view/{s3_key}"

                    return {
                        "success": True,
                        "data": {
                            "message": f"I created the PDF but couldn't send it to {email_address}. Error: {str(e)}. You can download it here instead: [Download PDF]({download_url})",
                            "sources": [],
                            "is_pdf_response": True,
                            "pdf_url": download_url,
                            "email_sent": False
                        }
                    }

            else:
                # No email request - provide download link
                # Upload PDF to S3
                from datetime import datetime
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                s3_key = f"generated_pdfs/{timestamp}_{filename}"

                s3_service.s3_client.put_object(
                    Bucket=s3_service.bucket_name,
                    Key=s3_key,
                    Body=pdf_bytes,
                    ContentType="application/pdf",
                    Metadata={
                        'generated_at': timestamp,
                        'type': pdf_intent["type"]
                    }
                )

                logger.info(f"PDF uploaded to S3: {s3_key}")

                # Return download URL
                download_url = f"http://localhost:8000/api/pdfs/view/{s3_key}"

                return {
                    "success": True,
                    "data": {
                        "message": f"I've created your PDF! You can download it here: [Download PDF]({download_url})",
                        "sources": [],
                        "is_pdf_response": True,
                        "pdf_url": download_url,
                        "s3_key": s3_key
                    }
                }

        # Normal chat flow (not a PDF request)
        result = await chat_service.chat_with_documents(
            message=request.message,
            conversation_history=history if history else None,
            file_filter=request.file_filter,
            top_k=request.top_k
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Chat request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat: {str(e)}"
        )


@app.post("/api/generate-pdf")
async def generate_pdf(request: PDFGenerateRequest):
    """
    Generate a PDF from either a prompt/response pair or chat history.

    Args:
        request: PDF generation request with either prompt/response or conversation history

    Returns:
        StreamingResponse: PDF file
    """
    try:
        # Determine which generation method to use
        if request.prompt and request.response:
            # Generate from prompt/response
            pdf_bytes = pdf_generator.generate_from_prompt(
                prompt=request.prompt,
                response=request.response
            )
            filename = "casebase_report.pdf"
        elif request.conversation_history and len(request.conversation_history) > 0:
            # Generate from chat history
            messages = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]
            pdf_bytes = pdf_generator.generate_from_chat_history(
                messages=messages,
                title=request.title
            )
            filename = request.title.replace(" ", "_") + ".pdf" if request.title else "conversation_history.pdf"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide either prompt/response or conversation_history"
            )

        # Return PDF as download
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
