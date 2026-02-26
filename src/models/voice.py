"""Voice interface data models."""
from dataclasses import dataclass
from typing import List
from .enums import SupportedLanguage
from .query import Citation


@dataclass
class TranscriptionResult:
    """Result of audio transcription."""
    text: str
    language: SupportedLanguage
    confidence: float
    
    def validate(self) -> bool:
        """Validate transcription result."""
        if not self.text:
            return False
        if not (0.0 <= self.confidence <= 1.0):
            return False
        return True


@dataclass
class VoiceQueryResult:
    """Result of a voice query operation."""
    transcribed_text: str
    translated_query: str
    answer_text: str
    translated_answer: str
    audio_url: str
    citations: List[Citation]
    
    def validate(self) -> bool:
        """Validate voice query result."""
        if not all([self.transcribed_text, self.translated_query, 
                   self.answer_text, self.translated_answer, self.audio_url]):
            return False
        if not all(c.validate() for c in self.citations):
            return False
        return True
