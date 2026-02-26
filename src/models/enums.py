"""Enumerations for Jansahayak."""
from enum import Enum


class DocumentStatus(Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SupportedLanguage(Enum):
    """Supported languages for voice interface."""
    HINDI = "hi"
    TELUGU = "te"
    TAMIL = "ta"
    ENGLISH = "en"
