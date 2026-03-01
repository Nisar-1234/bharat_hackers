"""Unit tests for chunking and citation logic.

These tests cover pure functions that require no AWS credentials.
Run with: pytest tests/test_unit.py -m unit
"""
import pytest
from unittest.mock import patch

from src.models.query import RetrievedChunk


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def processor():
    with patch('boto3.client'), patch('boto3.resource'):
        from src.components.document_processor import DocumentProcessor
        yield DocumentProcessor()


@pytest.fixture
def engine():
    with patch('boto3.client'), patch('boto3.resource'):
        from src.components.query_engine import QueryEngine
        yield QueryEngine()


@pytest.fixture
def sample_chunks():
    return [
        RetrievedChunk(
            chunk_id='chunk-1',
            document_id='doc-abc',
            content='PM-KISAN provides income support of Rs 6000 per year to eligible farmers.',
            relevance_score=0.92,
            page_number=2,
            section_reference='Section 3',
        ),
        RetrievedChunk(
            chunk_id='chunk-2',
            document_id='doc-def',
            content='Eligibility: small and marginal farmers with less than 2 hectares of land.',
            relevance_score=0.85,
            page_number=5,
            section_reference='Section 4',
        ),
    ]


# ── chunk_text ────────────────────────────────────────────────────────────────

class TestChunkText:

    @pytest.mark.unit
    def test_empty_text_returns_empty_list(self, processor):
        assert processor.chunk_text('', 'doc-1') == []

    @pytest.mark.unit
    def test_short_text_produces_single_chunk(self, processor):
        text = 'Short document content under 1000 characters.'
        chunks = processor.chunk_text(text, 'doc-1')
        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].document_id == 'doc-1'
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == len(text)

    @pytest.mark.unit
    def test_long_text_produces_multiple_chunks(self, processor):
        chunks = processor.chunk_text('A' * 2500, 'doc-1')
        assert len(chunks) > 1

    @pytest.mark.unit
    def test_last_chunk_reaches_end_of_text(self, processor):
        text = 'x' * 3200
        chunks = processor.chunk_text(text, 'doc-1')
        assert chunks[-1].end_char == len(text)

    @pytest.mark.unit
    def test_consecutive_chunks_have_200_char_overlap(self, processor):
        chunks = processor.chunk_text('B' * 2500, 'doc-1')
        for i in range(len(chunks) - 1):
            overlap = chunks[i].end_char - chunks[i + 1].start_char
            assert overlap == 200

    @pytest.mark.unit
    def test_no_chunk_exceeds_1000_chars(self, processor):
        chunks = processor.chunk_text('C' * 5000, 'doc-1')
        for chunk in chunks:
            assert len(chunk.content) <= 1000

    @pytest.mark.unit
    def test_chunk_ids_are_unique(self, processor):
        chunks = processor.chunk_text('D' * 3000, 'doc-1')
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    @pytest.mark.unit
    def test_chunk_content_matches_source_slice(self, processor):
        text = 'E' * 1500
        chunks = processor.chunk_text(text, 'doc-1')
        for chunk in chunks:
            assert text[chunk.start_char:chunk.end_char] == chunk.content


# ── extract_citations ─────────────────────────────────────────────────────────

class TestExtractCitations:

    @pytest.mark.unit
    def test_no_citations_in_response(self, engine, sample_chunks):
        citations = engine.extract_citations('This answer has no citations.', sample_chunks)
        assert citations == []

    @pytest.mark.unit
    def test_citation_with_page_number(self, engine, sample_chunks):
        response = 'According to Document 1, Page 2, farmers receive Rs 6000 annually.'
        citations = engine.extract_citations(response, sample_chunks)
        assert len(citations) == 1
        assert citations[0].document_id == 'doc-abc'
        assert citations[0].page_number == 2

    @pytest.mark.unit
    def test_citation_without_page_falls_back_to_chunk_page(self, engine, sample_chunks):
        response = 'As stated in Document 2, eligibility requires less than 2 hectares.'
        citations = engine.extract_citations(response, sample_chunks)
        assert len(citations) == 1
        assert citations[0].document_id == 'doc-def'
        assert citations[0].page_number == 5  # chunk's own page_number

    @pytest.mark.unit
    def test_duplicate_doc_and_page_deduplicated(self, engine, sample_chunks):
        response = 'Document 1, Page 2 says X. Document 1, Page 2 also confirms Y.'
        citations = engine.extract_citations(response, sample_chunks)
        assert len(citations) == 1

    @pytest.mark.unit
    def test_out_of_range_document_number_ignored(self, engine, sample_chunks):
        response = 'According to Document 99, Page 1, the benefit is available.'
        citations = engine.extract_citations(response, sample_chunks)
        assert citations == []

    @pytest.mark.unit
    def test_citation_excerpt_from_chunk_content(self, engine, sample_chunks):
        response = 'Document 1, Page 2 states the benefit amount.'
        citations = engine.extract_citations(response, sample_chunks)
        assert 'PM-KISAN' in citations[0].excerpt

    @pytest.mark.unit
    def test_confidence_score_taken_from_chunk_relevance(self, engine, sample_chunks):
        response = 'Document 1, Page 2 is the source.'
        citations = engine.extract_citations(response, sample_chunks)
        assert citations[0].confidence_score == 0.92

    @pytest.mark.unit
    def test_multiple_distinct_citations(self, engine, sample_chunks):
        response = 'Document 1, Page 2 and Document 2, Page 5 both describe the scheme.'
        citations = engine.extract_citations(response, sample_chunks)
        assert len(citations) == 2
        assert {c.document_id for c in citations} == {'doc-abc', 'doc-def'}
