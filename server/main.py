"""
FastAPI backend for CaseBase PDF management.
Handles PDF uploads to AWS S3 and provides endpoints for CRUD operations.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict
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
import re

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


@app.post("/api/chat")
async def chat_with_documents(request: ChatRequest):
    """
    Chat with the AI assistant using RAG.
    Also detects and handles:
    - Sending existing documents via email
    - PDF creation requests (from chat history or document content)
    - Normal chat conversations

    Args:
        request: Chat request with message and optional history

    Returns:
        dict: AI response with sources and metadata, PDF generation result, or document send confirmation
    """
    try:
        # Convert Pydantic models to dicts for the chat service
        history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]

        # Extract the most recent email address from conversation history
        remembered_email = extract_most_recent_email_from_history(history)
        if remembered_email:
            logger.info(f"Using remembered email address: {remembered_email}")

        # Check if there was a PDF creation in recent history (not just the last message)
        # This helps us understand if "send it" refers to the PDF or documents
        previous_was_pdf_creation = False
        previous_pdf_topic = None
        previous_pdf_s3_key = None

        if history and len(history) >= 2:
            # Check recent assistant messages (up to last 4 messages) for PDF creation
            for i in range(len(history) - 1, max(0, len(history) - 5), -1):
                if history[i].get('role') == 'assistant':
                    assistant_msg = history[i].get('content', '')
                    # Check if it contains PDF download link
                    if 'Download PDF' in assistant_msg or '/api/pdfs/view/' in assistant_msg:
                        previous_was_pdf_creation = True

                        # Extract S3 key from the PDF URL
                        # URL format: http://localhost:8000/api/pdfs/view/generated_pdfs/20251209_195408_document_content.pdf
                        s3_key_match = re.search(r'/api/pdfs/view/([^\s\)]+)', assistant_msg)
                        if s3_key_match:
                            previous_pdf_s3_key = s3_key_match.group(1)
                            logger.info(f"Found previous PDF S3 key: {previous_pdf_s3_key}")

                        # Try to find the user's request that triggered the PDF
                        if i > 0:
                            for j in range(i - 1, -1, -1):
                                if history[j].get('role') == 'user':
                                    previous_pdf_topic = history[j].get('content', '')
                                    break
                        logger.info(f"Detected previous PDF creation. Topic: {previous_pdf_topic}")
                        break  # Found the PDF, stop looking

        # Check if user is providing email after being asked for it
        # Look for messages like "My email is X" or just an email address
        user_provided_email_only = False
        provided_email = None
        was_asked_for_pdf_email = False
        was_asked_for_docs_email = False
        was_asked_for_bulk_pdf_email = False

        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', request.message):
            # Check if previous assistant message asked for email
            if history and len(history) >= 1:
                for i in range(len(history) - 1, -1, -1):
                    if history[i].get('role') == 'assistant':
                        last_assistant_msg = history[i].get('content', '')
                        if 'email address would you like me to send' in last_assistant_msg.lower():
                            user_provided_email_only = True
                            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', request.message)
                            if email_match:
                                provided_email = email_match.group(0)
                                logger.info(f"User provided email after being asked: {provided_email}")

                            # Determine what they were asked about by checking the message
                            if 'pdfs' in last_assistant_msg.lower():
                                # Plural "PDFs" indicates bulk send
                                was_asked_for_bulk_pdf_email = True
                            elif 'pdf' in last_assistant_msg.lower():
                                # Singular "PDF" indicates single PDF
                                was_asked_for_pdf_email = True
                            else:
                                was_asked_for_docs_email = True
                        break

        # Check email intent first to see if user is trying to email something
        email_intent = await chat_service.detect_email_intent(request.message, history, remembered_email)

        # Check if user wants to send existing documents via email (not create PDF)
        # Only skip this check if BOTH: (1) previous was PDF creation AND (2) user wants to email
        # This ensures "Find documents and send" works even after PDF creation
        send_docs_intent = {"wants_send_docs": False}
        skip_send_docs_check = previous_was_pdf_creation and email_intent["wants_email"]

        if not skip_send_docs_check:
            send_docs_intent = await chat_service.detect_send_documents_intent(request.message, history, remembered_email)

        # Initialize bulk_send_intent - may be set by email follow-up handler below
        bulk_send_intent = None

        # If user provided email only after being asked, handle accordingly
        if user_provided_email_only and provided_email:
            logger.info(f"User provided email only. was_asked_for_pdf_email={was_asked_for_pdf_email}, previous_was_pdf_creation={previous_was_pdf_creation}, previous_pdf_s3_key={previous_pdf_s3_key}")
            if was_asked_for_pdf_email and previous_was_pdf_creation and previous_pdf_s3_key:
                # User was asked for email to send PDF, now they provided it
                logger.info(f"User provided email for PDF: {provided_email}, sending PDF: {previous_pdf_s3_key}")

                # Check if email service is available
                if not email_service:
                    return {
                        "success": True,
                        "data": {
                            "message": "Email service is not configured. Please contact your administrator.",
                            "sources": [],
                            "is_pdf_response": False
                        }
                    }

                try:
                    # Download the existing PDF from S3
                    s3_response = s3_service.s3_client.get_object(
                        Bucket=s3_service.bucket_name,
                        Key=previous_pdf_s3_key
                    )
                    pdf_bytes = s3_response['Body'].read()
                    filename = previous_pdf_s3_key.split('/')[-1]

                    # Send email with the PDF
                    await email_service.send_pdf_email(
                        to_email=provided_email,
                        subject="Your CaseBase Document Report",
                        pdf_bytes=pdf_bytes,
                        pdf_filename=filename
                    )

                    return {
                        "success": True,
                        "data": {
                            "message": f"✅ Perfect! I've sent the PDF to **{provided_email}**. Please check your inbox (and spam folder just in case).",
                            "sources": [],
                            "is_pdf_response": True,
                            "email_sent": True,
                            "email_address": provided_email
                        }
                    }
                except Exception as e:
                    logger.error(f"Failed to email PDF: {str(e)}")
                    return {
                        "success": True,
                        "data": {
                            "message": f"I found the PDF but couldn't send it. Error: {str(e)}",
                            "sources": [],
                            "is_pdf_response": False
                        }
                    }

            elif was_asked_for_bulk_pdf_email:
                # Look for the previous bulk send request
                for i in range(len(history) - 1, -1, -1):
                    if history[i].get('role') == 'user':
                        prev_user_msg = history[i].get('content', '')
                        # Check if it was a bulk send request
                        if any(keyword in prev_user_msg.lower() for keyword in ['send', 'email', 'pdf']):
                            logger.info(f"Retrying bulk PDF send with provided email: {provided_email}")
                            # Recheck bulk send intent with the previous message and the new email
                            bulk_send_intent = await chat_service.detect_bulk_pdf_send_intent(prev_user_msg, history, provided_email)
                            if bulk_send_intent["wants_bulk_send"]:
                                # Override the email address with the one just provided
                                bulk_send_intent["email_address"] = provided_email

                                # Now proceed to bulk send logic with the email
                                # This will be handled by the bulk send block below
                            break

            elif was_asked_for_docs_email:
                # Look for the topic from the previous incomplete send request
                for i in range(len(history) - 1, -1, -1):
                    if history[i].get('role') == 'user':
                        prev_user_msg = history[i].get('content', '')
                        # Check if it was a send documents request
                        if any(keyword in prev_user_msg.lower() for keyword in ['find', 'send', 'email', 'documents']):
                            logger.info(f"Retrying send documents with provided email: {provided_email}")
                            # Recheck send documents intent with the previous message and the new email
                            send_docs_intent = await chat_service.detect_send_documents_intent(prev_user_msg, history, provided_email)
                            if send_docs_intent["wants_send_docs"]:
                                # Override the email address with the one just provided
                                send_docs_intent["email_address"] = provided_email
                            break

        if send_docs_intent["wants_send_docs"]:
            # User wants to send existing documents
            logger.info(f"Send documents request detected. Topic: {send_docs_intent['topic']}, Email: {send_docs_intent['email_address']}")

            email_address = send_docs_intent["email_address"]
            topic = send_docs_intent["topic"]

            # Check if email address is missing
            if not email_address or email_address == "":
                logger.info("Email address missing in send documents request")
                return {
                    "success": True,
                    "data": {
                        "message": f"I'd be happy to send you documents about {topic}! What email address would you like me to send them to?",
                        "sources": [],
                        "is_send_docs_response": False
                    }
                }

            # Check if email service is available
            if not email_service:
                return {
                    "success": True,
                    "data": {
                        "message": "Email service is not configured. Please contact your administrator to enable email features.",
                        "sources": [],
                        "is_pdf_response": False
                    }
                }

            # Query vector database to find relevant documents
            query_embedding = await embedding_service.generate_embedding(topic)

            results = await pinecone_service.query(
                query_embedding=query_embedding,
                top_k=10,
                filter=None
            )

            if not results or len(results) == 0:
                return {
                    "success": True,
                    "data": {
                        "message": f"I couldn't find any documents related to '{topic}'. Please try a different search term or upload documents first.",
                        "sources": [],
                        "is_send_docs_response": False
                    }
                }

            # Build context with source labels for AI filtering
            context_parts = []
            available_sources = {}

            for result in results:
                metadata = result.get("metadata", {})
                chunk_text = metadata.get("chunk_text", "")
                file_name = metadata.get("file_name", "")

                if file_name:
                    simple_name = file_name.split('/')[-1].replace('.pdf', '')
                    available_sources[simple_name] = file_name
                    # Limit chunk preview to avoid token limits
                    chunk_preview = chunk_text[:300] if len(chunk_text) > 300 else chunk_text
                    context_parts.append(f"[Source: {simple_name}]\n{chunk_preview}")

            context = "\n\n".join(context_parts)

            logger.info(f"Retrieved chunks from {len(available_sources)} unique documents")

            # Use AI to filter and identify which documents are actually relevant
            filter_prompt = f"""You are analyzing document chunks to determine which documents are relevant to a specific topic.

TOPIC: {topic}

DOCUMENT CHUNKS:
{context}

TASK: Determine which source documents are ACTUALLY about "{topic}".
- Only include documents that are primarily about or directly related to {topic}
- Do NOT include documents that only mention {topic} in passing or tangentially
- Be strict and selective - if a document isn't clearly about the topic, exclude it

List ONLY the relevant source documents.
Format: RELEVANT_DOCS: source1, source2, source3
Use the exact source names shown in [Source: ...] tags above.

Your response:"""

            filter_response = await chat_service.client.chat.completions.create(
                model=chat_service.model,
                messages=[
                    {"role": "system", "content": "You are a document relevance analyzer. Be strict and selective about relevance."},
                    {"role": "user", "content": filter_prompt}
                ],
                temperature=0,
                max_tokens=200
            )

            ai_filter_result = filter_response.choices[0].message.content

            # Parse the AI response to get relevant documents
            document_files = set()
            if "RELEVANT_DOCS:" in ai_filter_result:
                parts = ai_filter_result.split("RELEVANT_DOCS:")
                docs_line = parts[1].strip()
                relevant_doc_names = [s.strip().rstrip('.').strip() for s in docs_line.split(',')]
                relevant_doc_names = [name for name in relevant_doc_names if name]

                # Map back to full file paths
                for name in relevant_doc_names:
                    if name in available_sources:
                        document_files.add(available_sources[name])
                        logger.info(f"AI identified relevant document: {name}")
                    else:
                        logger.warning(f"AI mentioned document '{name}' not found in available sources")

                logger.info(f"AI filtered to {len(document_files)} relevant document(s) for topic '{topic}'")
            else:
                # Fallback: if AI doesn't follow format, use all documents
                document_files = set(available_sources.values())
                logger.warning(f"AI didn't follow format, using all {len(document_files)} documents")

            # Download documents from S3
            documents_to_send = []
            for file_path in document_files:
                try:
                    s3_response = s3_service.s3_client.get_object(
                        Bucket=s3_service.bucket_name,
                        Key=file_path
                    )
                    doc_bytes = s3_response['Body'].read()

                    # Extract filename from S3 key
                    display_filename = file_path.split('/')[-1]

                    documents_to_send.append({
                        'bytes': doc_bytes,
                        'filename': display_filename
                    })

                    logger.info(f"Downloaded document: {display_filename}")

                except Exception as e:
                    logger.warning(f"Failed to download document {file_path}: {str(e)}")
                    continue

            if not documents_to_send:
                return {
                    "success": True,
                    "data": {
                        "message": "I found relevant documents but couldn't retrieve them from storage. Please try again later.",
                        "sources": [],
                        "is_send_docs_response": False
                    }
                }

            # Send documents via email
            try:
                await email_service.send_documents_email(
                    to_email=email_address,
                    subject=f"Documents related to: {topic}",
                    documents=documents_to_send
                )

                doc_list = "\n".join([f"- {doc['filename']}" for doc in documents_to_send])

                return {
                    "success": True,
                    "data": {
                        "message": f"✅ Perfect! I've sent {len(documents_to_send)} document(s) related to '{topic}' to **{email_address}**.\n\nDocuments sent:\n{doc_list}\n\nPlease check your inbox (and spam folder just in case).",
                        "sources": [],
                        "is_send_docs_response": True,
                        "email_sent": True,
                        "email_address": email_address,
                        "documents_count": len(documents_to_send)
                    }
                }

            except Exception as e:
                logger.error(f"Failed to send documents email: {str(e)}")
                return {
                    "success": True,
                    "data": {
                        "message": f"I found the documents but couldn't send the email. Error: {str(e)}",
                        "sources": [],
                        "is_send_docs_response": False
                    }
                }

        # Check if user wants to bulk send generated PDFs (if not already set by email follow-up handler)
        if bulk_send_intent is None:
            bulk_send_intent = await chat_service.detect_bulk_pdf_send_intent(request.message, history, remembered_email)

        if bulk_send_intent and bulk_send_intent["wants_bulk_send"]:
            logger.info(f"Bulk PDF send request detected. Selection: {bulk_send_intent['selection_type']}, Count: {bulk_send_intent['count']}, Email: {bulk_send_intent['email_address']}")

            email_address = bulk_send_intent["email_address"]

            # Check if email address is missing
            if not email_address or email_address == "":
                logger.info("Email address missing in bulk send request")
                return {
                    "success": True,
                    "data": {
                        "message": "I'd be happy to send you the PDFs! What email address would you like me to send them to?",
                        "sources": [],
                        "is_bulk_send_response": False,
                        "awaiting_email_for": "bulk_pdfs"
                    }
                }

            # Check if email service is available
            if not email_service:
                return {
                    "success": True,
                    "data": {
                        "message": "Email service is not configured. Please contact your administrator to enable email features.",
                        "sources": [],
                        "is_bulk_send_response": False
                    }
                }

            # Extract generated PDFs from conversation history
            all_generated_pdfs = extract_generated_pdfs_from_history(history)

            if not all_generated_pdfs or len(all_generated_pdfs) == 0:
                return {
                    "success": True,
                    "data": {
                        "message": "I couldn't find any generated PDFs in our conversation history. Please create some PDFs first!",
                        "sources": [],
                        "is_bulk_send_response": False
                    }
                }

            # Select PDFs based on selection_type
            selected_pdfs = []
            selection_type = bulk_send_intent["selection_type"]
            count = bulk_send_intent["count"]

            if selection_type == "all":
                selected_pdfs = all_generated_pdfs
                logger.info(f"Selecting all {len(selected_pdfs)} PDFs")
            elif selection_type == "last":
                selected_pdfs = [all_generated_pdfs[-1]]
                logger.info(f"Selecting last PDF: {selected_pdfs[0]['s3_key']}")
            elif selection_type == "last_n":
                # Get the last N PDFs
                selected_pdfs = all_generated_pdfs[-count:] if count <= len(all_generated_pdfs) else all_generated_pdfs
                logger.info(f"Selecting last {len(selected_pdfs)} PDFs")

            # Download PDFs from S3
            pdfs_to_send = []
            for pdf_info in selected_pdfs:
                try:
                    s3_response = s3_service.s3_client.get_object(
                        Bucket=s3_service.bucket_name,
                        Key=pdf_info['s3_key']
                    )
                    pdf_bytes = s3_response['Body'].read()

                    pdfs_to_send.append({
                        'bytes': pdf_bytes,
                        'filename': pdf_info['filename']
                    })

                    logger.info(f"Downloaded PDF: {pdf_info['filename']}")

                except Exception as e:
                    logger.warning(f"Failed to download PDF {pdf_info['s3_key']}: {str(e)}")
                    continue

            if not pdfs_to_send:
                return {
                    "success": True,
                    "data": {
                        "message": "I found the PDFs but couldn't retrieve them from storage. Please try again later.",
                        "sources": [],
                        "is_bulk_send_response": False
                    }
                }

            # Send PDFs via email
            try:
                await email_service.send_documents_email(
                    to_email=email_address,
                    subject=f"Your CaseBase Generated PDFs ({len(pdfs_to_send)} document(s))",
                    documents=pdfs_to_send
                )

                pdf_list = "\n".join([f"- {pdf['filename']}" for pdf in pdfs_to_send])

                return {
                    "success": True,
                    "data": {
                        "message": f"✅ Perfect! I've sent {len(pdfs_to_send)} generated PDF(s) to **{email_address}**.\n\nPDFs sent:\n{pdf_list}\n\nPlease check your inbox (and spam folder just in case).",
                        "sources": [],
                        "is_bulk_send_response": True,
                        "email_sent": True,
                        "email_address": email_address,
                        "pdfs_count": len(pdfs_to_send)
                    }
                }

            except Exception as e:
                logger.error(f"Failed to send bulk PDFs email: {str(e)}")
                return {
                    "success": True,
                    "data": {
                        "message": f"I found the PDFs but couldn't send the email. Error: {str(e)}",
                        "sources": [],
                        "is_bulk_send_response": False
                    }
                }

        # Check if user is requesting PDF creation using semantic detection
        pdf_intent = await chat_service.detect_pdf_creation_intent(request.message, history)

        # Special case: If previous message was PDF creation and user wants to email
        # Send the exact same PDF that was already created
        if previous_was_pdf_creation and email_intent["wants_email"] and previous_pdf_s3_key:
            logger.info(f"User wants to email the previously created PDF: {previous_pdf_s3_key}")

            email_address = email_intent["email_address"]

            # Check if email address is missing or invalid
            if not email_address or email_address == "" or not re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email_address):
                logger.info("Email address missing or invalid for PDF email request")
                return {
                    "success": True,
                    "data": {
                        "message": "I'd be happy to send you the PDF! What email address would you like me to send it to?",
                        "sources": [],
                        "is_pdf_response": False
                    }
                }

            # Check if email service is available
            if not email_service:
                return {
                    "success": True,
                    "data": {
                        "message": "I found the PDF, but email service is not configured. Please contact your administrator to enable email features.",
                        "sources": [],
                        "is_pdf_response": False
                    }
                }

            try:
                # Download the existing PDF from S3
                logger.info(f"Downloading PDF from S3: {previous_pdf_s3_key}")
                s3_response = s3_service.s3_client.get_object(
                    Bucket=s3_service.bucket_name,
                    Key=previous_pdf_s3_key
                )
                pdf_bytes = s3_response['Body'].read()

                # Extract filename from S3 key
                filename = previous_pdf_s3_key.split('/')[-1]

                # Send email with the exact PDF
                await email_service.send_pdf_email(
                    to_email=email_address,
                    subject="Your CaseBase Document Report",
                    pdf_bytes=pdf_bytes,
                    pdf_filename=filename
                )

                logger.info(f"Previously created PDF successfully emailed to {email_address}")

                return {
                    "success": True,
                    "data": {
                        "message": f"✅ Perfect! I've sent the PDF to **{email_address}**. Please check your inbox (and spam folder just in case).",
                        "sources": [],
                        "is_pdf_response": True,
                        "email_sent": True,
                        "email_address": email_address
                    }
                }

            except Exception as e:
                logger.error(f"Failed to email previously created PDF: {str(e)}")
                return {
                    "success": True,
                    "data": {
                        "message": f"I found the PDF but couldn't send it. Error: {str(e)}",
                        "sources": [],
                        "is_pdf_response": False
                    }
                }

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
                # Extract the actual content topic from the user's message
                logger.info(f"Extracting content topic from: {request.message}")

                # Build context from conversation history for topic extraction
                history_context = ""
                if history and len(history) > 0:
                    recent_history = history[-6:]  # Last 3 exchanges
                    history_text = "\n".join([
                        f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}"
                        for msg in recent_history
                    ])
                    history_context = f"\n\nCONVERSATION HISTORY:\n{history_text}\n"

                topic_extraction_prompt = f"""Extract the main topic/subject from this user request, removing any mention of PDF creation or emailing.
{history_context}
Current user request: "{request.message}"

Important: If the user uses pronouns like "it", "that", "this", look at the conversation history to understand what they're referring to.

Return ONLY the core topic that the user wants information about. Remove phrases like:
- "Create a PDF"
- "Generate a PDF"
- "Email to"
- Email addresses
- Any PDF or email related instructions

Examples:
- "Create a pdf on Alex and his fit for Casebase and email to alex@email.com" → "Alex and his fit for Casebase"
- "Generate a PDF about healthcare policies" → "healthcare policies"
- "Make a PDF comparing the two resumes" → "comparing the two resumes"
- Previous: "Tell me about Alex's skills", Current: "Create a PDF about that" → "Alex's skills"
- Previous: "What does the resume say?", Current: "Generate a PDF on it" → "the resume"

Your response (topic only):"""

                topic_response = await chat_service.client.chat.completions.create(
                    model=chat_service.model,
                    messages=[
                        {"role": "system", "content": "You extract topics from user requests. Return only the topic, nothing else."},
                        {"role": "user", "content": topic_extraction_prompt}
                    ],
                    temperature=0,
                    max_tokens=100
                )

                query = topic_response.choices[0].message.content.strip()
                logger.info(f"[PDF GEN] Extracted content topic: '{query}' from message: '{request.message}'")

                # Generate response to get the content from vector store
                logger.info(f"[PDF GEN] Retrieving content from vector store for: {query}")

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

                # Build context from retrieved chunks with source labels
                context_parts = []
                available_sources = {}  # Map: {filename -> simple_name}

                for result in results:
                    metadata = result.get("metadata", {})
                    chunk_text = metadata.get("chunk_text", "")
                    file_name = metadata.get("file_name", "")

                    if file_name:
                        # Create simple source name (e.g., "pdfs/Alex_Resume.pdf" -> "Alex_Resume")
                        simple_name = file_name.split('/')[-1].replace('.pdf', '')
                        available_sources[simple_name] = file_name

                        # Add labeled chunk
                        context_parts.append(f"[Source: {simple_name}]\n{chunk_text}")
                    else:
                        context_parts.append(chunk_text)

                context = "\n\n".join(context_parts)

                logger.info(f"Available source documents: {list(available_sources.keys())}")

                # Generate AI summary with explicit source tracking
                system_prompt = f"""You are an AI assistant. Provide a comprehensive summary and analysis based on the following document content.

DOCUMENT CONTENT:
{context}

Create a well-structured response that summarizes and explains the key information.

CRITICAL INSTRUCTION: After your summary, you MUST list ONLY the source documents you actually used and referenced in your response.
- Format: SOURCES_USED: source1, source2, source3
- Use the exact source names shown in [Source: ...] tags above
- ONLY include sources you directly referenced or cited in your summary
- If you didn't use a source, DO NOT include it in the list
- Be strict and honest about which sources you actually used"""

                response = await chat_service.client.chat.completions.create(
                    model=chat_service.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    temperature=0.3,  # Lower temperature for more consistent source tracking
                    max_tokens=2000
                )

                ai_response = response.choices[0].message.content
                logger.info(f"[PDF GEN] AI generated summary (first 200 chars): {ai_response[:200]}...")

                # Parse out the sources used and the actual summary
                if "SOURCES_USED:" in ai_response:
                    parts = ai_response.split("SOURCES_USED:")
                    ai_summary = parts[0].strip()
                    sources_line = parts[1].strip()

                    # Parse the source names (remove any trailing periods or extra whitespace)
                    used_source_names = [s.strip().rstrip('.').strip() for s in sources_line.split(',')]

                    # Filter out any empty strings
                    used_source_names = [name for name in used_source_names if name]

                    # Map back to full file paths
                    source_file_names = set()
                    for name in used_source_names:
                        if name in available_sources:
                            source_file_names.add(available_sources[name])
                        else:
                            logger.warning(f"AI reported source '{name}' not found in available sources")

                    logger.info(f"AI explicitly used these sources: {used_source_names}")
                    logger.info(f"Mapped to {len(source_file_names)} file(s): {source_file_names}")
                else:
                    # If AI didn't follow format, don't attach any source documents
                    ai_summary = ai_response
                    source_file_names = set()
                    logger.warning("AI didn't specify sources in the correct format, no source documents will be attached")

                # Extract display filenames from source file paths
                source_document_names = []
                if source_file_names:
                    for file_path in source_file_names:
                        # Extract just the filename from the S3 key
                        display_filename = file_path.split('/')[-1]
                        source_document_names.append(display_filename)
                    logger.info(f"Source documents to include in PDF: {source_document_names}")

                # Create PDF with the query, AI summary, and source document names
                logger.info(f"[PDF GEN] Generating PDF with prompt='{query}', summary length={len(ai_summary)}, sources={source_document_names}")
                pdf_bytes = pdf_generator.generate_from_prompt(
                    prompt=query,
                    response=ai_summary,
                    source_documents=source_document_names
                )
                logger.info(f"[PDF GEN] PDF generated successfully, size={len(pdf_bytes)} bytes")

                # Create descriptive filename from query topic
                # Sanitize query for filename (remove special chars, limit length)
                safe_topic = re.sub(r'[^\w\s-]', '', query)[:50]  # Remove special chars, max 50 chars
                safe_topic = re.sub(r'\s+', '_', safe_topic.strip())  # Replace spaces with underscores
                filename = f"{safe_topic}_content.pdf" if safe_topic else "document_content.pdf"

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
                    from datetime import datetime, timezone
                    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
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

                    download_url = f"{settings.backend_url}/api/pdfs/view/{s3_key}"

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
                from datetime import datetime, timezone
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                s3_key = f"generated_pdfs/{timestamp}_{filename}"
                logger.info(f"[PDF GEN] Creating PDF with timestamp={timestamp}, filename={filename}, s3_key={s3_key}, pdf_bytes size={len(pdf_bytes)}")

                # Ensure we're uploading fresh bytes (convert to bytes if needed)
                pdf_bytes_to_upload = bytes(pdf_bytes) if not isinstance(pdf_bytes, bytes) else pdf_bytes

                s3_service.s3_client.put_object(
                    Bucket=s3_service.bucket_name,
                    Key=s3_key,
                    Body=pdf_bytes_to_upload,
                    ContentType="application/pdf",
                    Metadata={
                        'generated_at': timestamp,
                        'type': pdf_intent["type"]
                    }
                )

                logger.info(f"[PDF GEN] PDF uploaded to S3: {s3_key}, size={len(pdf_bytes)} bytes")

                # Return download URL
                download_url = f"{settings.backend_url}/api/pdfs/view/{s3_key}"

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
