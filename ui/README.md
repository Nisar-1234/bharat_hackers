# Jansahayak Streamlit UI

Simple and intuitive web interface for the Jansahayak GenAI Citizen Assistant.

## Features

-  **Home Dashboard** - Overview of all features
-  **Document Upload** - Upload PDFs and images for OCR processing
-  **Text Queries** - Ask questions in multiple languages with citations
-  **Voice Queries** - Upload audio files and get voice responses
-  **Document Library** - View all uploaded documents and their status

## Supported Languages

- English
- हिंदी (Hindi)
- తెలుగు (Telugu)
- தమிழ் (Tamil)

## Installation

```bash
# Navigate to UI directory
cd ui

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Set the API endpoint in your environment:

```bash
# For local development (FastAPI running locally)
export API_ENDPOINT=http://localhost:8000

# For production (deployed API Gateway)
export API_ENDPOINT=https://your-api-id.execute-api.us-east-1.amazonaws.com/prod
```

Or create a `.env` file in the `ui/` directory:

```
API_ENDPOINT=http://localhost:8000
```

## Running the UI

### Local Development (with local FastAPI)

Terminal 1 - Run FastAPI backend:
```bash
cd bharat_hackers
uvicorn src.api.app:app --reload
```

Terminal 2 - Run Streamlit UI:
```bash
cd bharat_hackers/ui
streamlit run app.py
```

### Production (with deployed Lambda/API Gateway)

```bash
cd bharat_hackers/ui
export API_ENDPOINT=https://your-api-id.execute-api.us-east-1.amazonaws.com/prod
streamlit run app.py
```

The UI will open in your browser at `http://localhost:8501`

## Usage

### 1. Upload Documents

1. Navigate to " Upload Document"
2. Choose a PDF or image file (max 50MB)
3. Click "Upload and Process"
4. Wait for processing to complete (may take a few minutes)
5. Check "Document Library" to see status

### 2. Ask Text Questions

1. Navigate to " Text Query"
2. Select your language
3. Type your question
4. Click "Get Answer"
5. View answer with source citations

### 3. Voice Queries

1. Navigate to " Voice Query"
2. Select your language
3. Upload an audio file (MP3, WAV, or FLAC)
4. Click "Process Voice Query"
5. View transcription, answer, and listen to voice response

### 4. Browse Documents

1. Navigate to " Document Library"
2. Filter by status (pending, processing, completed, failed)
3. View document details and processing status

## Features

### Document Upload
- Supports PDF, PNG, JPG, JPEG formats
- Max file size: 50MB
- Real-time processing status
- OCR extraction with Amazon Textract

### Text Queries
- Multilingual support (4 languages)
- Semantic search (not keyword matching)
- Source citations for every answer
- Sub-10 second response time

### Voice Queries
- Speech-to-text transcription
- Automatic language translation
- Text-to-speech synthesis
- Full voice pipeline in 30-60 seconds

### Document Library
- View all uploaded documents
- Filter by processing status
- Real-time status updates
- Document metadata display

## Troubleshooting

### API Connection Issues

If you see " API Offline" in the sidebar:

1. Check if the API endpoint is correct
2. Verify the backend is running (local or deployed)
3. Check network connectivity
4. Review API logs for errors

### Upload Failures

If document upload fails:

1. Check file size (must be < 50MB)
2. Verify file format (PDF, PNG, JPG, JPEG only)
3. Check API logs for detailed error messages
4. Ensure AWS services are properly configured

### Query Timeouts

If queries timeout:

1. Text queries: Should complete in < 15 seconds
2. Voice queries: May take up to 60 seconds
3. Document processing: May take up to 5 minutes
4. Check Lambda function timeouts in AWS Console

## Architecture

```
Streamlit UI (Port 8501)
        ↓
    HTTP Requests
        ↓
FastAPI Backend (Port 8000) OR API Gateway
        ↓
    AWS Lambda Functions
        ↓
AWS AI Services (Bedrock, Textract, Transcribe, etc.)
```

## Development

### Adding New Features

1. Add new page in `app.py`
2. Update navigation in sidebar
3. Implement API calls to backend
4. Add error handling and loading states

### Customizing UI

- Modify CSS in the `st.markdown()` section
- Update colors, fonts, and layout
- Add custom components as needed

### Testing

```bash
# Run with debug mode
streamlit run app.py --logger.level=debug

# Run on different port
streamlit run app.py --server.port=8502
```

## Deployment

### Deploy to Streamlit Cloud

1. Push code to GitHub
2. Go to https://share.streamlit.io/
3. Connect your repository
4. Set environment variables (API_ENDPOINT)
5. Deploy

### Deploy to AWS EC2

```bash
# Install dependencies
pip install -r requirements.txt

# Run with nohup
nohup streamlit run app.py --server.port=8501 --server.address=0.0.0.0 &
```

### Deploy with Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## License

MIT License - See main project LICENSE file

## Support

For issues and questions:
- Check the main project README
- Review AWS_SETUP.md for deployment issues
- Check CloudWatch logs for API errors
