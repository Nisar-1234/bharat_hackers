"""FastAPI application."""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from .models import (
    TextQueryRequest, VoiceQueryRequest,
    QueryResponse, VoiceQueryResponse,
    DocumentResponse, DocumentUploadResponse,
    CitationResponse, ErrorResponse
)
from ..components.document_processor import DocumentProcessor
from ..components.query_engine import QueryEngine
from ..components.voice_interface import VoiceInterface
from ..database.dynamodb_client import DynamoDBClient
from ..models.enums import SupportedLanguage
from ..utils.error_handler import create_error_response


app = FastAPI(
    title="Jansahayak API",
    version="1.0.0",
    description="GenAI-powered citizen assistant for government schemes"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
document_processor = DocumentProcessor()
query_engine = QueryEngine()
voice_interface = VoiceInterface()
db = DynamoDBClient()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Jansahayak"}


@app.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document for processing.
    
    Accepts PDF and image files (PNG, JPG, JPEG).
    """
    try:
        # Read file content
        file_content = await file.read()
        
        # Upload document
        metadata = await document_processor.upload_document(
            file_content=file_content,
            filename=file.filename,
            mime_type=file.content_type
        )
        
        return DocumentUploadResponse(
            document_id=metadata.document_id,
            filename=metadata.filename,
            status=metadata.status.value,
            message="Document uploaded successfully. Processing will begin shortly."
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/documents", response_model=List[DocumentResponse])
async def list_documents(limit: int = 10, status: str = None):
    """List uploaded documents, optionally filtered by status."""
    documents = db.list_documents(status=status, limit=limit)
    return [
        DocumentResponse(
            document_id=doc.document_id,
            filename=doc.filename,
            status=doc.status.value,
            upload_date=doc.upload_date.isoformat(),
            chunk_count=doc.chunk_count,
            file_size_bytes=doc.file_size_bytes,
        )
        for doc in documents
    ]


@app.get("/documents/{document_id}/status", response_model=DocumentResponse)
async def get_document_status(document_id: str):
    """Get the processing status of a document."""
    try:
        metadata = await document_processor.get_document_status(document_id)
        
        return DocumentResponse(
            document_id=metadata.document_id,
            filename=metadata.filename,
            status=metadata.status.value,
            upload_date=metadata.upload_date.isoformat(),
            chunk_count=metadata.chunk_count,
            file_size_bytes=metadata.file_size_bytes
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="Document not found")


@app.post("/query/text", response_model=QueryResponse)
async def query_text(request: TextQueryRequest):
    """
    Process a text query against uploaded documents.
    
    Returns answer with citations.
    """
    try:
        # Process query
        result = await query_engine.query(
            query_text=request.query,
            language=request.language
        )
        
        # Convert citations to response model
        citations = [
            CitationResponse(
                document_id=c.document_id,
                document_name=c.document_name,
                page_number=c.page_number,
                clause_reference=c.clause_reference,
                excerpt=c.excerpt,
                confidence_score=c.confidence_score
            )
            for c in result.citations
        ]
        
        return QueryResponse(
            answer=result.answer,
            citations=citations,
            processing_time_ms=result.processing_time_ms
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query/voice", response_model=VoiceQueryResponse)
async def query_voice(
    audio: UploadFile = File(...),
    language: str = Form(...)
):
    """
    Process a voice query.
    
    Accepts audio file and returns transcription, answer, and synthesized audio.
    """
    try:
        # Read audio content
        audio_bytes = await audio.read()
        
        # Parse language
        lang_enum = SupportedLanguage(language)
        
        # Process voice query
        result = await voice_interface.process_voice_query(audio_bytes, lang_enum)
        
        # Convert citations to response model
        citations = [
            CitationResponse(
                document_id=c.document_id,
                document_name=c.document_name,
                page_number=c.page_number,
                clause_reference=c.clause_reference,
                excerpt=c.excerpt,
                confidence_score=c.confidence_score
            )
            for c in result.citations
        ]
        
        return VoiceQueryResponse(
            transcribed_text=result.transcribed_text,
            answer_text=result.answer_text,
            audio_url=result.audio_url,
            citations=citations
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return create_error_response(exc, context={"path": request.url.path})
