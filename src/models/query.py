"""Query-related data models."""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Citation:
    """Citation for a fact in a query response."""
    document_id: str
    document_name: str
    page_number: int
    clause_reference: str
    excerpt: str
    confidence_score: float
    
    def validate(self) -> bool:
        """Validate citation data."""
        if not self.document_id or not self.document_name:
            return False
        if self.page_number < 1:
            return False
        if not self.clause_reference or not self.excerpt:
            return False
        if not (0.0 <= self.confidence_score <= 1.0):
            return False
        return True


@dataclass
class QueryResult:
    """Result of a query operation."""
    answer: str
    citations: List[Citation]
    query_id: str
    processing_time_ms: int
    
    def validate(self) -> bool:
        """Validate query result."""
        if not self.answer or not self.query_id:
            return False
        if self.processing_time_ms < 0:
            return False
        if not all(c.validate() for c in self.citations):
            return False
        return True


@dataclass
class RetrievedChunk:
    """A document chunk retrieved from semantic search."""
    chunk_id: str
    document_id: str
    content: str
    relevance_score: float
    page_number: int
    section_reference: Optional[str]
    
    def validate(self) -> bool:
        """Validate retrieved chunk."""
        if not self.chunk_id or not self.document_id or not self.content:
            return False
        if not (0.0 <= self.relevance_score <= 1.0):
            return False
        if self.page_number < 1:
            return False
        return True
