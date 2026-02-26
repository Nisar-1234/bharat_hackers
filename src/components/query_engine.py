"""Query engine component."""
import uuid
import json
import time
from typing import List, Tuple
import boto3
from botocore.exceptions import ClientError

from ..models.query import QueryResult, Citation, RetrievedChunk
from ..config import load_config


class QueryEngine:
    """Processes user queries against the Knowledge Base."""
    
    def __init__(self):
        self.config = load_config()
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=self.config.region)
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.config.region)
    
    async def query(self, query_text: str, language: str = "en") -> QueryResult:
        """
        Process a text query and return cited response.
        
        Args:
            query_text: User's question in English
            language: Target response language code
            
        Returns:
            QueryResult with answer and citations
        """
        start_time = time.time()
        
        # Retrieve relevant chunks
        chunks = await self.retrieve_relevant_chunks(query_text, top_k=5)
        
        if not chunks:
            # No relevant information found
            return QueryResult(
                answer="I couldn't find relevant information in the available documents to answer your question.",
                citations=[],
                query_id=str(uuid.uuid4()),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # Generate response with citations
        answer, citations = await self.generate_response(query_text, chunks)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # TODO: Log query to Aurora
        
        return QueryResult(
            answer=answer,
            citations=citations,
            query_id=str(uuid.uuid4()),
            processing_time_ms=processing_time
        )
    
    async def retrieve_relevant_chunks(self, query_text: str, top_k: int = 5) -> List[RetrievedChunk]:
        """
        Perform semantic search against Knowledge Base.
        
        Uses Titan embeddings to find most relevant document chunks.
        """
        try:
            response = self.bedrock_agent_runtime.retrieve(
                knowledgeBaseId=self.config.knowledge_base_id,
                retrievalQuery={
                    'text': query_text
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': top_k
                    }
                }
            )
            
            chunks = []
            for result in response.get('retrievalResults', []):
                content = result.get('content', {}).get('text', '')
                score = result.get('score', 0.0)
                metadata = result.get('metadata', {})
                
                chunk = RetrievedChunk(
                    chunk_id=metadata.get('chunk_id', str(uuid.uuid4())),
                    document_id=metadata.get('document_id', 'unknown'),
                    content=content,
                    relevance_score=score,
                    page_number=int(metadata.get('page_number', 1)),
                    section_reference=metadata.get('section_reference')
                )
                chunks.append(chunk)
            
            return chunks
            
        except ClientError as e:
            raise Exception(f"Failed to retrieve chunks: {str(e)}")
    
    async def generate_response(self, query: str, context_chunks: List[RetrievedChunk]) -> Tuple[str, List[Citation]]:
        """
        Generate LLM response with citations using Claude 3 Sonnet.
        
        The prompt instructs Claude to:
        1. Only use information from provided context
        2. Cite specific sections for each claim
        3. Indicate when information is not available
        """
        # Build context from chunks
        context = "\n\n".join([
            f"[Document {i+1}, Page {chunk.page_number}]\n{chunk.content}"
            for i, chunk in enumerate(context_chunks)
        ])
        
        # Create prompt
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
        
        try:
            # Call Claude 3 Sonnet
            response = self.bedrock_runtime.invoke_model(
                modelId=self.config.bedrock_model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "temperature": 0.3,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })
            )
            
            response_body = json.loads(response['body'].read())
            answer = response_body['content'][0]['text']
            
            # Extract citations
            citations = self.extract_citations(answer, context_chunks)
            
            return answer, citations
            
        except ClientError as e:
            raise Exception(f"Failed to generate response: {str(e)}")
    
    def extract_citations(self, llm_response: str, chunks: List[RetrievedChunk]) -> List[Citation]:
        """Parse LLM response to extract structured citations."""
        import re
        
        citations = []
        
        # Pattern to match citations like "Document 1, Page 3" or "Document 2"
        pattern = r'Document (\d+)(?:, Page (\d+))?'
        matches = re.finditer(pattern, llm_response)
        
        seen_citations = set()
        
        for match in matches:
            doc_num = int(match.group(1)) - 1  # Convert to 0-indexed
            page_num = int(match.group(2)) if match.group(2) else None
            
            # Get corresponding chunk
            if 0 <= doc_num < len(chunks):
                chunk = chunks[doc_num]
                
                # Create unique key to avoid duplicates
                citation_key = (chunk.document_id, chunk.page_number)
                if citation_key in seen_citations:
                    continue
                seen_citations.add(citation_key)
                
                # Extract excerpt (first 200 chars of chunk)
                excerpt = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
                
                citation = Citation(
                    document_id=chunk.document_id,
                    document_name=f"Document {doc_num + 1}",
                    page_number=page_num or chunk.page_number,
                    clause_reference=chunk.section_reference or "General",
                    excerpt=excerpt,
                    confidence_score=chunk.relevance_score
                )
                citations.append(citation)
        
        return citations
