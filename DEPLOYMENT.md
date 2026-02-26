# Jansahayak Deployment Guide

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your AWS credentials and configuration
```

### 3. Initialize Database

```bash
# Connect to your Aurora PostgreSQL instance
psql -h <your-aurora-endpoint> -U admin -d jansahayak -f infrastructure/schema.sql
```

### 4. Deploy Infrastructure

#### Using Terraform

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

#### Manual Setup

If deploying manually:
1. Create S3 bucket: `jansahayak-documents`
2. Create Aurora PostgreSQL cluster
3. Create Bedrock Knowledge Base with Titan embeddings
4. Create Lambda functions from handlers
5. Set up API Gateway

### 5. Package Lambda Functions

```bash
# Create deployment package
pip install -r requirements.txt -t package/
cd package
zip -r ../lambda_deployment.zip .
cd ..
zip -g lambda_deployment.zip -r src/
```

### 6. Deploy Lambda Functions

```bash
aws lambda update-function-code \
  --function-name jansahayak-document-processor \
  --zip-file fileb://lambda_deployment.zip

aws lambda update-function-code \
  --function-name jansahayak-query-engine \
  --zip-file fileb://lambda_deployment.zip

aws lambda update-function-code \
  --function-name jansahayak-voice-interface \
  --zip-file fileb://lambda_deployment.zip
```

## Testing

### Run Unit Tests

```bash
pytest tests/ -m unit
```

### Run Integration Tests

```bash
# Requires AWS credentials
pytest tests/ -m integration
```

### Test API Locally

```bash
uvicorn src.api.app:app --reload
```

Then visit: http://localhost:8000/docs

## Configuration

### Environment Variables

Required environment variables:

- `AWS_REGION`: AWS region (default: us-east-1)
- `S3_BUCKET_NAME`: S3 bucket for documents
- `DB_HOST`: Aurora PostgreSQL endpoint
- `DB_NAME`: Database name (default: jansahayak)
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password
- `KNOWLEDGE_BASE_ID`: Bedrock Knowledge Base ID
- `BEDROCK_MODEL_ID`: Claude model ID
- `TITAN_EMBEDDING_MODEL_ID`: Titan embedding model ID

### AWS Permissions

Lambda execution role needs:
- S3: Read/Write access to documents bucket
- Textract: AnalyzeDocument
- Bedrock: InvokeModel, Retrieve (Knowledge Base)
- Transcribe: StartTranscriptionJob, GetTranscriptionJob
- Translate: TranslateText
- Polly: SynthesizeSpeech
- RDS: Connect to Aurora cluster

## Monitoring

### CloudWatch Logs

Lambda logs are automatically sent to CloudWatch:
- `/aws/lambda/jansahayak-document-processor`
- `/aws/lambda/jansahayak-query-engine`
- `/aws/lambda/jansahayak-voice-interface`

### Metrics

Key metrics to monitor:
- Lambda invocation count and duration
- API Gateway 4xx/5xx errors
- S3 bucket size
- Aurora connections and query performance
- Bedrock API latency

## Troubleshooting

### Common Issues

1. **Lambda timeout**: Increase timeout in Lambda configuration
2. **Out of memory**: Increase memory allocation
3. **Database connection failed**: Check VPC configuration and security groups
4. **Bedrock throttling**: Implement exponential backoff (already included)
5. **S3 access denied**: Verify IAM role permissions

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Production Checklist

- [ ] Enable S3 versioning and lifecycle policies
- [ ] Configure Aurora backup retention
- [ ] Set up CloudWatch alarms
- [ ] Enable API Gateway throttling
- [ ] Configure WAF rules
- [ ] Set up VPC endpoints for AWS services
- [ ] Enable encryption at rest for all data
- [ ] Configure CORS properly for production domains
- [ ] Set up CI/CD pipeline
- [ ] Document runbooks for common operations
