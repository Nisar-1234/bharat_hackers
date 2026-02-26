"""Document processing component."""
import uuid
from datetime import datetime
from typing import List, Optional
import boto3
from botocore.exceptions import ClientError

from ..models.document import DocumentMetadata, DocumentChunk
from ..models.enums import DocumentStatus
from ..config import load_config


class FileTooLargeError(Exception):
    """Raised when uploaded file exceeds size limit."""
    pass


class UnsupportedFormatError(Exception):
    """Raised when file format is not supported."""
    pass


class DocumentProcessor:
    """Processes uploaded documents through OCR and chunking pipeline."""
    
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    SUPPORTED_MIME_TYPES = [
        'application/pdf',
        'image/png',
        'image/jpg',
        'image/jpeg'
    ]
    
    def __init__(self):
        self.config = load_config()
        self.s3_client = boto3.client('s3', region_name=self.config.region)
        self.textract_client = boto3.client('textract', region_name=self.config.region)
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=self.config.region)
    
    async def upload_document(
        self, 
        file_content: bytes, 
        filename: str, 
        mime_type: str
    ) -> DocumentMetadata:
        """
        Upload and process a document.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            mime_type: MIME type (application/pdf, image/png, etc.)
            
        Returns:
            DocumentMetadata with processing status
            
        Raises:
            FileTooLargeError: If file exceeds 50MB limit
            UnsupportedFormatError: If file type not supported
        """
        # Validate file size
        if len(file_content) > self.MAX_FILE_SIZE:
            raise FileTooLargeError(f"File size {len(file_content)} exceeds limit of {self.MAX_FILE_SIZE} bytes")
        
        # Validate MIME type
        if mime_type not in self.SUPPORTED_MIME_TYPES:
            raise UnsupportedFormatError(f"MIME type {mime_type} not supported")
        
        # Generate document ID and S3 key
        document_id = str(uuid.uuid4())
        s3_key = f"raw/{document_id}/{filename}"
        
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.config.s3_bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=mime_type
            )
            
            # Create metadata
            metadata = DocumentMetadata(
                document_id=document_id,
                filename=filename,
                s3_key=s3_key,
                upload_date=datetime.now(),
                status=DocumentStatus.PENDING,
                chunk_count=0,
                file_size_bytes=len(file_content),
                mime_type=mime_type
            )
            
            # TODO: Store metadata in Aurora
            
            return metadata
            
        except ClientError as e:
            raise Exception(f"Failed to upload document: {str(e)}")
    
    async def extract_text(self, s3_key: str, mime_type: str) -> str:
        """Extract text from document using Amazon Textract."""
        try:
            # Call Textract to analyze document
            response = self.textract_client.analyze_document(
                Document={
                    'S3Object': {
                        'Bucket': self.config.s3_bucket,
                        'Name': s3_key
                    }
                },
                FeatureTypes=['LAYOUT']
            )
            
            # Extract text while preserving paragraph structure
            blocks = response.get('Blocks', [])
            paragraphs = []
            current_paragraph = []
            
            for block in blocks:
                if block['BlockType'] == 'LINE':
                    text = block.get('Text', '')
                    if text:
                        current_paragraph.append(text)
                elif block['BlockType'] == 'PAGE' and current_paragraph:
                    # End of page, finalize paragraph
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
            
            # Add any remaining text
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
            
            # Join paragraphs with double newlines
            extracted_text = '\n\n'.join(paragraphs)
            
            # Store extracted text in S3
            document_id = s3_key.split('/')[1]
            processed_key = f"processed/{document_id}/extracted_text.txt"
            self.s3_client.put_object(
                Bucket=self.config.s3_bucket,
                Key=processed_key,
                Body=extracted_text.encode('utf-8'),
                ContentType='text/plain'
            )
            
            return extracted_text
            
        except ClientError as e:
            raise Exception(f"Failed to extract text: {str(e)}")
    
    def chunk_text(self, text: str, document_id: str) -> List[DocumentChunk]:
        """
        Split text into semantically meaningful chunks.
        
        Uses recursive character splitting with overlap to maintain context.
        Target chunk size: 1000 characters with 200 character overlap.
        """
        if not text:
            return []
        
        CHUNK_SIZE = 1000
        OVERLAP = 200
        
        chunks = []
        start = 0
        page_number = 1
        
        while start < len(text):
            # Calculate end position
            end = min(start + CHUNK_SIZE, len(text))
            
            # Extract chunk content
            chunk_content = text[start:end]
            
            # Create chunk object
            chunk = DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                document_id=document_id,
                content=chunk_content,
                page_number=page_number,
                section_reference=None,
                start_char=start,
                end_char=end
            )
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            start = end - OVERLAP if end < len(text) else end
            
            # Estimate page number (rough approximation: 3000 chars per page)
            page_number = (end // 3000) + 1
        
        return chunks
    
    async def ingest_to_knowledge_base(self, chunks: List[DocumentChunk]) -> bool:
        """Store chunks in Amazon Bedrock Knowledge Base with Titan embeddings."""
        try:
            # Store chunks in S3 for Knowledge Base ingestion
            for chunk in chunks:
                chunk_key = f"kb-chunks/{chunk.document_id}/{chunk.chunk_id}.txt"
                self.s3_client.put_object(
                    Bucket=self.config.s3_bucket,
                    Key=chunk_key,
                    Body=chunk.content.encode('utf-8'),
                    ContentType='text/plain',
                    Metadata={
                        'document_id': chunk.document_id,
                        'chunk_id': chunk.chunk_id,
                        'page_number': str(chunk.page_number)
                    }
                )
            
            # Trigger Knowledge Base sync
            # Note: In production, this would trigger a data source sync
            # For now, we'll assume the KB is configured to auto-sync from S3
            
            # TODO: Store chunk metadata in Aurora with knowledge_base_id
            
            return True
            
        except ClientError as e:
            raise Exception(f"Failed to ingest to knowledge base: {str(e)}")
    
    async def get_document_status(self, document_id: str) -> DocumentMetadata:
        """Retrieve current processing status of a document."""
        # TODO: Query Aurora for document metadata
        # For now, return a placeholder
        raise NotImplementedError("Database integration pending")
    
    async def delete_document(self, document_id: str) -> bool:
        """Remove document from S3, Aurora, and Knowledge Base."""
        try:
            # List and delete all S3 objects for this document
            prefixes = [
                f"raw/{document_id}/",
                f"processed/{document_id}/",
                f"kb-chunks/{document_id}/"
            ]
            
            for prefix in prefixes:
                # List objects with prefix
                response = self.s3_client.list_objects_v2(
                    Bucket=self.config.s3_bucket,
                    Prefix=prefix
                )
                
                # Delete objects
                if 'Contents' in response:
                    objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                    if objects_to_delete:
                        self.s3_client.delete_objects(
                            Bucket=self.config.s3_bucket,
                            Delete={'Objects': objects_to_delete}
                        )
            
            # TODO: Delete from Aurora (cascading delete will handle chunks)
            # TODO: Delete from Knowledge Base
            
            return True
            
        except ClientError as e:
            raise Exception(f"Failed to delete document: {str(e)}")
