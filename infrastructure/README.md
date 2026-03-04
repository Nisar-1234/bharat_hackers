# Infrastructure Setup

This directory contains infrastructure as code for deploying Jansahayak.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.0 or AWS CDK >= 2.0
- Python 3.11+

## Components

1. **S3 Buckets**: Document storage (raw uploads, processed text, kb-chunks, audio)
2. **DynamoDB**: Single-table design for document metadata, chunks, and query logs
3. **Amazon Bedrock Knowledge Base**: Vector search (OpenSearch Serverless backend)
4. **Lambda Functions**: Compute layer
5. **API Gateway**: REST API endpoints

## Deployment

### Using Terraform

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

### Using AWS CDK

```bash
cd infrastructure/cdk
npm install
cdk deploy
```

## Configuration

Update `terraform.tfvars` or `cdk.json` with your AWS account details and preferences.

## Resources Created

- S3 bucket: `jansahayak-documents-{account-id}`
- DynamoDB table: `jansahayak-data` (PAY_PER_REQUEST, GSI1 on `GSI1PK`/`GSI1SK`)
- Knowledge Base: `jansahayak-kb` (created manually in Bedrock console, not via Terraform)
- Lambda functions: `jansahayak-document-processor`, `jansahayak-query-engine`, `jansahayak-voice-interface`
- API Gateway: `jansahayak-api`
