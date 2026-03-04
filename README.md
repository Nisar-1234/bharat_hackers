# Jansahayak - GenAI-Powered Citizen Assistant

[![AWS](https://img.shields.io/badge/AWS-Bedrock%20%7C%20Lambda%20%7C%20S3-orange)](https://aws.amazon.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **AI for Rural Innovation and Sustainable Systems**
> Democratizing access to government welfare schemes through multilingual voice-powered AI

A serverless GenAI backend with a Streamlit web UI that helps Indian citizens understand government welfare schemes by processing official documents and answering voice-based queries in regional languages (Hindi, Telugu, Tamil, English).

## Problem Statement

Rural Indian citizens struggle to navigate government welfare schemes due to:
- **Language barriers** — Complex English documentation
- **Literacy challenges** — Text-heavy scheme guidelines
- **Information asymmetry** — Dependency on intermediaries
- **Trust issues** — Misinformation about eligibility and benefits

## Solution

Jansahayak uses AWS GenAI to provide:
- **Voice-first interface** — Ask questions in your native language
- **Fact-checked answers** — Every response includes source citations
- **OCR processing** — Extracts text from PDFs and images
- **Semantic search** — Understands intent, not just keywords
- **Multilingual support** — Hindi, Telugu, Tamil, English

## Architecture

```
  Streamlit UI (ui/app.py)
         |
         | HTTP
         v
  API Gateway (REST API)
         |
         v
+------------------+------------------+------------------+
| Document Lambda  |  Query Lambda    |  Voice Lambda    |
|  (300s, 2GB)     |  (15s, 1GB)      |  (30s, 1.5GB)    |
+--------+---------+---------+--------+--------+---------+
         |                   |                 |
         v                   v                 v
    Textract           Bedrock KB          Transcribe
    (OCR)          (Claude + Titan)        Translate
                                             Polly
         |                   |                 |
         v                   v                 v
+----------------+  +------------------+  +----------+
|  S3 Bucket     |  |    DynamoDB      |  |  S3 Audio|
| raw/ processed |  | (metadata/logs)  |  |  output  |
| kb-chunks/     |  +------------------+  +----------+
+----------------+
```

All three Lambda functions serve the same FastAPI app (via Mangum). They differ only in timeout and memory configuration.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Compute | AWS Lambda (Python 3.11) |
| API | FastAPI + Mangum + API Gateway |
| AI/ML | Amazon Bedrock — Converse API (Claude 3 Sonnet or Nova), Titan Embeddings, Knowledge Base |
| OCR | Amazon Textract |
| Voice | AWS Transcribe, Translate, Polly |
| Storage | Amazon S3, DynamoDB (single-table) |
| Frontend | Streamlit |
| Resilience | Circuit breaker (per-service) + exponential backoff retry |
| IaC | Terraform (`infrastructure/terraform/`) |

## Project Structure

```
bharat_hackers/
├── src/
│   ├── api/            # FastAPI app + Pydantic request/response models
│   ├── components/     # DocumentProcessor, QueryEngine, VoiceInterface
│   ├── database/       # DynamoDBClient (single-table design)
│   ├── handlers/       # Lambda entry points (Mangum wrappers)
│   ├── models/         # Dataclasses + enums (DocumentStatus, SupportedLanguage)
│   ├── utils/          # Retry (exponential backoff), CircuitBreaker, ErrorHandler
│   └── config.py       # AWSConfig loaded from env vars
├── ui/                 # Streamlit web interface
│   ├── app.py          # Single-page multi-section UI
│   ├── requirements.txt
│   └── .env.example
├── infrastructure/
│   ├── terraform/      # IaC for all AWS resources
│   └── schema.sql      # Legacy Aurora schema (unused — kept for reference)
├── tests/              # pytest suite (markers: unit, integration, property)
├── requirements.txt
└── .env.example
```

## Quick Start

### Prerequisites
- Python 3.11+
- AWS CLI configured (`aws configure`)
- AWS credentials with access to Bedrock, S3, DynamoDB, Textract, Transcribe, Translate, Polly

### 1. Install dependencies

```bash
git clone https://github.com/Nisar-1234/bharat_hackers.git
cd bharat_hackers

pip install -r requirements.txt
pip install -r ui/requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in: AWS_ACCOUNT_ID, S3_BUCKET_NAME, KNOWLEDGE_BASE_ID
# AWS_REGION is injected automatically in Lambda — set it only for local dev
```

### 3. Run locally

```bash
# Terminal 1 — FastAPI backend (Swagger UI: http://localhost:8000/docs)
uvicorn src.api.app:app --reload

# Terminal 2 — Streamlit UI (http://localhost:8501)
streamlit run ui/app.py
```

Or use the convenience scripts:
```bash
./run_all.sh    # Git Bash / Linux / Mac
run_all.bat     # Windows CMD / PowerShell
```

> **Note:** Local mode calls real AWS services. There is no offline/mock mode.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/documents/upload` | Upload PDF/image (max 50MB) — runs full OCR + KB ingestion pipeline |
| `GET` | `/documents` | List documents (`?status=completed&limit=10`) |
| `GET` | `/documents/{id}/status` | Get processing status |
| `POST` | `/query/text` | Text query → semantic search + cited answer |
| `POST` | `/query/voice` | MP3 audio + language → transcription + answer + presigned audio URL |

### Example: Text Query

```bash
curl -X POST "http://localhost:8000/query/text" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the eligibility for PM-KISAN?", "language": "en"}'
```

**Response:**
```json
{
  "answer": "According to Document 1, Page 3, the eligibility...",
  "citations": [
    {
      "document_name": "Document 1",
      "page_number": 3,
      "clause_reference": "General",
      "excerpt": "All landholding farmer families...",
      "confidence_score": 0.92
    }
  ],
  "processing_time_ms": 3421
}
```

### Example: Voice Query

```bash
curl -X POST "http://localhost:8000/query/voice" \
  -F "audio=@question.mp3" \
  -F "language=hi"
```

**Response:**
```json
{
  "transcribed_text": "पीएम किसान के लिए पात्रता क्या है?",
  "answer_text": "छोटे और सीमांत किसान जिनके पास 2 हेक्टेयर से कम जमीन है...",
  "audio_url": "https://s3.amazonaws.com/jansahayak-documents/audio/.../response.mp3?...",
  "citations": [...]
}
```

> Voice input must be **MP3 format**. `audio_url` is a presigned HTTPS URL valid for 1 hour. Supported language codes: `en`, `hi`, `te`, `ta`.

## Data Pipeline

**Document ingestion** (synchronous, up to 300s):
```
Upload PDF/image
  → S3 raw/<id>/<filename>
  → Textract OCR (async job for PDFs, sync for images)
  → S3 processed/<id>/extracted_text.txt
  → Chunk (1000 chars, 200-char overlap)
  → S3 kb-chunks/<id>/<chunk_id>.txt + DynamoDB chunk metadata
  → Bedrock KB ingestion job (allow ~30-60s before queryable)
```

Status transitions: `PENDING → PROCESSING → COMPLETED` (or `FAILED`)

**Text query:**
```
Query text
  → Bedrock KB retrieve (Titan embeddings, top-5 chunks)
  → Bedrock Converse API (Claude/Nova) with citation prompt
  → Regex citation extraction
  → DynamoDB query log
```

**Voice query:**
```
MP3 audio
  → S3 upload → Transcribe async job (hi-IN / te-IN / ta-IN / en-IN)
  → Translate to English (AWS Translate)
  → QueryEngine (same as text query above)
  → Translate answer back to user language
  → Polly TTS (Aditi/standard for hi/te/ta — Joanna/neural for en)
  → S3 audio/<query_id>/response.mp3
  → Presigned HTTPS URL returned (1-hour expiry)
```

## Resilience

Critical AWS service calls are protected by three layers:

**1. DynamoDB response cache** — Repeated queries return cached answers instantly without hitting Bedrock. Cache key = SHA-256 of normalised query text. TTL = 24 hours. If Bedrock is unavailable, cached answers still serve returning users.

**2. LLM fallback model** — `QueryEngine.generate_response()` tries `BEDROCK_MODEL_ID` first. If it receives a `ClientError` (throttle, model unavailable), it immediately retries with `BEDROCK_FALLBACK_MODEL_ID` (default: `amazon.nova-lite-v1:0`). Both models use the same Converse API — zero code change required.

**3. Circuit breaker + retry** (per service):

*Circuit breaker* (`src/utils/circuit_breaker.py`) — opens after 5 failures in 60 seconds; recovers after 30 seconds:

| Component | Breaker | Protects |
|-----------|---------|---------|
| QueryEngine | `_kb_breaker` | Bedrock KB `retrieve()` |
| QueryEngine | `_bedrock_breaker` | Bedrock `converse()` |
| DocumentProcessor | `_textract_breaker` | Textract `detect_document_text()` |
| VoiceInterface | `_translate_breaker` | Translate (both directions) |
| VoiceInterface | `_polly_breaker` | Polly `synthesize_speech()` |

*Retry with exponential backoff* (`src/utils/retry.py`): max 3 retries, 1s base delay, 30s cap — applied via `@async_retry_with_backoff()` decorator on `retrieve_relevant_chunks()` and `generate_response()` — handles `ThrottlingException`, `ServiceUnavailableException`, `InternalServerException`.

## Testing

```bash
pytest tests/                    # all tests
pytest tests/ -m unit            # unit tests only (no AWS credentials needed)
pytest tests/ -m integration     # requires real AWS credentials
pytest tests/path/test_file.py::TestClass::test_name  # single test
```

Unit tests in `tests/test_unit.py` cover the two core pure functions with no AWS dependencies:

**Chunking (8 tests):** empty input, single chunk, multiple chunks, 200-char overlap enforcement, 1000-char max size, unique chunk IDs, content matches source slice, last chunk reaches end of text.

**Citation extraction (8 tests):** no citations, citation with page number, citation without page (falls back to chunk page), duplicate deduplication, out-of-range document number ignored, excerpt content, confidence score from chunk relevance, multiple distinct citations.

## Lambda Deployment

> Lambda runs on Linux. Always build with Linux platform flags — plain `pip install -t` on Windows installs Windows `.pyd` binaries that fail with `No module named 'pydantic_core._pydantic_core'` at runtime.

```bash
# Build Linux-compatible package
rm -rf lambda-package && mkdir lambda-package
pip install \
  --platform manylinux2014_x86_64 \
  --target lambda-package/ \
  --implementation cp \
  --python-version 3.11 \
  --only-binary=:all: \
  -r requirements.txt
cp -r src lambda-package/

# Create zip (Python — zip command not available in Git Bash on Windows)
python -c "
import zipfile, os
with zipfile.ZipFile('lambda_deployment.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('lambda-package'):
        for file in files:
            fp = os.path.join(root, file)
            zf.write(fp, os.path.relpath(fp, 'lambda-package'))
"

# Deploy to all three functions
for func in document-processor query-engine voice-interface; do
  aws lambda update-function-code \
    --function-name jansahayak-${func} \
    --zip-file fileb://lambda_deployment.zip
done
```

Handler format must be `src.handlers.<module>.handler` (e.g. `src.handlers.query_handler.handler`). Do not pass `AWS_REGION` in Lambda environment variables — it is reserved and injected automatically.

See `AWS_SETUP.md` for full first-time AWS infrastructure setup, `DEPLOYMENT.md` for the deployment checklist, and `RUN.md` for end-to-end testing commands.

## Architecture Decisions

**Why DynamoDB, not RDS/Aurora?**
We briefly implemented an Aurora PostgreSQL schema (see `infrastructure/schema.sql`) but switched to DynamoDB before the first working prototype. The reasons: Lambda cold starts with RDS require a VPC and incur connection overhead; DynamoDB is truly serverless and scales to zero cost with PAY_PER_REQUEST; our access patterns (point lookups by doc ID + status-filtered list queries) map cleanly to a single-table design with one GSI — no joins needed.

**Why AWS Lambda, not EC2 or ECS?**
The app has spiky, event-driven traffic: an upload is triggered once, a query fires in response to a user request. Lambda is zero-cost at idle, no server management, and each function type (document/query/voice) can have independent memory and timeout settings. EC2 or ECS would require always-on instances and a load balancer just to handle occasional hackathon-level traffic.

**Why Bedrock Knowledge Base, not a custom embedding pipeline?**
Bedrock KB manages the vector store (backed by OpenSearch Serverless), handles chunking and ingestion, and exposes a single `retrieve()` API. Building this with a custom embedding pipeline + pinecone/FAISS would require maintaining infrastructure, syncing on updates, and duplicating the chunking logic already present in our `DocumentProcessor`. KB lets us stay fully serverless with no extra services.

**Why the Converse API, not `invoke_model()` directly?**
The Converse API is model-agnostic — the same code path works for Claude 3 Sonnet, Claude 3.5 Haiku, and Amazon Nova (Lite/Pro/Micro). This lets us swap `BEDROCK_MODEL_ID` without touching application code, and is exactly what the LLM fallback uses: the primary model fails → fallback model is tried with the same request.

**Why Amazon Translate + Polly over a multilingual LLM prompt?**
Prompting Claude in Hindi/Telugu/Tamil works but costs more tokens (the full context + prompt in a regional language) and output quality for low-resource languages like Telugu is inconsistent. Using Translate lets the RAG pipeline operate in English (where embeddings are strongest) and translate only the final answer. Polly adds TTS without any additional LLM call. The total cost per voice query is lower and latency is more predictable.

**Why S3 for document storage, not DynamoDB?**
DynamoDB items have a 400KB limit. PDF documents and extracted text regularly exceed this. S3 is the right store for arbitrary-size blobs; DynamoDB holds only structured metadata and chunk indexes that are always small.

**Why response caching in DynamoDB?**
Once the Knowledge Base is loaded, the same citizen question (e.g., "PM-KISAN eligibility") will be asked repeatedly. Caching the Bedrock response by a hash of the normalised query avoids redundant embedding + LLM calls, reducing both latency and AWS cost. Cache items use DynamoDB's built-in TTL to expire after 24 hours so stale answers are automatically evicted.

## Key Configuration

All settings are loaded by `src/config.py` from environment variables:

| Variable | Default | Notes |
|----------|---------|-------|
| `AWS_REGION` | `us-east-1` | Do NOT set in Lambda env — it is reserved |
| `S3_BUCKET_NAME` | `jansahayak-documents` | |
| `DYNAMODB_TABLE_NAME` | `jansahayak-data` | |
| `KNOWLEDGE_BASE_ID` | *(required)* | Created in Bedrock console |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-sonnet-20240229-v1:0` | Any Converse-compatible model works |
| `BEDROCK_FALLBACK_MODEL_ID` | `amazon.nova-lite-v1:0` | Used if primary model throttles |
| `TITAN_EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v1` | |

## DynamoDB Schema

Table `jansahayak-data` (PAY_PER_REQUEST), GSI1 on `GSI1PK`/`GSI1SK`:

| Entity | PK | SK | GSI1PK |
|--------|----|----|--------|
| Document | `DOC#<id>` | `METADATA` | `STATUS#<status>` |
| Chunk | `DOC#<id>` | `CHUNK#<nnn>` | — |
| QueryLog | `QUERY#<date>` | `LOG#<time>#<id>` | `QUERYLOGS` |
| Cache | `CACHE#<sha256>` | `RESPONSE` | — |

`list_documents` with a status filter queries GSI1. Without a filter it falls back to a full table scan — avoid on large datasets. Cache items have a `ttl` attribute (epoch seconds); DynamoDB TTL auto-deletes expired entries.

## License

MIT License — Built for AWS GenAI Hackathon 2025 by Team Bharat Hackers

**GitHub**: https://github.com/Nisar-1234/bharat_hackers
