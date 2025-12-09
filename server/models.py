"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel
from typing import Optional, List


class ChatMessage(BaseModel):
    """Model for a chat message in conversation history."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Model for chat endpoint requests."""
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    file_filter: Optional[str] = None
    top_k: Optional[int] = 5


class PDFGenerateRequest(BaseModel):
    """Model for PDF generation requests."""
    prompt: str = None
    response: str = None
    conversation_history: Optional[List[ChatMessage]] = []
    title: Optional[str] = None
