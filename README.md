# 🇮🇳 Jansahayak - GenAI-Powered Citizen Assistant

[![AWS](https://img.shields.io/badge/AWS-Bedrock%20%7C%20Lambda%20%7C%20S3-orange)](https://aws.amazon.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **AI for Rural Innovation and Sustainable Systems**  
> Democratizing access to government welfare schemes through multilingual voice-powered AI

A serverless backend system that helps Indian citizens understand government schemes by processing official documents and enabling voice-based queries in regional languages (Hindi, Telugu, Tamil, English).

## 🎯 Problem Statement

Rural Indian citizens struggle to navigate government welfare schemes due to:
- **Language barriers**: Complex English documentation
- **Literacy challenges**: Text-heavy scheme guidelines
- **Information asymmetry**: Dependency on intermediaries
- **Trust issues**: Misinformation about eligibility and benefits

## 💡 Solution

Jansahayak uses GenAI to provide:
- ✅ **Voice-first interface** - Ask questions in your native language
- ✅ **Fact-checked answers** - Every response includes source citations
- ✅ **OCR processing** - Extracts text from PDFs and images
- ✅ **Semantic search** - Understands intent, not just keywords
- ✅ **Multilingual support** - Hindi, Telugu, Tamil, English

## 🏗️ Architecture

```
┌─────────────┐
│   Frontend  │ (Streamlit/React)
└──────┬──────┘
       │
┌──────▼──────────────────────────────────────────┐
│           API Gateway (REST API)                │
└──────┬──────────────────────────────────────────┘
       │
┌──────▼──────────┬──────────────┬────────────────┐
│ Document Lambda │ Query Lambda │ Voice Lambda   │
│  (5min, 2GB)    │ (15s, 1GB)   │ (30s, 1.5GB)  │
└──────┬──────────┴──────┬───────┴────────┬───────┘
       │                 │                │
┌──────▼─────┐  ┌────────▼────────┐  ┌───▼────────┐
│  Textract  │  │ Bedrock (Claude │  │ Transcribe │
│    (OCR)   │  │  + Titan + KB)  │  │ Translate  │
└──────┬─────┘  └────────┬────────┘  │   Polly    │
       │                 │            └───┬────────┘
┌──────▼─────────────────▼────────────────▼────────┐
│    S3 (Documents)  │  DynamoDB (Metadata/Logs)   │
└────────────────────────────────────────────────────┘
```

## 🚀 Features

### Document Processing
- Upload PDFs and images (up to 50MB)
- OCR extraction with Amazon Textract
- Intelligent text chunking (1000 chars, 200 overlap)
- Vector embeddings with Titan
- Storage in Bedrock Knowledge Base

### Query Engine
- Semantic search (not keyword matching)
- Claude 3 Sonnet for grounded responses
- Automatic citation extraction
- Sub-10 second response time

### Voice Interface
- Speech-to-text (AWS Transcribe)
- Translation (Hindi/Telugu/Tamil ↔ English)
- Text-to-speech (AWS Polly)
- End-to-end voice query pipeline

## 📁 Project Structure

```
bharat_hackers/
├── src/
│   ├── api/                    # FastAPI application
│   │   ├── app.py             # REST endpoints
│   │   └── models.py          # Request/response models
│   ├── components/            # Core business logic
│   │   ├── document_processor.py
│   │   ├── query_engine.py
│   │   └── voice_interface.py
│   ├── handlers/              # Lambda handlers
│   ├── models/                # Data models
│   └── utils/                 # Retry, circuit breaker, errors
├── infrastructure/
│   ├── terraform/             # IaC for AWS resources
│   └── schema.sql             # Database schema
├── tests/                     # Test suite
├── requirements.txt           # Python dependencies
├── DEPLOYMENT.md              # Deployment guide
├── requirements.md            # Full requirements spec
└── design.md                  # Architecture document
```

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Compute** | AWS Lambda (Python 3.11) |
| **API** | FastAPI + API Gateway |
| **AI/ML** | Amazon Bedrock (Claude 3 Sonnet, Titan Embeddings) |
| **OCR** | Amazon Textract |
| **Voice** | AWS Transcribe, Translate, Polly |
| **Storage** | Amazon S3, DynamoDB |
| **IaC** | Terraform |

## 📦 Installation

### Prerequisites
- Python 3.11+
- AWS CLI configured
- Terraform 1.0+

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/Nisar-1234/bharat_hackers.git
cd bharat_hackers
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your AWS credentials
```

4. **Deploy infrastructure**
```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/documents/upload` | Upload PDF/image document |
| `GET` | `/documents` | List all documents |
| `GET` | `/documents/{id}/status` | Check processing status |
| `POST` | `/query/text` | Text query with citations |
| `POST` | `/query/voice` | Voice query (audio → answer → audio) |

### Example: Text Query

```bash
curl -X POST "https://api.jansahayak.in/query/text" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "प्रधानमंत्री किसान योजना के लिए पात्रता क्या है?",
    "language": "hi"
  }'
```

**Response:**
```json
{
  "answer": "प्रधानमंत्री किसान सम्मान निधि योजना के लिए पात्रता...",
  "citations": [
    {
      "document_name": "PM-KISAN Guidelines",
      "page_number": 3,
      "clause_reference": "Section 2.1",
      "excerpt": "All landholding farmer families...",
      "confidence_score": 0.92
    }
  ],
  "processing_time_ms": 3421
}
```

## 🎯 24-Hour Milestone

Once AWS credits are available, we will achieve:

1. ✅ Deploy all infrastructure (Aurora, S3, Bedrock KB, Lambda)
2. ✅ Upload 3 real government scheme PDFs (PM-KISAN, Ayushman Bharat, MGNREGA)
3. ✅ Test 10 Hindi queries with cited responses
4. ✅ Record demo video showing end-to-end flow
5. ✅ Validate response time < 10 seconds

## 📊 Data Strategy

### Data Sources
- Government scheme documents (PDFs, images)
- User voice queries (audio files)

### Storage
- **S3**: Raw documents, processed text, kb-chunks, audio responses
- **DynamoDB**: Document metadata, chunk metadata, query logs (single-table design)
- **Bedrock Knowledge Base**: Vector embeddings for semantic search (OpenSearch Serverless)

### Processing Pipeline
```
Upload → Textract (OCR) → Chunking → Embeddings → Knowledge Base
Query → Semantic Search → Claude → Citations → Response
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run unit tests only
pytest tests/ -m unit

# Run integration tests (requires AWS)
pytest tests/ -m integration
```

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines.

## 📄 License

This project is licensed under the MIT License.

## 👥 Team

Built for AWS GenAI Hackathon 2025 by Team Bharat Hackers

## 🔗 Links

- **GitHub**: https://github.com/Nisar-1234/bharat_hackers
- **Documentation**: [requirements.md](requirements.md), [design.md](design.md)
- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)

---

**Made with ❤️ for Rural India**
