# Implementation Plan: Jansahayak

## Overview

This implementation plan breaks down the Jansahayak GenAI-powered citizen assistant into discrete coding tasks. The system will be built using Python with AWS Lambda, FastAPI, and Amazon Bedrock services. The implementation follows a bottom-up approach: core components first, then integration, and finally API layer.

The plan prioritizes early validation through property-based testing using Hypothesis, ensuring correctness at each stage before moving to the next component.

## Tasks

- [ ] 1. Set up project structure and AWS infrastructure
  - Create Python project with virtual environment
  - Set up directory structure: `/src`, `/tests`, `/infrastructure`
  - Configure AWS CDK or Terraform for infrastructure as code
  - Define Lambda function structure for three main handlers
  - Set up requirements.txt with dependencies: boto3, fastapi, mangum, hypothesis, pytest
  - Configure environment variables for AWS service endpoints
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 2. Implement Aurora PostgreSQL schema and data models
  - [ ] 2.1 Create database schema SQL scripts
    - Write CREATE TABLE statements for documents, document_chunks, query_logs
    - Add indexes for performance (document_id, knowledge_base_id)
    - Add constraints for referential integrity and status validation
    - _Requirements: 7.2, 7.4_

  - [ ] 2.2 Implement Python data models using dataclasses
    - Create DocumentMetadata, DocumentChunk, Citation, QueryResult classes
    - Implement DocumentStatus and SupportedLanguage enums
    - Add validation methods for each model
    - _Requirements: 1.8, 7.2_

  - [ ]* 2.3 Write property test for data model validation
    - **Property 9: API Input Validation**
    - **Validates: Requirements 6.7**

- [ ] 3. Implement Document Processor component
  - [ ] 3.1 Create DocumentProcessor class with S3 upload functionality
    - Implement upload_document() method with file size validation (50MB limit)
    - Store original files in S3 under raw/{document_id}/ prefix
    - Generate unique document IDs using UUID
    - Handle MIME type validation (PDF, PNG, JPG, JPEG)
    - _Requirements: 1.1, 1.2, 1.6, 1.7, 7.1_

  - [ ] 3.2 Implement OCR text extraction using Amazon Textract
    - Create extract_text() method calling Textract's AnalyzeDocument API
    - Handle both PDF and image file types
    - Preserve paragraph structure from Textract response
    - Store extracted text in S3 under processed/{document_id}/
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ]* 3.3 Write property test for text extraction
    - **Property 1: Document Text Extraction**
    - **Validates: Requirements 1.1, 1.2, 1.3**

  - [ ] 3.4 Implement text chunking algorithm
    - Create chunk_text() method with recursive character splitting
    - Use 1000 character target size with 200 character overlap
    - Preserve section references and page numbers in chunks
    - Generate DocumentChunk objects with metadata
    - _Requirements: 1.4_

  - [ ]* 3.5 Write property test for text chunking
    - **Property 2: Text Chunking Consistency**
    - **Validates: Requirements 1.4**

  - [ ] 3.6 Implement Knowledge Base ingestion
    - Create ingest_to_knowledge_base() method
    - Call Bedrock Knowledge Base API to store chunks with Titan embeddings
    - Store knowledge_base_id in document_chunks table
    - Update document status to "completed" in Aurora
    - _Requirements: 1.5_

  - [ ] 3.7 Implement document status and deletion methods
    - Create get_document_status() to query Aurora
    - Create delete_document() to remove from S3, Aurora, and Knowledge Base
    - Ensure cascading deletes maintain referential integrity
    - _Requirements: 7.3, 7.4_

  - [ ]* 3.8 Write property test for document persistence
    - **Property 3: Document Persistence Round-Trip**
    - **Validates: Requirements 1.8, 7.1, 7.2**

  - [ ]* 3.9 Write property test for document deletion
    - **Property 7: Document Deletion Completeness**
    - **Validates: Requirements 7.3**

  - [ ]* 3.10 Write property test for storage integrity
    - **Property 8: Storage Referential Integrity**
    - **Validates: Requirements 7.4**

- [ ] 4. Checkpoint - Ensure document processing tests pass
  - Run all document processor tests
  - Verify S3, Textract, and Knowledge Base integration
  - Ask the user if questions arise

- [ ] 5. Implement Query Engine component
  - [ ] 5.1 Create QueryEngine class with semantic search
    - Implement retrieve_relevant_chunks() using Bedrock Knowledge Base RetrieveAndGenerate API
    - Configure to return top 5 most relevant chunks
    - Map Knowledge Base results to RetrievedChunk objects
    - _Requirements: 3.1_

  - [ ] 5.2 Implement LLM response generation with Claude 3 Sonnet
    - Create generate_response() method calling Bedrock Runtime
    - Design prompt template instructing Claude to cite sources
    - Pass retrieved chunks as context in the prompt
    - Handle "no relevant information" case
    - Implement 10-second timeout for query processing
    - _Requirements: 3.2, 3.3, 3.4, 3.5_

  - [ ] 5.3 Implement citation extraction logic
    - Create extract_citations() method to parse LLM response
    - Extract document name, page number, clause reference from response
    - Match citations back to RetrievedChunk objects
    - Calculate confidence scores based on relevance scores
    - Format citations with excerpts
    - _Requirements: 4.1, 4.2, 4.3, 4.5_

  - [ ] 5.4 Implement main query() method
    - Orchestrate retrieve → generate → extract pipeline
    - Log queries to query_logs table in Aurora
    - Track processing time
    - Return QueryResult with answer and citations
    - _Requirements: 3.1, 3.2, 3.3, 4.1_

  - [ ]* 5.5 Write property test for query grounding
    - **Property 5: Query Response Grounding**
    - **Validates: Requirements 3.3, 4.4**

  - [ ]* 5.6 Write property test for citation completeness
    - **Property 6: Citation Completeness**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.5**

- [ ] 6. Implement Voice Interface component
  - [ ] 6.1 Create VoiceInterface class with audio transcription
    - Implement transcribe_audio() using AWS Transcribe
    - Support Hindi, Telugu, Tamil, and English
    - Handle audio formats: WAV, MP3, FLAC
    - Return TranscriptionResult with confidence score
    - Handle poor audio quality errors
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6_

  - [ ] 6.2 Implement translation methods
    - Create translate_to_english() using Amazon Translate
    - Create translate_from_english() using Amazon Translate
    - Support Hindi (hi), Telugu (te), Tamil (ta) language codes
    - _Requirements: 2.4, 5.4_

  - [ ]* 6.3 Write property test for translation round-trip
    - **Property 4: Translation Round-Trip Consistency**
    - **Validates: Requirements 2.4, 5.4**

  - [ ] 6.4 Implement speech synthesis
    - Create synthesize_speech() using AWS Polly
    - Configure neural voices for Hindi (Aditi)
    - Configure standard voices for Telugu and Tamil
    - Return audio bytes in MP3 format
    - Store generated audio in S3 under audio/{query_id}/
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ] 6.5 Implement end-to-end voice query pipeline
    - Create process_voice_query() orchestrating full pipeline
    - Transcribe → Translate to English → Query → Translate response → Synthesize
    - Handle fallback to text response if synthesis fails
    - Return VoiceQueryResult with audio URL
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 7. Checkpoint - Ensure query and voice tests pass
  - Run all query engine and voice interface tests
  - Verify Bedrock, Transcribe, Translate, and Polly integration
  - Ask the user if questions arise

- [ ] 8. Implement error handling and resilience
  - [ ] 8.1 Create retry decorator with exponential backoff
    - Implement retry logic for AWS service calls
    - Configure max 3 retries with exponential backoff (1s, 2s, 4s)
    - Handle ThrottlingException, ServiceUnavailableException, InternalServerException
    - _Requirements: 8.1_

  - [ ] 8.2 Implement circuit breaker pattern
    - Create CircuitBreaker class tracking failure rates
    - Configure 5 failures in 60 seconds threshold
    - Implement 30-second recovery timeout
    - Apply to all AWS service clients
    - _Requirements: 8.1_

  - [ ] 8.3 Create error response formatter
    - Map exception types to HTTP status codes
    - Generate user-friendly error messages
    - Implement logging without exposing internal details
    - Create error response models
    - _Requirements: 6.6, 8.2, 8.3, 8.4_

  - [ ]* 8.4 Write property test for error logging
    - **Property 10: Error Logging Without Exposure**
    - **Validates: Requirements 8.3, 8.4**

- [ ] 9. Implement FastAPI application and endpoints
  - [ ] 9.1 Create FastAPI app with request/response models
    - Define Pydantic models: TextQueryRequest, VoiceQueryRequest, DocumentResponse, QueryResponse
    - Configure CORS middleware
    - Set up request validation
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.7_

  - [ ] 9.2 Implement POST /documents/upload endpoint
    - Accept multipart file upload
    - Validate file size and MIME type
    - Call DocumentProcessor.upload_document()
    - Return DocumentResponse with document_id and status
    - _Requirements: 6.1, 1.6, 1.7_

  - [ ] 9.3 Implement GET /documents endpoint
    - Query Aurora for all documents
    - Return list of DocumentResponse objects
    - Support pagination with limit/offset query parameters
    - _Requirements: 6.4_

  - [ ] 9.4 Implement GET /documents/{id}/status endpoint
    - Call DocumentProcessor.get_document_status()
    - Return DocumentResponse with current status
    - Return 404 if document not found
    - _Requirements: 6.5_

  - [ ] 9.5 Implement POST /query/text endpoint
    - Accept TextQueryRequest with query and language
    - Call QueryEngine.query()
    - Return QueryResponse with answer and citations
    - _Requirements: 6.2, 3.1, 3.2, 3.3_

  - [ ] 9.6 Implement POST /query/voice endpoint
    - Accept multipart audio file and language parameter
    - Call VoiceInterface.process_voice_query()
    - Return VoiceQueryResponse with transcription, answer, and audio URL
    - _Requirements: 6.3, 2.1, 2.2, 2.3, 5.1, 5.2, 5.3_

  - [ ] 9.7 Add global exception handler
    - Catch all unhandled exceptions
    - Use error response formatter
    - Log errors with request context
    - Return appropriate HTTP status codes
    - _Requirements: 6.6, 8.2, 8.3, 8.4_

- [ ] 10. Create Lambda function handlers
  - [ ] 10.1 Create document processor Lambda handler
    - Use Mangum adapter to wrap FastAPI app
    - Configure Lambda timeout to 5 minutes for document processing
    - Set memory to 2048MB for Textract operations
    - _Requirements: 1.1, 1.2, 1.8_

  - [ ] 10.2 Create query engine Lambda handler
    - Use Mangum adapter to wrap FastAPI app
    - Configure Lambda timeout to 15 seconds
    - Set memory to 1024MB
    - _Requirements: 3.1, 3.2, 3.3, 3.5_

  - [ ] 10.3 Create voice interface Lambda handler
    - Use Mangum adapter to wrap FastAPI app
    - Configure Lambda timeout to 30 seconds for audio processing
    - Set memory to 1536MB
    - _Requirements: 2.1, 2.2, 2.3, 5.1, 5.2, 5.3_

- [ ] 11. Set up infrastructure with AWS CDK or Terraform
  - [ ] 11.1 Define S3 buckets
    - Create jansahayak-documents bucket with lifecycle policies
    - Configure folder structure: raw/, processed/, audio/
    - Set up encryption at rest
    - _Requirements: 7.1_

  - [ ] 11.2 Define Aurora PostgreSQL cluster
    - Create serverless Aurora cluster
    - Configure VPC and security groups
    - Set up database initialization script
    - _Requirements: 7.2_

  - [ ] 11.3 Define Amazon Bedrock Knowledge Base
    - Create Knowledge Base with Titan Embeddings
    - Configure S3 as data source
    - Set up IAM roles for Lambda access
    - _Requirements: 1.5, 3.1_

  - [ ] 11.4 Define Lambda functions
    - Create three Lambda functions with appropriate IAM roles
    - Configure VPC access for Aurora connection
    - Set up environment variables
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ] 11.5 Define API Gateway
    - Create REST API with three routes
    - Configure Lambda integrations
    - Set up request validation
    - Enable CORS
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 12. Write integration tests
  - [ ]* 12.1 Write end-to-end document upload test
    - Test full pipeline: upload → OCR → chunk → ingest
    - Verify document appears in S3, Aurora, and Knowledge Base
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.8_

  - [ ]* 12.2 Write end-to-end text query test
    - Upload test document, wait for processing
    - Submit query and verify response with citations
    - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2_

  - [ ]* 12.3 Write end-to-end voice query test
    - Test full voice pipeline with sample audio files
    - Verify transcription, translation, query, and synthesis
    - Test all supported languages
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 5.1, 5.2, 5.3, 5.4_

  - [ ]* 12.4 Write API validation tests
    - Test all endpoints with invalid inputs
    - Verify 400 responses with descriptive errors
    - _Requirements: 6.6, 6.7_

- [ ] 13. Final checkpoint - Run full test suite
  - Run all unit tests, property tests, and integration tests
  - Verify all 10 correctness properties pass with 100+ iterations
  - Deploy to AWS and perform smoke tests
  - Ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property-based tests use Hypothesis with minimum 100 iterations
- Integration tests require AWS credentials and may incur costs
- The implementation follows a bottom-up approach: data models → components → API → infrastructure
- Checkpoints ensure incremental validation before moving to the next phase
