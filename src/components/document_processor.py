"""Document processing component."""
import uuid
import time
from datetime import datetime
from typing import List, Optional
import boto3
from botocore.exceptions import ClientError

from ..models.document import DocumentMetadata, DocumentChunk
from ..models.enums import DocumentStatus
from ..config import load_config
from ..database.dynamodb_client import DynamoDBClient


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
        self.db = DynamoDBClient()
    
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
            
            # Create and persist metadata as PENDING
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
            self.db.put_document(metadata)

            # Run full processing pipeline inline
            # (Document Lambda has 300s timeout — sufficient for OCR + chunking)
            try:
                self.db.update_document_status(document_id, DocumentStatus.PROCESSING)

                extracted_text = await self.extract_text(s3_key, mime_type)
                chunks = self.chunk_text(extracted_text, document_id)
                await self.ingest_to_knowledge_base(chunks)

                self.db.update_document_status(
                    document_id, DocumentStatus.COMPLETED, chunk_count=len(chunks)
                )
                metadata.status = DocumentStatus.COMPLETED
                metadata.chunk_count = len(chunks)
            except Exception as processing_error:
                self.db.update_document_status(document_id, DocumentStatus.FAILED)
                metadata.status = DocumentStatus.FAILED
                metadata.error_message = str(processing_error)

            return metadata

        except ClientError as e:
            raise Exception(f"Failed to upload document: {str(e)}")
    
    async def extract_text(self, s3_key: str, mime_type: str) -> str:
        """
        Extract text from document using Amazon Textract.

        Uses the async API (start/get) for PDFs to handle multi-page documents.
        Uses the sync API for single-page images.
        """
        try:
            if mime_type == 'application/pdf':
                all_blocks = self._extract_text_async(s3_key)
            else:
                response = self.textract_client.detect_document_text(
                    Document={
                        'S3Object': {
                            'Bucket': self.config.s3_bucket,
                            'Name': s3_key
                        }
                    }
                )
                all_blocks = response.get('Blocks', [])

            # Build text preserving page boundaries
            paragraphs = []
            current_paragraph = []

            for block in all_blocks:
                if block['BlockType'] == 'LINE':
                    text = block.get('Text', '')
                    if text:
                        current_paragraph.append(text)
                elif block['BlockType'] == 'PAGE' and current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []

            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))

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

    def _extract_text_async(self, s3_key: str) -> list:
        """Run Textract async job for multi-page PDFs and collect all blocks."""
        # Start async detection job
        start_response = self.textract_client.start_document_text_detection(
            DocumentLocation={
                'S3Object': {
                    'Bucket': self.config.s3_bucket,
                    'Name': s3_key
                }
            }
        )
        job_id = start_response['JobId']

        # Poll until complete (Lambda has 300s timeout)
        while True:
            result = self.textract_client.get_document_text_detection(JobId=job_id)
            status = result['JobStatus']

            if status == 'SUCCEEDED':
                break
            elif status == 'FAILED':
                raise Exception(f"Textract job failed: {result.get('StatusMessage', 'unknown')}")

            time.sleep(2)

        # Collect blocks from all pages (paginate through NextToken)
        all_blocks = result.get('Blocks', [])
        next_token = result.get('NextToken')

        while next_token:
            result = self.textract_client.get_document_text_detection(
                JobId=job_id, NextToken=next_token
            )
            all_blocks.extend(result.get('Blocks', []))
            next_token = result.get('NextToken')

        return all_blocks
    
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
        """Store chunks in S3 and trigger Bedrock Knowledge Base ingestion job."""
        try:
            # Write chunk text files to the S3 path the KB data source watches
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

            # Store chunk metadata in DynamoDB
            self.db.put_chunks(chunks)

            # Trigger Bedrock KB sync — look up data source ID dynamically
            ds_response = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=self.config.knowledge_base_id,
                maxResults=1
            )
            data_source_id = ds_response['dataSourceSummaries'][0]['dataSourceId']

            self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.config.knowledge_base_id,
                dataSourceId=data_source_id
            )

            return True

        except ClientError as e:
            raise Exception(f"Failed to ingest to knowledge base: {str(e)}")
    
    async def get_document_status(self, document_id: str) -> DocumentMetadata:
        """Retrieve current processing status of a document."""
        metadata = self.db.get_document(document_id)
        if metadata is None:
            raise Exception(f"Document {document_id} not found")
        return metadata
    
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
            
            self.db.delete_document(document_id)

            return True
            
        except ClientError as e:
            raise Exception(f"Failed to delete document: {str(e)}")
