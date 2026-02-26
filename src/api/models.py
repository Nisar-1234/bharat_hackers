"""API request and response models."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class TextQueryRequest(BaseModel):
    """Request model for text queries."""
    query: str = Field(..., min_length=1, description="User's question")
    language: str = Field(default="en", description="Target response language (en, hi, te, ta)")


class VoiceQueryRequest(BaseModel):
    """Request model for voice queries."""
    language: str = Field(..., description="Audio language (hi, te, ta, en)")


class CitationResponse(BaseModel):
    """Citation information in response."""
    document_id: str
    document_name: str
    page_number: int
    clause_reference: str
    excerpt: str
    confidence_score: float


class QueryResponse(BaseModel):
    """Response model for text queries."""
    answer: str
    citations: List[CitationResponse]
    processing_time_ms: int


class VoiceQueryResponse(BaseModel):
    """Response model for voice queries."""
    transcribed_text: str
    answer_text: str
    audio_url: str
    citations: List[CitationResponse]


class DocumentResponse(BaseModel):
    """Response model for document information."""
    document_id: str
    filename: str
    status: str
    upload_date: str
    chunk_count: Optional[int] = None
    file_size_bytes: Optional[int] = None


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    document_id: str
    filename: str
    status: str
    message: str


class ErrorResponse(BaseModel):
    """Error response model."""
    error: bool = True
    message: str
    error_type: str
