# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Jansahayak** — a serverless GenAI-powered citizen assistant helping rural Indians access government welfare schemes via multilingual voice interaction. Built for the AWS GenAI Hackathon.

## Commands

### Local Development
```bash
pip install -r requirements.txt
cp .env.example .env  # populate with real AWS credentials

# Run local dev server (Swagger UI at http://localhost:8000/docs)
uvicorn src.api.app:app --reload
```

Local mode still calls real AWS services (Bedrock, S3, DynamoDB, Textract, etc.). There is no mock/offline mode.

### Testing
```bash
pytest tests/                    # all tests
pytest tests/ -m unit            # unit tests only
pytest tests/ -m integration     # requires real AWS credentials
pytest tests/path/test_file.py::TestClass::test_name  # single test
```

Test suite is empty — markers (`unit`, `integration`, `property`) are configured in `pytest.ini` but no tests have been written yet.

### Lambda Packaging & Deploy

**Important:** Lambda runs on Linux. Always install dependencies with Linux platform flags — plain `pip install -t` on Windows installs Windows `.pyd` binaries that will fail with `No module named 'pydantic_core._pydantic_core'` at runtime.

```bash
rm -rf lambda-package && mkdir lambda-package

# Install Linux-compatible wheels (works from any OS)
pip install \
  --platform manylinux2014_x86_64 \
  --target lambda-package/ \
  --implementation cp \
  --python-version 3.11 \
  --only-binary=:all: \
  -r requirements.txt

cp -r src lambda-package/

# zip is not available in Git Bash on Windows — use Python instead
python -c "
import zipfile, os
with zipfile.ZipFile('lambda_deployment.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('lambda-package'):
        for file in files:
            fp = os.path.join(root, file)
            zf.write(fp, os.path.relpath(fp, 'lambda-package'))
"

# Update all three functions (run from project root where zip lives)
for func in document-processor query-engine voice-interface; do
  aws lambda update-function-code \
    --function-name jansahayak-${func} \
    --zip-file fileb://lambda_deployment.zip
done
```

## Architecture

**Runtime:** Python 3.11, FastAPI, deployed to AWS Lambda via Mangum (ASGI→Lambda adapter)

### Layer Structure

```
src/api/        → FastAPI app + Pydantic request/response models
src/components/ → Business logic: DocumentProcessor, QueryEngine, VoiceInterface
src/database/   → DynamoDBClient (single-table design: documents, chunks, query logs)
src/models/     → Dataclasses (document.py, query.py, voice.py) + enums.py
src/handlers/   → Lambda entry points (Mangum wrappers around the same FastAPI app)
src/utils/      → Retry (exponential backoff), CircuitBreaker, ErrorHandler
src/config.py   → Centralized env var loading into AWSConfig dataclass
infrastructure/ → Terraform configs + schema.sql (legacy Aurora schema, no longer used)
```

### API Endpoints

| Method | Path | Handler |
|--------|------|---------|
| GET | `/` | Health check |
| POST | `/documents/upload` | Upload PDF/image → full processing pipeline |
| GET | `/documents` | List documents (optional `?status=` filter, `?limit=`) |
| GET | `/documents/{id}/status` | Get document processing status |
| POST | `/query/text` | Text query → KB search + LLM answer + citations |
| POST | `/query/voice` | Audio file + language → full voice pipeline |

### Three Lambda Functions (different timeout/memory)

| Handler | Timeout | Memory | Purpose |
|---------|---------|--------|---------|
| `document_handler.py` | 300s | 2GB | Upload, OCR, chunk, ingest to KB |
| `query_handler.py` | 15s | 1GB | Semantic search + LLM generation |
| `voice_handler.py` | 30s | 1.5GB | Full voice pipeline |

All three wrap the same FastAPI app — they differentiate by Lambda configuration, not code.

### Data Flows

**Document ingestion** (synchronous within `/documents/upload`, up to 300s):
1. Validate (50MB max; PDF/PNG/JPG/JPEG only)
2. Upload raw file → S3 `raw/<id>/<filename>`
3. Textract OCR:
   - PDF: async job (`start_document_text_detection` + polling) — handles multi-page
   - Images: sync `detect_document_text`
4. Chunk text (1000 chars, 200-char overlap) → S3 `kb-chunks/<doc_id>/<chunk_id>.txt`
5. Store chunk metadata → DynamoDB
6. Start Bedrock KB ingestion job (async; allow ~30–60s before new content is queryable)

Status transitions: `PENDING → PROCESSING → COMPLETED` (or `FAILED`)

**Text query:** Bedrock KB semantic search (Titan embeddings) → retrieved chunks → Claude 3 Sonnet with citation prompt → regex citation extraction → DynamoDB query log

**Voice query:** Transcribe (S3 upload + async job) → Translate to English → QueryEngine → Translate back → Polly TTS → S3 audio URL

### AWS Services

| Service | Role |
|---------|------|
| Bedrock (Claude 3 Sonnet + Titan) | LLM generation + embeddings + Knowledge Base |
| DynamoDB | Document metadata, chunk metadata, query logs (single-table) |
| S3 | Raw documents, processed text, kb-chunks, audio output |
| Textract | PDF/image OCR (async for PDFs, sync for images) |
| Transcribe / Translate / Polly | Voice pipeline (hi, te, ta, en) |
| API Gateway | HTTP API frontend |
| Lambda | Serverless compute (3 functions) |

**Polly voice mapping:** Hindi/Telugu/Tamil → `Aditi` (standard engine only; neural not available). English → `Joanna` (neural).

### DynamoDB Single-Table Design

Table: `jansahayak-data`, PAY_PER_REQUEST, GSI1 on `GSI1PK`/`GSI1SK`

| Entity | PK | SK | GSI1PK | GSI1SK |
|--------|----|----|--------|--------|
| Document | `DOC#<id>` | `METADATA` | `STATUS#<status>` | ISO timestamp |
| Chunk | `DOC#<id>` | `CHUNK#<nnn>` | — | — |
| QueryLog | `QUERY#<date>` | `LOG#<time>#<id>` | `QUERYLOGS` | ISO timestamp |

`list_documents` with a status filter uses the GSI1 query. Without a filter, it falls back to a full table Scan — avoid on large datasets.

### Key Configuration (`.env` / `src/config.py`)

```
AWS_REGION, AWS_ACCOUNT_ID
S3_BUCKET_NAME
DYNAMODB_TABLE_NAME          (default: jansahayak-data)
KNOWLEDGE_BASE_ID
BEDROCK_MODEL_ID             (default: anthropic.claude-3-sonnet-20240229-v1:0)
TITAN_EMBEDDING_MODEL_ID     (default: amazon.titan-embed-text-v1)
```

## Resilience Patterns

`src/utils/retry.py` — `@retry` and `@async_retry` decorators with exponential backoff (max 3 retries, 1s base, 30s cap) for AWS throttling exceptions.

`src/utils/circuit_breaker.py` — CircuitBreaker class (CLOSED→OPEN→HALF_OPEN); opens after 5 failures in 60s, recovers after 30s.

## Lambda IAM Permissions

The Lambda execution role needs these service permissions:
- **S3**: Read/Write on the documents bucket
- **Textract**: `AnalyzeDocument`, `StartDocumentTextDetection`, `GetDocumentTextDetection`
- **Bedrock**: `InvokeModel`, `Retrieve` (Knowledge Base), `StartIngestionJob`, `ListDataSources`
- **Transcribe**: `StartTranscriptionJob`, `GetTranscriptionJob`
- **Translate**: `TranslateText`
- **Polly**: `SynthesizeSpeech`
- **DynamoDB**: Read/Write on `jansahayak-data` table

CloudWatch logs land in `/aws/lambda/jansahayak-{document-processor,query-engine,voice-interface}`.

## Lambda Deployment Notes

**Handler format** must be `src.handlers.<module>.handler` — e.g. `src.handlers.query_handler.handler`. Using just `query_handler.handler` causes `Runtime.ImportModuleError`.

**`AWS_REGION` is a reserved Lambda env var** — do not pass it in `--environment Variables={...}`. Lambda injects it automatically; passing it causes `InvalidParameterValueException`.

**`fileb://` path is relative to CWD** — always run `aws lambda` commands from the project root where `lambda_deployment.zip` lives, not from inside `lambda-package/`.

**AWS CLI path conversion on Windows Git Bash** — prefix commands that use `/aws/...` log group paths with `MSYS_NO_PATHCONV=1` to prevent Git Bash from mangling them:
```bash
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/jansahayak-query-engine --follow
```

**Testing deployed functions** — the handlers are Mangum/FastAPI wrappers, so `aws lambda invoke` requires an API Gateway v2 event, not a raw JSON body:
```bash
MSYS_NO_PATHCONV=1 aws lambda invoke \
  --function-name jansahayak-query-engine \
  --cli-binary-format raw-in-base64-out \
  --payload '{"version":"2.0","routeKey":"POST /query/text","rawPath":"/query/text","headers":{"content-type":"application/json"},"body":"{\"query\":\"test\",\"language\":\"en\"}","isBase64Encoded":false}' \
  response.json && cat response.json
```

## Key Deployment Docs

- `AWS_SETUP.md` — full step-by-step AWS deployment with cost protection
- `RUN.md` — how to run the deployed app, test every endpoint, demo script for judges
- `DYNAMODB_MIGRATION.md` — rationale and data model for Aurora → DynamoDB switch

> **Note:** `infrastructure/schema.sql` is a legacy Aurora PostgreSQL schema kept for reference only. The application uses DynamoDB exclusively.
