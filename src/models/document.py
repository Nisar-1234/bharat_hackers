"""Document-related data models."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from .enums import DocumentStatus


@dataclass
class DocumentChunk:
    """Represents a chunk of a processed document."""
    chunk_id: str
    document_id: str
    content: str
    page_number: int
    section_reference: Optional[str]
    start_char: int
    end_char: int
    
    def validate(self) -> bool:
        """Validate chunk data."""
        if not self.content or len(self.content) == 0:
            return False
        if self.start_char < 0 or self.end_char <= self.start_char:
            return False
        if self.page_number < 1:
            return False
        return True


@dataclass
class DocumentMetadata:
    """Metadata for an uploaded document."""
    document_id: str
    filename: str
    s3_key: str
    upload_date: datetime
    status: DocumentStatus
    chunk_count: int
    file_size_bytes: int
    mime_type: str
    error_message: Optional[str] = None
    
    def validate(self) -> bool:
        """Validate document metadata."""
        if not self.filename or not self.s3_key:
            return False
        if self.file_size_bytes <= 0:
            return False
        if self.mime_type not in ['application/pdf', 'image/png', 'image/jpg', 'image/jpeg']:
            return False
        if self.status == DocumentStatus.COMPLETED and self.chunk_count <= 0:
            return False
        return True
