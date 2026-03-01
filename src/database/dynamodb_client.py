"""DynamoDB client for Jansahayak."""
import boto3
from datetime import datetime
from typing import List, Optional
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from ..models.document import DocumentMetadata, DocumentChunk
from ..models.enums import DocumentStatus
from ..config import load_config


class DynamoDBClient:
    """DynamoDB client for all data operations."""

    def __init__(self):
        self.config = load_config()
        self.dynamodb = boto3.resource('dynamodb', region_name=self.config.region)
        self.table = self.dynamodb.Table(self.config.dynamodb_table_name)

    # ── Document operations ──────────────────────────────────────────────────

    def put_document(self, metadata: DocumentMetadata) -> bool:
        """Store document metadata."""
        try:
            self.table.put_item(
                Item={
                    'PK': f'DOC#{metadata.document_id}',
                    'SK': 'METADATA',
                    'EntityType': 'Document',
                    'document_id': metadata.document_id,
                    'filename': metadata.filename,
                    's3_key': metadata.s3_key,
                    'status': metadata.status.value,
                    'chunk_count': metadata.chunk_count,
                    'file_size_bytes': metadata.file_size_bytes,
                    'mime_type': metadata.mime_type,
                    'created_at': metadata.upload_date.isoformat(),
                    'updated_at': datetime.utcnow().isoformat(),
                    'GSI1PK': f'STATUS#{metadata.status.value}',
                    'GSI1SK': metadata.upload_date.isoformat(),
                }
            )
            return True
        except ClientError as e:
            print(f"Error storing document: {e}")
            return False

    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        """Retrieve document metadata by ID."""
        try:
            response = self.table.get_item(
                Key={'PK': f'DOC#{document_id}', 'SK': 'METADATA'}
            )
            if 'Item' not in response:
                return None
            item = response['Item']
            return DocumentMetadata(
                document_id=item['document_id'],
                filename=item['filename'],
                s3_key=item['s3_key'],
                upload_date=datetime.fromisoformat(item['created_at']),
                status=DocumentStatus(item['status']),
                chunk_count=int(item.get('chunk_count', 0)),
                file_size_bytes=int(item['file_size_bytes']),
                mime_type=item['mime_type'],
            )
        except ClientError as e:
            print(f"Error retrieving document: {e}")
            return None

    def update_document_status(
        self, document_id: str, status: DocumentStatus, chunk_count: int = 0
    ) -> bool:
        """Update document processing status and chunk count."""
        try:
            self.table.update_item(
                Key={'PK': f'DOC#{document_id}', 'SK': 'METADATA'},
                UpdateExpression=(
                    'SET #st = :status, chunk_count = :count, '
                    'updated_at = :updated, GSI1PK = :gsi1pk'
                ),
                ExpressionAttributeNames={'#st': 'status'},
                ExpressionAttributeValues={
                    ':status': status.value,
                    ':count': chunk_count,
                    ':updated': datetime.utcnow().isoformat(),
                    ':gsi1pk': f'STATUS#{status.value}',
                },
            )
            return True
        except ClientError as e:
            print(f"Error updating document status: {e}")
            return False

    def list_documents(
        self, status: Optional[str] = None, limit: int = 10
    ) -> List[DocumentMetadata]:
        """List documents, optionally filtered by status."""
        try:
            if status:
                response = self.table.query(
                    IndexName='GSI1',
                    KeyConditionExpression=Key('GSI1PK').eq(f'STATUS#{status}'),
                    Limit=limit,
                    ScanIndexForward=False,
                )
            else:
                response = self.table.scan(
                    FilterExpression='EntityType = :type',
                    ExpressionAttributeValues={':type': 'Document'},
                    Limit=limit,
                )

            documents = []
            for item in response.get('Items', []):
                documents.append(
                    DocumentMetadata(
                        document_id=item['document_id'],
                        filename=item['filename'],
                        s3_key=item['s3_key'],
                        upload_date=datetime.fromisoformat(item['created_at']),
                        status=DocumentStatus(item['status']),
                        chunk_count=int(item.get('chunk_count', 0)),
                        file_size_bytes=int(item['file_size_bytes']),
                        mime_type=item['mime_type'],
                    )
                )
            return documents
        except ClientError as e:
            print(f"Error listing documents: {e}")
            return []

    def delete_document(self, document_id: str) -> bool:
        """Delete document metadata and all its chunks."""
        try:
            # Delete metadata record
            self.table.delete_item(
                Key={'PK': f'DOC#{document_id}', 'SK': 'METADATA'}
            )

            # Find and batch-delete all chunk records
            response = self.table.query(
                KeyConditionExpression=(
                    Key('PK').eq(f'DOC#{document_id}') & Key('SK').begins_with('CHUNK#')
                )
            )
            with self.table.batch_writer() as batch:
                for item in response.get('Items', []):
                    batch.delete_item(Key={'PK': item['PK'], 'SK': item['SK']})

            return True
        except ClientError as e:
            print(f"Error deleting document: {e}")
            return False

    # ── Chunk operations ─────────────────────────────────────────────────────

    def put_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """Store document chunks in batch."""
        try:
            with self.table.batch_writer() as batch:
                for i, chunk in enumerate(chunks):
                    batch.put_item(
                        Item={
                            'PK': f'DOC#{chunk.document_id}',
                            'SK': f'CHUNK#{i:03d}',
                            'EntityType': 'Chunk',
                            'chunk_id': chunk.chunk_id,
                            'document_id': chunk.document_id,
                            'content': chunk.content,
                            'page_number': chunk.page_number,
                            'section_reference': chunk.section_reference or '',
                            'start_char': chunk.start_char,
                            'end_char': chunk.end_char,
                            'created_at': datetime.utcnow().isoformat(),
                        }
                    )
            return True
        except ClientError as e:
            print(f"Error storing chunks: {e}")
            return False

    def get_chunks(self, document_id: str) -> List[DocumentChunk]:
        """Retrieve all chunks for a document."""
        try:
            response = self.table.query(
                KeyConditionExpression=(
                    Key('PK').eq(f'DOC#{document_id}') & Key('SK').begins_with('CHUNK#')
                )
            )
            chunks = []
            for item in response.get('Items', []):
                chunks.append(
                    DocumentChunk(
                        chunk_id=item['chunk_id'],
                        document_id=item['document_id'],
                        content=item['content'],
                        page_number=int(item['page_number']),
                        section_reference=item.get('section_reference') or None,
                        start_char=int(item['start_char']),
                        end_char=int(item['end_char']),
                    )
                )
            return chunks
        except ClientError as e:
            print(f"Error retrieving chunks: {e}")
            return []

    # ── Query log operations ─────────────────────────────────────────────────

    def log_query(
        self,
        query_id: str,
        query_text: str,
        source_language: str,
        response_text: str,
        processing_time_ms: int,
    ) -> bool:
        """Log a query for analytics."""
        try:
            now = datetime.utcnow()
            date_key = now.strftime('%Y-%m-%d')
            time_key = now.strftime('%H:%M:%S')
            self.table.put_item(
                Item={
                    'PK': f'QUERY#{date_key}',
                    'SK': f'LOG#{time_key}#{query_id}',
                    'EntityType': 'QueryLog',
                    'query_id': query_id,
                    'query_text': query_text,
                    'source_language': source_language,
                    'response_text': response_text,
                    'processing_time_ms': processing_time_ms,
                    'created_at': now.isoformat(),
                    'GSI1PK': 'QUERYLOGS',
                    'GSI1SK': now.isoformat(),
                }
            )
            return True
        except ClientError as e:
            print(f"Error logging query: {e}")
            return False
