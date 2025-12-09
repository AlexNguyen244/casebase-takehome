"""
Chat service for handling conversational AI with RAG integration.
Uses OpenAI's GPT models to generate responses based on retrieved document context.
"""

from typing import List, Dict, Optional
import logging
import re
from openai import AsyncOpenAI

from embedding_service import EmbeddingService
from pinecone_service import PineconeService

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling chat completions with RAG context."""

    def __init__(
        self,
        openai_api_key: str,
        embedding_service: EmbeddingService,
        pinecone_service: PineconeService,
        model: str = "gpt-4o-mini"
    ):
        """
        Initialize the chat service.

        Args:
            openai_api_key: OpenAI API key
            embedding_service: Service for generating embeddings
            pinecone_service: Service for vector storage
            model: OpenAI model to use (default: gpt-4o-mini)
        """
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.embedding_service = embedding_service
        self.pinecone_service = pinecone_service
        self.model = model

    async def chat_with_documents(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None,
        file_filter: Optional[str] = None,
        top_k: int = 5
    ) -> Dict:
        """
        Generate a chat response using RAG.

        Args:
            message: User's message/question
            conversation_history: Previous messages in the conversation
            file_filter: Optional file name to filter results
            top_k: Number of document chunks to retrieve

        Returns:
            Dictionary with response and metadata
        """
        try:
            logger.info(f"Processing chat message: {message[:50]}...")

            # Step 1: Generate embedding for the query
            query_embedding = await self.embedding_service.generate_embedding(message)

            # Step 2: Retrieve relevant chunks from Pinecone
            metadata_filter = {"file_name": file_filter} if file_filter else None

            results = await self.pinecone_service.query(
                query_embedding=query_embedding,
                top_k=top_k,
                filter=metadata_filter
            )

            logger.info(f"Retrieved {len(results)} relevant chunks")

            # Step 3: Build context from retrieved chunks
            if not results:
                # No relevant documents found
                context = "No relevant documents found in the knowledge base."
                sources = []
            else:
                # Format retrieved chunks into context
                context_parts = []
                sources = []

                for result in results:
                    metadata = result.get("metadata", {})
                    chunk_text = metadata.get("chunk_text", "")
                    file_name = metadata.get("file_name", "unknown")
                    score = result.get("score", 0)

                    # Just add the content without document labels
                    context_parts.append(chunk_text)

                    sources.append({
                        "file_name": file_name,
                        "chunk_id": metadata.get("chunk_id"),
                        "relevance_score": score
                    })

                # Join chunks with clear separation
                context = "\n\n".join(context_parts)

            # Step 4: Build system prompt with RAG context
            system_prompt = self._build_system_prompt(context)

            # Step 5: Build conversation messages
            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)

            # Add current user message
            messages.append({"role": "user", "content": message})

            # Step 6: Generate response using OpenAI
            logger.info(f"Calling OpenAI {self.model}...")

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )

            assistant_message = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }

            logger.info(f"Response generated. Tokens used: {usage['total_tokens']}")

            return {
                "message": assistant_message,
                "sources": sources,
                "retrieved_chunks": len(results),
                "usage": usage,
                "model": self.model
            }

        except Exception as e:
            logger.error(f"Chat service error: {str(e)}")
            raise Exception(f"Chat processing failed: {str(e)}")

    def _build_system_prompt(self, context: str) -> str:
        """
        Build the system prompt with RAG context.

        Args:
            context: Retrieved document context

        Returns:
            System prompt string
        """
        return f"""You are Casey, an intelligent AI assistant for CaseBase, a community supervision platform. Your role is to help users understand and extract information from their uploaded PDF documents.

CAPABILITIES:
- Answer questions about uploaded documents
- Create PDF reports from conversations or document content
- Email PDFs to users when they request it

INSTRUCTIONS:
1. Answer questions based ONLY on the provided context below
2. If the context doesn't contain relevant information, politely say you don't have that information in the documents
3. Be concise, accurate, and helpful
4. Synthesize information naturally without referring to "Document 1", "Document 2", or numbered sources
5. Present information as if you're directly answering from the documents
6. Never make up or infer information that isn't in the provided context
7. When users ask to create PDFs or email PDFs, confidently tell them you can do that

IMPORTANT: You CAN create and email PDFs. When users request PDF creation or emailing, respond positively (e.g., "I'll create that PDF for you" or "I can email that to you"). The system will automatically detect and handle PDF/email requests.

CONTEXT FROM DOCUMENTS:
{context}

Remember: Only use information from the context above to answer questions. Provide direct, natural answers without mentioning document numbers or labels."""

    async def detect_email_intent(self, message: str, conversation_history: Optional[List[Dict]] = None, remembered_email: Optional[str] = None) -> Dict:
        """
        Detect if the user wants to email a PDF and extract the email address.

        Args:
            message: User's message
            conversation_history: Previous messages in the conversation
            remembered_email: Previously used email address from conversation history

        Returns:
            Dictionary with 'wants_email' bool and 'email_address' string (or None)
        """
        try:
            # Build context from conversation history
            context = ""
            if conversation_history and len(conversation_history) > 0:
                recent_history = conversation_history[-6:]  # Last 3 exchanges
                history_text = "\n".join([
                    f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}"
                    for msg in recent_history
                ])
                context = f"\n\nCONVERSATION HISTORY:\n{history_text}\n"

            # Add remembered email to context if available
            remembered_email_context = ""
            if remembered_email:
                remembered_email_context = f"\n\nREMEMBERED EMAIL: {remembered_email}\nIf the user says 'email me' or 'send to me' without providing an email, use this remembered email.\n"

            # Use LLM to detect email intent and extract email address
            classifier_prompt = f"""You are an email intent detector.
{context}{remembered_email_context}
Analyze this user message and determine:
1. Does the user want to EMAIL a PDF (not just create/download it)?
2. If yes, what email address do they want it sent to?
3. Use the conversation history for context if the user says "it" or "that"
4. If user says "email me" or "send to me" without providing an email, use the REMEMBERED EMAIL if available
5. IMPORTANT: If no email is provided and no remembered email exists, respond with "EMAIL: NONE" - do NOT invent an email address

Current user message: "{message}"

Respond in this EXACT format:
- If they want to email AND have an email: "EMAIL: their@email.com"
- If they want to email BUT no email provided/remembered: "EMAIL: NONE"
- If they don't want to email: "NO_EMAIL"

Examples:
- "Send the PDF to john@example.com" → EMAIL: john@example.com
- "Email this to alex@test.com" → EMAIL: alex@test.com
- "Create a PDF and email it to me at user@domain.org" → EMAIL: user@domain.org
- Previous: "Create a PDF about Alex", Current: "Send it to me at test@email.com" → EMAIL: test@email.com
- Remembered email: "alex@test.com", Current: "Email me that" → EMAIL: alex@test.com
- Remembered email: "alex@test.com", Current: "Send it to me" → EMAIL: alex@test.com
- No remembered email, Current: "Send this to my email" → EMAIL: NONE
- No remembered email, Current: "Email me this" → EMAIL: NONE
- "Create a PDF of our conversation" → NO_EMAIL
- "Generate a PDF" → NO_EMAIL

Your response:"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an email intent detector. Extract email addresses accurately. Use conversation context and remembered email when appropriate."},
                    {"role": "user", "content": classifier_prompt}
                ],
                temperature=0,
                max_tokens=50
            )

            result = response.choices[0].message.content.strip()
            logger.info(f"Email intent detection result: {result}")

            # Parse the response
            if result.startswith("EMAIL:"):
                email_address = result.replace("EMAIL:", "").strip()

                # Check if LLM explicitly said no email was provided
                if email_address.upper() in ["NONE", "NULL", "N/A", ""]:
                    logger.info("LLM detected email intent but no email address was provided")
                    return {
                        "wants_email": True,
                        "email_address": None
                    }

                # Validate that it's an actual email address, not a placeholder or generic text
                # Check if it's a real email format
                if not re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email_address):
                    # Not a valid email format - treat as no email
                    logger.warning(f"Invalid email format detected: '{email_address}' - treating as no email provided")
                    return {
                        "wants_email": True,
                        "email_address": None
                    }

                # Check for placeholder emails that shouldn't be used
                placeholder_patterns = [
                    "example",
                    "placeholder",
                    "your@",
                    "user@",
                    "my email",
                    "my@email"
                ]
                email_lower = email_address.lower()
                for pattern in placeholder_patterns:
                    if pattern in email_lower:
                        logger.warning(f"Placeholder email pattern detected: '{email_address}' - treating as no email provided")
                        return {
                            "wants_email": True,
                            "email_address": None
                        }

                return {
                    "wants_email": True,
                    "email_address": email_address
                }
            else:
                return {
                    "wants_email": False,
                    "email_address": None
                }

        except Exception as e:
            logger.error(f"Error in email intent detection: {str(e)}")
            return {"wants_email": False, "email_address": None}

    async def detect_pdf_creation_intent(self, message: str, conversation_history: Optional[List[Dict]] = None) -> Dict:
        """
        Detect if the user is requesting PDF creation using an LLM intent classifier.

        Args:
            message: User's message
            conversation_history: Previous messages in the conversation

        Returns:
            Dictionary with 'is_pdf_request' bool and 'type' ('history', 'vector_content', or None)
        """
        try:
            # Build context from conversation history
            context = ""
            if conversation_history and len(conversation_history) > 0:
                recent_history = conversation_history[-6:]  # Last 3 exchanges
                history_text = "\n".join([
                    f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}"
                    for msg in recent_history
                ])
                context = f"\n\nCONVERSATION HISTORY:\n{history_text}\n"

            # Use LLM as an intent classifier
            classifier_prompt = f"""You are an intent classifier for a document chatbot system.
{context}
Analyze the user's message and determine their intent:
- Use conversation history for context if the user says "it", "that", or refers to something previously mentioned

Current user message: "{message}"

IMPORTANT DISTINCTION:
- PDF creation: User explicitly asks to CREATE, GENERATE, or MAKE a PDF document
- Send documents: User asks to FIND, SEND, or EMAIL existing documents/files (NOT creating a new PDF)
- Chat: User asks questions or has normal conversation

Respond with ONLY ONE of these three options:
- "history" - if the user wants to CREATE a PDF of the conversation/chat history
- "vector_content" - if the user wants to CREATE a NEW PDF from document content
- "chat" - if the user wants to have a normal conversation OR send existing documents (NOT create PDF)

Examples:
- "Create a PDF of our conversation" → history
- "Generate a PDF from the documents about healthcare" → vector_content
- "Make a PDF summary about AI" → vector_content
- "What companies are mentioned?" → chat
- "Export this chat to PDF" → history
- Previous: "Tell me about Alex's skills", Current: "Create a PDF about that" → vector_content
- Previous: "What does the document say?", Current: "Generate a PDF of it" → vector_content
- "Find all documents related to Alex and send me those" → chat (sending existing docs, not creating PDF)
- "Send me the documents about healthcare" → chat (sending existing docs, not creating PDF)
- "Email me all files about the project" → chat (sending existing docs, not creating PDF)
- "Tell me about the project" → chat

Answer with only one word: history, vector_content, or chat."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise intent classifier. Respond with only one word. Use conversation context."},
                    {"role": "user", "content": classifier_prompt}
                ],
                temperature=0,  # Use 0 for deterministic classification
                max_tokens=10
            )

            intent = response.choices[0].message.content.strip().lower()

            logger.info(f"LLM intent classifier result: {intent}")

            # Parse the LLM response
            if intent == "history":
                return {
                    "is_pdf_request": True,
                    "type": "history"
                }
            elif intent == "vector_content":
                return {
                    "is_pdf_request": True,
                    "type": "vector_content"
                }
            else:
                # Default to chat for any other response
                return {
                    "is_pdf_request": False,
                    "type": None
                }

        except Exception as e:
            logger.error(f"Error in PDF intent detection: {str(e)}")
            # Fail safe: if classifier fails, treat as normal chat
            return {"is_pdf_request": False, "type": None}

    async def detect_send_documents_intent(self, message: str, conversation_history: Optional[List[Dict]] = None, remembered_email: Optional[str] = None) -> Dict:
        """
        Detect if the user wants to send/email existing documents (not create a PDF).

        Args:
            message: User's message
            conversation_history: Previous messages in the conversation
            remembered_email: Previously used email address from conversation history

        Returns:
            Dictionary with 'wants_send_docs' bool, 'email_address' string, and 'topic' string
        """
        try:
            # Build context from conversation history
            context = ""
            if conversation_history and len(conversation_history) > 0:
                recent_history = conversation_history[-6:]  # Last 3 exchanges
                history_text = "\n".join([
                    f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}"
                    for msg in recent_history
                ])
                context = f"\n\nCONVERSATION HISTORY:\n{history_text}\n"

            # Add remembered email to context if available
            remembered_email_context = ""
            if remembered_email:
                remembered_email_context = f"\n\nREMEMBERED EMAIL: {remembered_email}\nIf the user says 'email me' or 'send to me' without providing an email, use this remembered email.\n"

            classifier_prompt = f"""You are an intent detector for a document management system.
{context}{remembered_email_context}
Analyze this user message and determine:
1. Does the user want to SEND/EMAIL existing documents/files (not create a new PDF)?
2. If yes, what email address? Use REMEMBERED EMAIL if user says "email me" without providing one
3. What topic/subject are they asking about? Use conversation history if they say "it", "that", or "them"

Current user message: "{message}"

IMPORTANT: Keywords that indicate sending existing documents:
- "Find documents and send"
- "Send me documents/files"
- "Email me documents/files"
- "Send me all documents about X"
- "Send those/them to me"

NOT for PDF creation requests (those use "create", "generate", "make" a PDF)

Respond in this EXACT format:
- If they want to send existing documents: "SEND_DOCS|email@example.com|topic description"
- If they don't want to send documents: "NO_SEND"

Examples:
- "Send me all documents relating to CaseBase to alex@email.com" → SEND_DOCS|alex@email.com|CaseBase
- "Email me documents about the resumes to john@test.com" → SEND_DOCS|john@test.com|resumes
- "Can you send the job description files to me at user@domain.org" → SEND_DOCS|user@domain.org|job description
- "Find all documents related to Alex and send me those too" → SEND_DOCS|[remembered_email]|Alex
- "Send me the documents about healthcare" → SEND_DOCS|[remembered_email]|healthcare
- Previous: "Tell me about healthcare docs", Current: "Send them to alex@email.com" → SEND_DOCS|alex@email.com|healthcare
- Remembered email: "alex@test.com", Current: "Find documents about Alex and email me them" → SEND_DOCS|alex@test.com|Alex
- Remembered email: "john@test.com", Current: "Send me documents about healthcare" → SEND_DOCS|john@test.com|healthcare
- "Create a PDF about Alex" → NO_SEND (this is PDF creation, not sending existing docs)
- "Make a PDF summary" → NO_SEND (this is PDF creation, not sending existing docs)
- "What documents do you have?" → NO_SEND (just asking, not requesting to send)

Your response:"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an intent detector. Extract email addresses and topics accurately. Use conversation context and remembered email when appropriate."},
                    {"role": "user", "content": classifier_prompt}
                ],
                temperature=0,
                max_tokens=100
            )

            result = response.choices[0].message.content.strip()
            logger.info(f"Send documents intent detection result: {result}")

            # Parse the response
            if result.startswith("SEND_DOCS|"):
                parts = result.replace("SEND_DOCS|", "").split("|")
                if len(parts) >= 2:
                    email_address = parts[0].strip()
                    topic = parts[1].strip() if len(parts) > 1 else ""

                    # Check if email_address is a placeholder (not a real email)
                    if email_address in ["[remembered_email]", "[email]", "REMEMBERED_EMAIL", "email"]:
                        # Use the remembered email if available, otherwise None
                        email_address = remembered_email if remembered_email else None

                    return {
                        "wants_send_docs": True,
                        "email_address": email_address,
                        "topic": topic
                    }

            return {
                "wants_send_docs": False,
                "email_address": None,
                "topic": None
            }

        except Exception as e:
            logger.error(f"Error in send documents intent detection: {str(e)}")
            return {"wants_send_docs": False, "email_address": None, "topic": None}

    async def detect_bulk_pdf_send_intent(self, message: str, conversation_history: Optional[List[Dict]] = None, remembered_email: Optional[str] = None) -> Dict:
        """
        Detect if the user wants to send multiple generated PDFs via email.

        Args:
            message: User's message
            conversation_history: Previous messages in the conversation
            remembered_email: Previously used email address from conversation history

        Returns:
            Dictionary with:
            - 'wants_bulk_send' bool: Whether user wants to send multiple PDFs
            - 'email_address' string: Email address to send to
            - 'selection_type' string: 'all', 'last_n', 'last'
            - 'count' int: Number of PDFs to send (for 'last_n')
        """
        try:
            # Build context from conversation history
            context = ""
            if conversation_history and len(conversation_history) > 0:
                recent_history = conversation_history[-10:]  # Last 5 exchanges
                history_text = "\n".join([
                    f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}"
                    for msg in recent_history
                ])
                context = f"\n\nCONVERSATION HISTORY:\n{history_text}\n"

            # Add remembered email to context if available
            remembered_email_context = ""
            if remembered_email:
                remembered_email_context = f"\n\nREMEMBERED EMAIL: {remembered_email}\nIf the user says 'email me' or 'send to me' without providing an email, use this remembered email.\n"

            classifier_prompt = f"""You are an intent detector for a document management system that tracks generated PDFs.
{context}{remembered_email_context}
Analyze this user message and determine:
1. Does the user want to SEND/EMAIL previously generated PDFs from this conversation?
2. If yes, which PDFs do they want? (all, last one, last N)
3. What email address? Use REMEMBERED EMAIL if user says "email me" without providing one

Current user message: "{message}"

IMPORTANT: This is specifically for sending GENERATED PDFs from the conversation, not creating new ones or sending existing documents.

Keywords that indicate bulk PDF sending:
- "Send all PDFs"
- "Email the last 3 PDFs"
- "Send me all the reports"
- "Email the PDFs we created"
- "Send those PDFs"
- "Email all generated PDFs"

Respond in this EXACT format:
- If they want to send all PDFs: "BULK_SEND|all|email@example.com"
- If they want the last N PDFs: "BULK_SEND|last_n|N|email@example.com" (where N is a number)
- If they want just the last PDF: "BULK_SEND|last|email@example.com"
- If they don't want to send PDFs: "NO_BULK_SEND"

Examples:
- "Send all the PDFs to alex@email.com" → BULK_SEND|all|alex@email.com
- "Email me the last 3 PDFs" (remembered: john@test.com) → BULK_SEND|last_n|3|john@test.com
- "Send the last PDF to user@domain.org" → BULK_SEND|last|user@domain.org
- "Email all generated reports to me" (remembered: alex@test.com) → BULK_SEND|all|alex@test.com
- "Send me all PDFs we created" (remembered: john@test.com) → BULK_SEND|all|john@test.com
- "Email the last 5 reports to alex@email.com" → BULK_SEND|last_n|5|alex@email.com
- Previous: "Created 3 PDFs", Current: "Send them all to me" (remembered: user@test.com) → BULK_SEND|all|user@test.com
- Previous: "Here are your PDFs", Current: "Email the last 2 to alex@email.com" → BULK_SEND|last_n|2|alex@email.com
- "Create a new PDF" → NO_BULK_SEND (creating, not sending)
- "What PDFs do we have?" → NO_BULK_SEND (asking, not sending)

Your response:"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an intent detector. Extract email addresses and PDF selection criteria accurately. Use conversation context and remembered email when appropriate."},
                    {"role": "user", "content": classifier_prompt}
                ],
                temperature=0,
                max_tokens=100
            )

            result = response.choices[0].message.content.strip()
            logger.info(f"Bulk PDF send intent detection result: {result}")

            # Parse the response
            if result.startswith("BULK_SEND|"):
                parts = result.replace("BULK_SEND|", "").split("|")

                if len(parts) >= 2:
                    selection_type = parts[0].strip()

                    # Handle different selection types
                    if selection_type == "last_n" and len(parts) >= 3:
                        count = int(parts[1].strip())
                        email_address = parts[2].strip()

                        # Check if email_address is a placeholder
                        if email_address in ["[remembered_email]", "[email]", "REMEMBERED_EMAIL", "email"]:
                            email_address = remembered_email if remembered_email else None

                        return {
                            "wants_bulk_send": True,
                            "email_address": email_address,
                            "selection_type": "last_n",
                            "count": count
                        }
                    elif selection_type == "all":
                        email_address = parts[1].strip()

                        # Check if email_address is a placeholder
                        if email_address in ["[remembered_email]", "[email]", "REMEMBERED_EMAIL", "email"]:
                            email_address = remembered_email if remembered_email else None

                        return {
                            "wants_bulk_send": True,
                            "email_address": email_address,
                            "selection_type": "all",
                            "count": None
                        }
                    elif selection_type == "last":
                        email_address = parts[1].strip()

                        # Check if email_address is a placeholder
                        if email_address in ["[remembered_email]", "[email]", "REMEMBERED_EMAIL", "email"]:
                            email_address = remembered_email if remembered_email else None

                        return {
                            "wants_bulk_send": True,
                            "email_address": email_address,
                            "selection_type": "last",
                            "count": 1
                        }

            return {
                "wants_bulk_send": False,
                "email_address": None,
                "selection_type": None,
                "count": None
            }

        except Exception as e:
            logger.error(f"Error in bulk PDF send intent detection: {str(e)}")
            return {
                "wants_bulk_send": False,
                "email_address": None,
                "selection_type": None,
                "count": None
            }

    async def get_chat_completion_stream(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None,
        file_filter: Optional[str] = None,
        top_k: int = 5
    ):
        """
        Generate a streaming chat response (for future implementation).

        Args:
            message: User's message/question
            conversation_history: Previous messages in the conversation
            file_filter: Optional file name to filter results
            top_k: Number of document chunks to retrieve

        Yields:
            Chunks of the response as they're generated
        """
        # This can be implemented later for streaming responses
        pass
