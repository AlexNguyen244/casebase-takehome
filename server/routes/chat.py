"""
Chat and RAG endpoints for AI-powered document interaction.

This module contains:
- RAG query endpoint for semantic document search
- Chat endpoint with multi-intent detection (chat, PDF creation, email, bulk send, source docs)
- PDF generation endpoint
"""

import logging
import io
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from models import ChatRequest, PDFGenerateRequest
from utils.helpers import (
    extract_most_recent_email_from_history,
    extract_generated_pdfs_from_history,
    get_source_documents_for_pdf
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Chat & RAG"])


def init_chat_routes(
    rag_service,
    chat_service,
    s3_service,
    pdf_generator,
    email_service,
    embedding_service,
    pinecone_service,
    settings
):
    """
    Initialize chat routes with service dependencies.

    Args:
        rag_service: RAG service instance
        chat_service: Chat service instance
        s3_service: S3 service instance
        pdf_generator: PDF generator instance
        email_service: Email service instance (optional)
        embedding_service: Embedding service instance
        pinecone_service: Pinecone service instance
        settings: Application settings
    """

    @router.post("/rag/query")
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
    @router.post("/chat")
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
    
            # Check if there are recently generated PDFs in the conversation (last 4 messages)
            recent_history = history[-8:] if len(history) > 8 else history  # Last 4 exchanges
            all_generated_pdfs = extract_generated_pdfs_from_history(history)
            has_recent_pdfs = len(all_generated_pdfs) > 0

            # If there are generated PDFs AND user mentions sending, prioritize bulk_send_intent
            # This prevents "send those" from incorrectly triggering document search
            send_keywords = ['send', 'email', 'those', 'them', 'these', 'the pdfs', 'the pdf']
            user_wants_to_send = any(keyword in request.message.lower() for keyword in send_keywords)

            # Check if user is asking for source documents specifically
            source_keywords = ['source', 'sources', 'source documents', 'original documents', 'source files']
            user_wants_sources = any(keyword in request.message.lower() for keyword in source_keywords)

            # Initialize both intents
            bulk_send_intent = None
            send_docs_intent = {"wants_send_docs": False}

            # PRIORITY CHECK: If there are recent PDFs and user wants to send something,
            # check bulk_send_intent FIRST before checking send_docs_intent
            # EXCEPTION: If user explicitly mentions "source", skip this priority check
            if has_recent_pdfs and user_wants_to_send and not user_wants_sources:
                logger.info(f"Found {len(all_generated_pdfs)} generated PDFs. Checking bulk_send_intent first.")
                bulk_send_intent = await chat_service.detect_bulk_pdf_send_intent(request.message, history, remembered_email)

            # Only check send_docs_intent if:
            # 1. bulk_send_intent didn't trigger, AND
            # 2. User is NOT asking for sources (to prevent "send source" from triggering vector search)
            # Skip this check if BOTH: (1) previous was PDF creation AND (2) user wants to email
            skip_send_docs_check = (previous_was_pdf_creation and email_intent["wants_email"]) or user_wants_sources

            if not skip_send_docs_check and (not bulk_send_intent or not bulk_send_intent.get("wants_bulk_send")):
                send_docs_intent = await chat_service.detect_send_documents_intent(request.message, history, remembered_email)
    
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
    
                # Check if any documents were identified as relevant
                if not document_files:
                    return {
                        "success": True,
                        "data": {
                            "message": f"I searched through the uploaded documents but couldn't find any that are specifically about '{topic}'. Please try a different search term or upload relevant documents.",
                            "sources": [],
                            "is_send_docs_response": False
                        }
                    }

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
    
            # Check if user wants to send source documents for generated PDFs
            # Only check this if bulk_send_intent hasn't already been checked/triggered
            # This prevents "send those" from triggering source docs when user wants the generated PDFs
            send_source_docs_intent = {"wants_send_sources": False}

            # Skip source docs check if we already have a bulk send intent
            if not (bulk_send_intent and bulk_send_intent.get("wants_bulk_send")):
                send_source_docs_intent = await chat_service.detect_send_source_docs_intent(request.message, history, remembered_email)

            if send_source_docs_intent["wants_send_sources"]:
                logger.info(f"Send source docs request detected. Scope: {send_source_docs_intent['scope']}, Count: {send_source_docs_intent['count']}, Email: {send_source_docs_intent['email_address']}")
    
                email_address = send_source_docs_intent["email_address"]
    
                # Check if email address is missing
                if not email_address or email_address == "":
                    logger.info("Email address missing in send source docs request")
                    return {
                        "success": True,
                        "data": {
                            "message": "I'd be happy to send you the source documents! What email address would you like me to send them to?",
                            "sources": [],
                            "is_send_source_docs_response": False
                        }
                    }
    
                # Check if email service is available
                if not email_service:
                    return {
                        "success": True,
                        "data": {
                            "message": "Email service is not configured. Please contact your administrator to enable email features.",
                            "sources": [],
                            "is_send_source_docs_response": False
                        }
                    }
    
                # Extract generated PDFs from conversation history
                all_generated_pdfs = extract_generated_pdfs_from_history(history)
    
                if not all_generated_pdfs or len(all_generated_pdfs) == 0:
                    return {
                        "success": True,
                        "data": {
                            "message": "I couldn't find any generated PDFs in our conversation history to get sources from.",
                            "sources": [],
                            "is_send_source_docs_response": False
                        }
                    }
    
                # Select PDFs based on scope
                selected_pdfs = []
                scope = send_source_docs_intent["scope"]
                count = send_source_docs_intent["count"]
    
                if scope == "all":
                    selected_pdfs = all_generated_pdfs
                    logger.info(f"Selecting source docs from all {len(selected_pdfs)} PDFs")
                elif scope in ["those", "last_pdf"]:
                    # "those" refers to recently mentioned PDFs (last 2 or 3), "last_pdf" is just the last one
                    if scope == "last_pdf":
                        selected_pdfs = [all_generated_pdfs[-1]]
                    else:
                        # For "those", get the last 2-3 PDFs (or all if less)
                        selected_pdfs = all_generated_pdfs[-3:] if len(all_generated_pdfs) >= 3 else all_generated_pdfs
                    logger.info(f"Selecting source docs from {len(selected_pdfs)} PDF(s) (scope: {scope})")
                elif scope == "last_n_pdfs":
                    # Get the last N PDFs
                    selected_pdfs = all_generated_pdfs[-count:] if count <= len(all_generated_pdfs) else all_generated_pdfs
                    logger.info(f"Selecting source docs from last {len(selected_pdfs)} PDFs")
    
                # Collect all source documents from selected PDFs
                all_source_docs = set()
                for pdf_info in selected_pdfs:
                    source_docs = get_source_documents_for_pdf(s3_service, pdf_info['s3_key'])
                    all_source_docs.update(source_docs)
    
                if not all_source_docs:
                    return {
                        "success": True,
                        "data": {
                            "message": "I couldn't find any source documents for the selected PDFs. The PDFs may have been generated from conversation history rather than document content.",
                            "sources": [],
                            "is_send_source_docs_response": False
                        }
                    }
    
                # Download source documents from S3
                source_docs_to_send = []
                for source_doc_key in all_source_docs:
                    try:
                        s3_response = s3_service.s3_client.get_object(
                            Bucket=s3_service.bucket_name,
                            Key=source_doc_key
                        )
                        doc_bytes = s3_response['Body'].read()
    
                        # Extract filename from S3 key
                        display_filename = source_doc_key.split('/')[-1]
    
                        source_docs_to_send.append({
                            'bytes': doc_bytes,
                            'filename': display_filename
                        })
    
                        logger.info(f"Downloaded source document: {display_filename}")
    
                    except Exception as e:
                        logger.warning(f"Failed to download source document {source_doc_key}: {str(e)}")
                        continue
    
                if not source_docs_to_send:
                    return {
                        "success": True,
                        "data": {
                            "message": "I found source documents but couldn't retrieve them from storage. Please try again later.",
                            "sources": [],
                            "is_send_source_docs_response": False
                        }
                    }
    
                # Send source documents via email
                try:
                    await email_service.send_documents_email(
                        to_email=email_address,
                        subject=f"Source Documents from CaseBase ({len(source_docs_to_send)} document(s))",
                        documents=source_docs_to_send
                    )
    
                    doc_list = "\n".join([f"- {doc['filename']}" for doc in source_docs_to_send])
    
                    return {
                        "success": True,
                        "data": {
                            "message": f"✅ Perfect! I've sent {len(source_docs_to_send)} source document(s) to **{email_address}**.\n\nSource documents sent:\n{doc_list}\n\nPlease check your inbox (and spam folder just in case).",
                            "sources": [],
                            "is_send_source_docs_response": True,
                            "email_sent": True,
                            "email_address": email_address,
                            "documents_count": len(source_docs_to_send)
                        }
                    }
    
                except Exception as e:
                    logger.error(f"Failed to send source documents email: {str(e)}")
                    return {
                        "success": True,
                        "data": {
                            "message": f"I found the source documents but couldn't send the email. Error: {str(e)}",
                            "sources": [],
                            "is_send_source_docs_response": False
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
    
                # Initialize source_file_names for tracking source documents
                source_file_names = set()
    
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
    
                        # Store source documents in metadata (comma-separated)
                        source_docs_str = ",".join(source_file_names) if source_file_names else ""
    
                        s3_service.s3_client.put_object(
                            Bucket=s3_service.bucket_name,
                            Key=s3_key,
                            Body=pdf_bytes,
                            ContentType="application/pdf",
                            Metadata={
                                'generated_at': timestamp,
                                'type': pdf_intent["type"],
                                'source_documents': source_docs_str
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
    
                    # Store source documents in metadata (comma-separated)
                    source_docs_str = ",".join(source_file_names) if source_file_names else ""
    
                    s3_service.s3_client.put_object(
                        Bucket=s3_service.bucket_name,
                        Key=s3_key,
                        Body=pdf_bytes_to_upload,
                        ContentType="application/pdf",
                        Metadata={
                            'generated_at': timestamp,
                            'type': pdf_intent["type"],
                            'source_documents': source_docs_str
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
    @router.post("/generate-pdf")
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
    return router
