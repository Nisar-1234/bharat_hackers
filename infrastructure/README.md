# Infrastructure Setup

This directory contains infrastructure as code for deploying Jansahayak.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.0 or AWS CDK >= 2.0
- Python 3.11+

## Components

1. **S3 Buckets**: Document storage
2. **Aurora PostgreSQL**: Metadata and query logs
3. **Amazon Bedrock Knowledge Base**: Vector search
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
- Aurora cluster: `jansahayak-db`
- Knowledge Base: `jansahayak-kb`
- Lambda functions: `jansahayak-document-processor`, `jansahayak-query-engine`, `jansahayak-voice-interface`
- API Gateway: `jansahayak-api`
