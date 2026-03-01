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

### 3. Deploy Infrastructure

#### Using Terraform

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

#### Manual Setup

If deploying manually:
1. Create S3 bucket: `jansahayak-documents-{account-id}`
2. Create DynamoDB table `jansahayak-data` (PAY_PER_REQUEST, PK/SK as String, GSI1 on `GSI1PK`/`GSI1SK`)
3. Create Bedrock Knowledge Base with Titan Embeddings G1 v1, S3 data source pointing to `s3://jansahayak-documents-{account-id}/kb-chunks/`
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
- `AWS_ACCOUNT_ID`: AWS account ID
- `S3_BUCKET_NAME`: S3 bucket name (e.g. `jansahayak-documents-{account-id}`)
- `DYNAMODB_TABLE_NAME`: DynamoDB table name (default: `jansahayak-data`)
- `KNOWLEDGE_BASE_ID`: Bedrock Knowledge Base ID
- `BEDROCK_MODEL_ID`: Claude model ID (default: `anthropic.claude-3-sonnet-20240229-v1:0`)
- `TITAN_EMBEDDING_MODEL_ID`: Titan embedding model ID (default: `amazon.titan-embed-text-v1`)

### AWS Permissions

Lambda execution role needs:
- S3: Read/Write on documents bucket
- DynamoDB: Read/Write on `jansahayak-data` table
- Textract: `AnalyzeDocument`, `StartDocumentTextDetection`, `GetDocumentTextDetection`
- Bedrock: `InvokeModel`, `Retrieve`, `StartIngestionJob`, `ListDataSources`
- Transcribe: `StartTranscriptionJob`, `GetTranscriptionJob`
- Translate: `TranslateText`
- Polly: `SynthesizeSpeech`

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
3. **DynamoDB access denied**: Verify IAM role has `dynamodb:GetItem`, `PutItem`, `UpdateItem`, `Query`, `Scan`, `BatchWriteItem` on the table ARN
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
