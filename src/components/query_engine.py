"""Query engine component."""
import uuid
import json
import time
import hashlib
import dataclasses
from typing import List, Tuple
import boto3
from botocore.exceptions import ClientError

from ..models.query import QueryResult, Citation, RetrievedChunk
from ..config import load_config
from ..database.dynamodb_client import DynamoDBClient
from ..utils.circuit_breaker import CircuitBreaker
from ..utils.retry import async_retry_with_backoff


class QueryEngine:
    """Processes user queries against the Knowledge Base."""

    def __init__(self):
        self.config = load_config()
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=self.config.region)
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.config.region)
        self.db = DynamoDBClient()
        self._kb_breaker = CircuitBreaker()
        self._bedrock_breaker = CircuitBreaker()

    def _cache_key(self, query_text: str) -> str:
        """Generate a stable cache key from normalised query text."""
        normalized = query_text.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def query(self, query_text: str, language: str = "en") -> QueryResult:
        """
        Process a text query and return cited response.

        Pipeline:
        1. Check DynamoDB cache (hash of query text)
        2. Retrieve relevant chunks from Bedrock KB
        3. Generate LLM response with citations
        4. Store result in cache + log query
        """
        start_time = time.time()

        # ── Step 1: Cache lookup ──────────────────────────────────────────────
        cache_key = self._cache_key(query_text)
        cached = self.db.get_cached_response(cache_key)
        if cached:
            citations = [
                Citation(**c)
                for c in json.loads(cached.get('citations', '[]'))
            ]
            return QueryResult(
                answer=cached['answer'],
                citations=citations,
                query_id=str(uuid.uuid4()),
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # ── Step 2: Retrieve chunks ───────────────────────────────────────────
        chunks = await self.retrieve_relevant_chunks(query_text, top_k=5)

        if not chunks:
            return QueryResult(
                answer="I couldn't find relevant information in the available documents to answer your question.",
                citations=[],
                query_id=str(uuid.uuid4()),
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # ── Step 3: Generate response ─────────────────────────────────────────
        answer, citations = await self.generate_response(query_text, chunks)

        processing_time = int((time.time() - start_time) * 1000)
        query_id = str(uuid.uuid4())

        # ── Step 4: Cache + log ───────────────────────────────────────────────
        self.db.put_cached_response(
            cache_key,
            answer,
            [dataclasses.asdict(c) for c in citations],
        )
        self.db.log_query(
            query_id=query_id,
            query_text=query_text,
            source_language=language,
            response_text=answer,
            processing_time_ms=processing_time,
        )

        return QueryResult(
            answer=answer,
            citations=citations,
            query_id=query_id,
            processing_time_ms=processing_time,
        )

    @async_retry_with_backoff()
    async def retrieve_relevant_chunks(self, query_text: str, top_k: int = 5) -> List[RetrievedChunk]:
        """
        Perform semantic search against Bedrock Knowledge Base.

        Decorated with exponential-backoff retry so transient throttles
        are handled automatically (up to 3 retries, 1-30 s delay).
        """
        try:
            response = self._kb_breaker.call(
                self.bedrock_agent_runtime.retrieve,
                knowledgeBaseId=self.config.knowledge_base_id,
                retrievalQuery={'text': query_text},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {'numberOfResults': top_k}
                },
            )

            chunks = []
            for result in response.get('retrievalResults', []):
                content = result.get('content', {}).get('text', '')
                score = result.get('score', 0.0)
                metadata = result.get('metadata', {})
                chunks.append(RetrievedChunk(
                    chunk_id=metadata.get('chunk_id', str(uuid.uuid4())),
                    document_id=metadata.get('document_id', 'unknown'),
                    content=content,
                    relevance_score=score,
                    page_number=int(metadata.get('page_number', 1)),
                    section_reference=metadata.get('section_reference'),
                ))
            return chunks

        except ClientError:
            raise  # Let retry decorator handle ThrottlingException etc.

    @async_retry_with_backoff()
    async def generate_response(self, query: str, context_chunks: List[RetrievedChunk]) -> Tuple[str, List[Citation]]:
        """
        Generate LLM response with citations.

        Tries the primary model first; if it fails (throttle / error),
        automatically falls back to BEDROCK_FALLBACK_MODEL_ID.
        Also decorated with exponential-backoff retry for transient errors.
        """
        context = "\n\n".join([
            f"[Document {i+1}, Page {chunk.page_number}]\n{chunk.content}"
            for i, chunk in enumerate(context_chunks)
        ])

        prompt = f"""You are a helpful assistant that answers questions about government schemes based on official documents.

Context from official documents:
{context}

User Question: {query}

Instructions:
1. Answer the question using ONLY information from the context above
2. For each fact you state, cite the document number and page (e.g., "According to Document 1, Page 3...")
3. If the context doesn't contain enough information to answer the question, say so clearly
4. Be concise and accurate
5. Use simple language that citizens can understand

Answer:"""

        messages = [{"role": "user", "content": [{"text": prompt}]}]
        inference_config = {"maxTokens": 1000, "temperature": 0.3}

        # Try primary model, then fallback
        models = [self.config.bedrock_model_id, self.config.bedrock_fallback_model_id]
        last_error = None
        for model_id in models:
            try:
                response = self._bedrock_breaker.call(
                    self.bedrock_runtime.converse,
                    modelId=model_id,
                    messages=messages,
                    inferenceConfig=inference_config,
                )
                answer = response['output']['message']['content'][0]['text']
                citations = self.extract_citations(answer, context_chunks)
                return answer, citations
            except ClientError as e:
                last_error = e
                error_code = e.response.get('Error', {}).get('Code', '')
                if model_id != models[-1]:
                    print(f"Primary model {model_id} failed ({error_code}), trying fallback {models[-1]}…")

        raise last_error  # Both models failed — let retry decorator retry

    def extract_citations(self, llm_response: str, chunks: List[RetrievedChunk]) -> List[Citation]:
        """Parse LLM response to extract structured citations."""
        import re

        citations = []
        pattern = r'Document (\d+)(?:, Page (\d+))?'
        matches = re.finditer(pattern, llm_response)
        seen_citations = set()

        for match in matches:
            doc_num = int(match.group(1)) - 1
            page_num = int(match.group(2)) if match.group(2) else None

            if 0 <= doc_num < len(chunks):
                chunk = chunks[doc_num]
                citation_key = (chunk.document_id, chunk.page_number)
                if citation_key in seen_citations:
                    continue
                seen_citations.add(citation_key)

                excerpt = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
                citations.append(Citation(
                    document_id=chunk.document_id,
                    document_name=f"Document {doc_num + 1}",
                    page_number=page_num or chunk.page_number,
                    clause_reference=chunk.section_reference or "General",
                    excerpt=excerpt,
                    confidence_score=chunk.relevance_score,
                ))

        return citations
