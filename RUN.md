# RUN.md — Running Jansahayak After Deployment

This guide assumes you have completed every step in `AWS_SETUP.md` and have a live API endpoint. Follow the sections in order on your first run.

---

## Prerequisites

```bash
# Confirm your .env is populated
cat .env
# Must have all of these filled (no angle-bracket placeholders):
# AWS_REGION, AWS_ACCOUNT_ID, S3_BUCKET_NAME, DYNAMODB_TABLE_NAME,
# KNOWLEDGE_BASE_ID, BEDROCK_MODEL_ID, TITAN_EMBEDDING_MODEL_ID, API_ENDPOINT

# Load variables into your shell
export $(grep -v '^#' .env | xargs)

# Quick smoke test — health check
curl -s ${API_ENDPOINT}/ | python3 -m json.tool
# Expected: {"status": "healthy", "service": "Jansahayak"}
```

If the health check fails, check CloudWatch logs before going further:
```bash
aws logs tail /aws/lambda/jansahayak-document-processor --since 5m
```

---

## Full End-to-End Flow

```
Upload PDF
  → Textract OCR
  → Chunk text (1000 chars, 200 overlap)
  → Store chunks in S3 (kb-chunks/)
  → Store chunk metadata in DynamoDB
  → Start Bedrock KB ingestion job
  → COMPLETED

Text Query  ──→  Bedrock KB semantic search (Titan)
                 → Claude 3 Sonnet generates answer
                 → Citations extracted
                 → Query logged to DynamoDB
                 → Return answer + citations

Voice Query ──→  Transcribe (audio → text in native language)
                 → Translate (native → English)
                 → Text query pipeline (above)
                 → Translate (English → native)
                 → Polly TTS (text → audio)
                 → Store audio in S3
                 → Return transcription + answer + audio URL + citations
```

---

## Step 1 — Upload a Government Scheme Document

Use a real PDF for the demo (e.g., PM-KISAN guidelines, MGNREGA rules).

```bash
# Upload a PDF
curl -s -X POST "${API_ENDPOINT}/documents/upload" \
  -F "file=@/path/to/pm-kisan-guidelines.pdf" \
  | python3 -m json.tool
```

**Expected response:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "pm-kisan-guidelines.pdf",
  "status": "completed",
  "message": "Document uploaded successfully. Processing will begin shortly."
}
```

> **Status values:**
> - `pending` → just received
> - `processing` → OCR + chunking in progress
> - `completed` → in Knowledge Base, ready to query
> - `failed` → check CloudWatch logs for the error

**Save the document ID:**
```bash
export DOC_ID=<paste-document_id-from-response>
```

> **Upload takes 15–60 seconds** depending on PDF size. Textract OCR runs synchronously inside the 5-minute Lambda. After the response returns `"status": "completed"`, the Bedrock KB ingestion job has been started — wait ~30 seconds before running queries to allow embeddings to finish indexing.

---

## Step 2 — Check Document Status

```bash
curl -s "${API_ENDPOINT}/documents/${DOC_ID}/status" | python3 -m json.tool
```

**Expected:**
```json
{
  "document_id": "550e8400-...",
  "filename": "pm-kisan-guidelines.pdf",
  "status": "completed",
  "upload_date": "2025-01-15T10:30:00",
  "chunk_count": 42,
  "file_size_bytes": 2097152
}
```

If status is `failed`, tail logs:
```bash
aws logs tail /aws/lambda/jansahayak-document-processor --since 10m
```

---

## Step 3 — List All Documents

```bash
# All documents
curl -s "${API_ENDPOINT}/documents" | python3 -m json.tool

# Filter by status
curl -s "${API_ENDPOINT}/documents?status=completed" | python3 -m json.tool

# Limit results
curl -s "${API_ENDPOINT}/documents?limit=5" | python3 -m json.tool
```

---

## Step 4 — Text Query

### English query
```bash
curl -s -X POST "${API_ENDPOINT}/query/text" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the eligibility criteria for PM-KISAN scheme?",
    "language": "en"
  }' | python3 -m json.tool
```

### Hindi query
```bash
curl -s -X POST "${API_ENDPOINT}/query/text" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "प्रधानमंत्री किसान योजना के लिए पात्रता क्या है?",
    "language": "hi"
  }' | python3 -m json.tool
```

### Telugu query
```bash
curl -s -X POST "${API_ENDPOINT}/query/text" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "PM-KISAN పథకానికి అర్హత ఏమిటి?",
    "language": "te"
  }' | python3 -m json.tool
```

**Expected response:**
```json
{
  "answer": "According to Document 1, Page 3, the eligibility criteria for PM-KISAN...",
  "citations": [
    {
      "document_id": "550e8400-...",
      "document_name": "Document 1",
      "page_number": 3,
      "clause_reference": "General",
      "excerpt": "Eligibility: All land-holding farmer families...",
      "confidence_score": 0.87
    }
  ],
  "processing_time_ms": 3241
}
```

> If `citations` is empty and answer says "couldn't find relevant information" — the Bedrock KB hasn't finished indexing yet. Wait 30–60 seconds and retry.

---

## Step 5 — Voice Query

Accepts MP3, WAV, or FLAC audio. The `language` field must match the language spoken in the audio.

```bash
# Hindi voice query
curl -s -X POST "${API_ENDPOINT}/query/voice" \
  -F "audio=@/path/to/hindi-question.mp3" \
  -F "language=hi" \
  | python3 -m json.tool

# English voice query
curl -s -X POST "${API_ENDPOINT}/query/voice" \
  -F "audio=@/path/to/english-question.mp3" \
  -F "language=en" \
  | python3 -m json.tool
```

**Supported language codes:** `hi` (Hindi), `te` (Telugu), `ta` (Tamil), `en` (English)

**Expected response:**
```json
{
  "transcribed_text": "प्रधानमंत्री किसान योजना के लिए पात्रता क्या है",
  "answer_text": "पीएम-किसान योजना के तहत, सभी भूमि-धारक किसान परिवार...",
  "audio_url": "s3://jansahayak-documents-123456789/audio/query-uuid/response.mp3",
  "citations": [...]
}
```

> **Voice query limit:** Lambda timeout is 30 seconds. Keep audio under 30 seconds. Longer audio may time out.

---

## Verify Data in DynamoDB

```bash
# Count all records
aws dynamodb scan \
  --table-name jansahayak-data \
  --select COUNT \
  --query "Count"

# View document records
aws dynamodb scan \
  --table-name jansahayak-data \
  --filter-expression "EntityType = :t" \
  --expression-attribute-values '{":t":{"S":"Document"}}' \
  --query "Items[*].[document_id.S, filename.S, status.S]" \
  --output table

# View recent query logs
aws dynamodb query \
  --table-name jansahayak-data \
  --index-name GSI1 \
  --key-condition-expression "GSI1PK = :pk" \
  --expression-attribute-values '{":pk":{"S":"QUERYLOGS"}}' \
  --scan-index-forward false \
  --limit 5 \
  --query "Items[*].[query_text.S, source_language.S, processing_time_ms.N]" \
  --output table
```

---

## Watch Logs Live

Open three terminal tabs during testing:

```bash
# Tab 1 — Document processor (upload, OCR, chunking)
aws logs tail /aws/lambda/jansahayak-document-processor --follow

# Tab 2 — Query engine (Bedrock calls, citation extraction)
aws logs tail /aws/lambda/jansahayak-query-engine --follow

# Tab 3 — Voice interface (transcription, translation, TTS)
aws logs tail /aws/lambda/jansahayak-voice-interface --follow
```

---

## Local Development (No AWS Required for Basic Testing)

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill env
cp .env.example .env
# Fill in your AWS credentials and IDs

# Run local server
uvicorn src.api.app:app --reload
# API at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

> Local mode still calls real AWS services — Bedrock, S3, DynamoDB, etc. There is no mock/offline mode. You need valid AWS credentials in `.env`.

---

## Troubleshooting

### Upload returns `status: failed`
```bash
aws logs tail /aws/lambda/jansahayak-document-processor --since 5m
```
Common causes:
- Bedrock model access not granted — go to Bedrock console → Model access → enable Claude 3 Sonnet + Titan
- Textract can't parse the PDF — try a different PDF or a scanned image PNG
- `KNOWLEDGE_BASE_ID` env var not set in Lambda — re-run the Lambda update command from `AWS_SETUP.md`

### Query returns "couldn't find relevant information"
1. Wait 60 seconds — Bedrock KB ingestion is async and may still be indexing
2. Check KB sync status in the console: Bedrock → Knowledge bases → jansahayak-kb → Data source → View job status
3. Manually trigger sync if needed:
```bash
# Get data source ID
DATA_SOURCE_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id ${KNOWLEDGE_BASE_ID} \
  --query "dataSourceSummaries[0].dataSourceId" \
  --output text)

# Start sync
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KNOWLEDGE_BASE_ID} \
  --data-source-id ${DATA_SOURCE_ID}
```

### Voice query times out (504/Lambda timeout)
- Audio file is too long — keep voice queries under 20 seconds
- Transcribe job is taking longer than the 30s Lambda limit
- Workaround: use text query (`POST /query/text`) for the demo instead

### API returns 500 Internal Server Error
```bash
# Check which Lambda is failing
aws logs tail /aws/lambda/jansahayak-query-engine --since 2m
```
Most common cause: missing environment variable. Verify:
```bash
aws lambda get-function-configuration \
  --function-name jansahayak-query-engine \
  --query "Environment.Variables"
```

### DynamoDB access denied
IAM policy needs DynamoDB permissions. Re-attach the policy:
```bash
aws iam attach-role-policy \
  --role-name JansahayakLambdaRole \
  --policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/JansahayakPolicy
```

---

## Demo Script (for Hackathon Evaluators)

This is the exact sequence to demonstrate for the judges:

```bash
# 1. Show health check
curl -s ${API_ENDPOINT}/

# 2. Upload a government scheme PDF (show the returned document_id)
curl -s -X POST "${API_ENDPOINT}/documents/upload" \
  -F "file=@pm-kisan-guidelines.pdf"

# 3. Wait ~30 seconds for Bedrock KB to index

# 4. Query in Hindi — show semantic understanding + citations
curl -s -X POST "${API_ENDPOINT}/query/text" \
  -H "Content-Type: application/json" \
  -d '{"query":"प्रधानमंत्री किसान योजना के लिए पात्रता क्या है?","language":"hi"}'

# 5. Query same thing in English — show same KB, multilingual
curl -s -X POST "${API_ENDPOINT}/query/text" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the eligibility for PM-KISAN?","language":"en"}'

# 6. Show DynamoDB logged the queries
aws dynamodb scan --table-name jansahayak-data --select COUNT

# 7. (Optional) Voice query demo
curl -s -X POST "${API_ENDPOINT}/query/voice" \
  -F "audio=@hindi-question.mp3" \
  -F "language=hi"
```

---

## Known Limitations

| Limitation | Workaround |
|------------|-----------|
| Voice Lambda 30s timeout | Keep audio under 20 seconds |
| Bedrock KB indexing is async (~30–60s after upload) | Wait before querying |
| Telugu/Tamil TTS uses Hindi voice (Aditi) — Polly doesn't support those languages natively | Acceptable for demo; response text is still in correct language |
| All 3 Lambda functions serve all routes (same FastAPI app) | By design for hackathon — differentiation is timeout/memory only |
| Upload is synchronous (waits for full OCR pipeline) | Expected — document processor Lambda has 5-minute timeout |
