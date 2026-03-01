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
| `POST` | `/query/voice` | MP3 audio + language → transcription + answer + voice response |

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

> Voice input must be **MP3 format**. Supported language codes: `en`, `hi`, `te`, `ta`.

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
  → S3 upload → Transcribe async job (language: hi-IN / te-IN / ta-IN / en-IN)
  → Translate to English (AWS Translate)
  → QueryEngine (same as text query)
  → Translate answer back to user language
  → Polly TTS (Aditi/standard for hi/te/ta, Joanna/neural for en)
  → S3 audio/<query_id>/response.mp3
```

## Testing

```bash
pytest tests/                    # all tests
pytest tests/ -m unit            # unit tests only
pytest tests/ -m integration     # requires real AWS credentials
pytest tests/path/test_file.py::TestClass::test_name  # single test
```

> The test suite is currently empty. Markers (`unit`, `integration`, `property`) are configured in `pytest.ini` with `asyncio_mode = auto`.

## Lambda Deployment

```bash
# Build Linux-compatible package (required even on Windows)
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

See [AWS_SETUP.md](AWS_SETUP.md) for full first-time AWS infrastructure setup, [DEPLOYMENT.md](DEPLOYMENT.md) for the deployment checklist, and [RUN.md](RUN.md) for end-to-end testing commands.

## Key Configuration

All settings are loaded by `src/config.py` from environment variables:

| Variable | Default | Notes |
|----------|---------|-------|
| `AWS_REGION` | `us-east-1` | Do NOT set in Lambda env — it's reserved |
| `S3_BUCKET_NAME` | `jansahayak-documents` | |
| `DYNAMODB_TABLE_NAME` | `jansahayak-data` | |
| `KNOWLEDGE_BASE_ID` | *(required)* | Created in Bedrock console |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-sonnet-20240229-v1:0` | Any Converse-compatible model works |
| `TITAN_EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v1` | |

## DynamoDB Schema

Table `jansahayak-data` (PAY_PER_REQUEST), GSI1 on `GSI1PK`/`GSI1SK`:

| Entity | PK | SK | GSI1PK |
|--------|----|----|--------|
| Document | `DOC#<id>` | `METADATA` | `STATUS#<status>` |
| Chunk | `DOC#<id>` | `CHUNK#<nnn>` | — |
| QueryLog | `QUERY#<date>` | `LOG#<time>#<id>` | `QUERYLOGS` |

## License

MIT License — Built for AWS GenAI Hackathon 2025 by Team Bharat Hackers

**GitHub**: https://github.com/Nisar-1234/bharat_hackers
