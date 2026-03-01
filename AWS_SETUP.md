# AWS Setup Guide — Jansahayak

Complete deployment guide for the AWS GenAI Hackathon submission. Follow sections **in order** — cost protection is set up before any billable resources are created.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [AWS Account & CLI Setup](#2-aws-account--cli-setup)
3. [Cost Protection FIRST](#3-cost-protection-first)
4. [IAM Role & Permissions](#4-iam-role--permissions)
5. [Amazon S3](#5-amazon-s3)
6. [Amazon DynamoDB](#6-amazon-dynamodb)
7. [Amazon Bedrock](#7-amazon-bedrock)
8. [Lambda Functions](#8-lambda-functions)
9. [API Gateway](#9-api-gateway)
10. [Additional AWS AI Services](#10-additional-aws-ai-services)
11. [Environment Variables](#11-environment-variables)
12. [Test Every Endpoint](#12-test-every-endpoint)
13. [Cost Monitoring & Avoiding Charges](#13-cost-monitoring--avoiding-charges)
14. [Cleanup When Done](#14-cleanup-when-done)

---

## 1. Prerequisites

### Tools to install

```bash
# AWS CLI (Windows — run in PowerShell as Admin)
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# Python 3.11+
python --version

# Verify AWS CLI
aws --version
# Expected: aws-cli/2.x.x ...
```

### What you need before starting
- AWS account with billing enabled
- AWS hackathon credits applied (check console → Billing → Credits)
- IAM user or root credentials with AdministratorAccess (for setup only)

---

## 2. IAM User Setup (New Account — Do This First)

> **Never use root credentials for daily work.** Create an IAM admin user, then use that user's access keys for everything else.

### 2a. Enable IAM Identity Center (skip if you just want a quick IAM user)

For the hackathon, a simple IAM user with AdministratorAccess is fastest. Follow 2b below.

### 2b. Create IAM Admin User (AWS Console)

1. Log in to AWS Console as **root** at https://console.aws.amazon.com/
2. Search for **IAM** in the top search bar → click **IAM**
3. In the left sidebar, click **Users** → **Create user**
4. **User name:** `jansahayak-admin`
5. Check **Provide user access to the AWS Management Console** (optional — only if you want this user to also log into console)
   - Select **I want to create an IAM user**
   - Set a console password or auto-generate
6. Click **Next**
7. **Set permissions:**
   - Select **Attach policies directly**
   - Search for and check **AdministratorAccess**
8. Click **Next** → **Create user**
9. **Save the console sign-in URL** shown on the success page (format: `https://686255980320.signin.aws.amazon.com/console`)

### 2c. Create Access Keys for CLI

1. Go to **IAM** → **Users** → click **jansahayak-admin**
2. Click the **Security credentials** tab
3. Scroll to **Access keys** → click **Create access key**
4. Select **Command Line Interface (CLI)**
5. Check the confirmation checkbox → click **Next** → **Create access key**
6. **IMPORTANT: Copy both keys NOW** — the Secret Access Key is shown only once:
   - **Access Key ID:** `AKIA...` (copy this)
   - **Secret Access Key:** `wJal...` (copy this)
7. Click **Download .csv file** as backup → store it safely
8. Click **Done**

> **Never commit these keys to git.** They go in `~/.aws/credentials` (set up in the next step) and `.env` (which is in `.gitignore`).

### 2d. Configure AWS CLI with Your New Keys

```bash
# Verify AWS CLI is installed
aws --version
# If not installed, run in PowerShell as Admin:
# msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# Configure with the keys you just created
aws configure
# Prompts:
#   AWS Access Key ID:     [paste your AKIA... key]
#   AWS Secret Access Key: [paste your secret key]
#   Default region:        us-east-1
#   Default output format: json

# Verify it works
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDA...",
    "Account": "686255980320",
    "Arn": "arn:aws:iam::686255980320:user/jansahayak-admin"
}
```

### 2e. Set Shell Variables (used throughout this guide)

```bash
export AWS_ACCOUNT_ID=686255980320
export AWS_REGION=us-east-1
echo "Account: ${AWS_ACCOUNT_ID}  Region: ${AWS_REGION}"
```

### 2f. Secure Your Root Account (do this now, takes 2 minutes)

1. Go to **IAM** → **Dashboard** → look for **Security recommendations**
2. **Enable MFA on root account:**
   - Click your account name (top-right) → **Security credentials**
   - Under **Multi-factor authentication (MFA)** → **Assign MFA device**
   - Choose **Authenticator app** (use Google Authenticator or Authy on your phone)
   - Scan the QR code, enter two consecutive codes → **Add MFA**
3. **Stop using root** — from now on, sign in with `jansahayak-admin` at:
   `https://686255980320.signin.aws.amazon.com/console`

---

## 3. Cost Protection FIRST

> **Do this before creating any resource.** These alerts are your safety net.

### 3a. Enable billing alerts

```bash
# Turn on billing alerts (one-time, free)
aws cloudwatch put-metric-alarm \
  --alarm-name "Jansahayak-Billing-10USD" \
  --alarm-description "Alert when estimated charges exceed $10" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=Currency,Value=USD \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:${AWS_ACCOUNT_ID}:billing-alerts \
  --region us-east-1
```

### 3b. Create an AWS Budget with email alerts

Go to **AWS Console → Billing → Budgets → Create budget**:
- Budget type: **Cost budget**
- Amount: **$50** (or your credit limit)
- Alert threshold 1: **50%** → email yourself
- Alert threshold 2: **80%** → email yourself
- Alert threshold 3: **100%** → email yourself

This is the simplest way — takes 2 minutes and protects you completely.

### 3c. What costs money in this project (know before you deploy)

| Service | Charge model | Estimated cost | Risk level |
|---------|-------------|----------------|------------|
| **Bedrock Knowledge Base (OpenSearch Serverless)** | ~$0.24/OCU-hour even when idle | **$5–15/day if left on** | 🔴 HIGH |
| Amazon Bedrock (Claude 3 Sonnet) | $0.003/1K input tokens | ~$1–5 per demo | 🟡 MEDIUM |
| AWS Lambda | First 1M requests/month free | Effectively $0 | 🟢 LOW |
| Amazon S3 | $0.023/GB-month | < $1 | 🟢 LOW |
| Amazon DynamoDB | First 25 WCU/RCU free forever | $0 for hackathon | 🟢 LOW |
| Amazon Textract | $0.0015/page | < $1 for demo | 🟢 LOW |
| Amazon Transcribe | $0.024/minute | < $1 for demo | 🟢 LOW |
| Amazon Translate | $15/million chars | < $1 for demo | 🟢 LOW |
| Amazon Polly | $4/million chars | < $1 for demo | 🟢 LOW |
| API Gateway | First 1M calls/month free | $0 | 🟢 LOW |

> **Biggest risk**: The **OpenSearch Serverless** collection created by Bedrock Knowledge Base. It bills per OCU-hour even with zero traffic. Delete it immediately after the hackathon (see [Section 14](#14-cleanup-when-done)).

---

## 4. IAM Role & Permissions

> Policy JSON files are already in the repo: `lambda-trust-policy.json` and `jansahayak-policy.json`.
> Run these from `~/phase_hack/bharat_hackers`.

```bash
cd ~/phase_hack/bharat_hackers

# Create the Lambda execution role
aws iam create-role --role-name JansahayakLambdaRole --assume-role-policy-document file://lambda-trust-policy.json

# Attach basic Lambda logging
aws iam attach-role-policy --role-name JansahayakLambdaRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create custom policy with S3, DynamoDB, Bedrock, Textract, Transcribe, Translate, Polly access
aws iam create-policy --policy-name JansahayakPolicy --policy-document file://jansahayak-policy.json

# Attach custom policy to Lambda role
aws iam attach-role-policy --role-name JansahayakLambdaRole --policy-arn arn:aws:iam::686255980320:policy/JansahayakPolicy

# Verify
export LAMBDA_ROLE_ARN=$(aws iam get-role --role-name JansahayakLambdaRole --query "Role.Arn" --output text)
echo "Lambda Role ARN: ${LAMBDA_ROLE_ARN}"
```

---

## 5. Amazon S3

```bash
export S3_BUCKET=jansahayak-documents-${AWS_ACCOUNT_ID}

# Create bucket
aws s3api create-bucket \
  --bucket ${S3_BUCKET} \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket ${S3_BUCKET} \
  --versioning-configuration Status=Enabled

# Enable server-side encryption
aws s3api put-bucket-encryption \
  --bucket ${S3_BUCKET} \
  --server-side-encryption-configuration '{
    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
  }'

# Block all public access
aws s3api put-public-access-block \
  --bucket ${S3_BUCKET} \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Create folder structure
for folder in raw processed kb-chunks audio; do
  aws s3api put-object --bucket ${S3_BUCKET} --key ${folder}/
done

# Add lifecycle rule to auto-delete audio files after 7 days (saves cost)
aws s3api put-bucket-lifecycle-configuration \
  --bucket ${S3_BUCKET} \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "DeleteOldAudio",
      "Status": "Enabled",
      "Filter": {"Prefix": "audio/"},
      "Expiration": {"Days": 7}
    }]
  }'

echo "✅ S3 bucket ready: ${S3_BUCKET}"
aws s3 ls s3://${S3_BUCKET}
```

---

## 6. Amazon DynamoDB

```bash
# Create single-table with GSI for status queries
aws dynamodb create-table \
  --table-name jansahayak-data \
  --attribute-definitions \
    AttributeName=PK,AttributeType=S \
    AttributeName=SK,AttributeType=S \
    AttributeName=GSI1PK,AttributeType=S \
    AttributeName=GSI1SK,AttributeType=S \
  --key-schema \
    AttributeName=PK,KeyType=HASH \
    AttributeName=SK,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --global-secondary-indexes '[{
    "IndexName": "GSI1",
    "KeySchema": [
      {"AttributeName":"GSI1PK","KeyType":"HASH"},
      {"AttributeName":"GSI1SK","KeyType":"RANGE"}
    ],
    "Projection": {"ProjectionType":"ALL"}
  }]' \
  --tags Key=Project,Value=Jansahayak

# Wait for table to be active
aws dynamodb wait table-exists --table-name jansahayak-data

# Enable point-in-time recovery (free for PAY_PER_REQUEST)
aws dynamodb update-continuous-backups \
  --table-name jansahayak-data \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

echo "✅ DynamoDB table ready"
aws dynamodb describe-table \
  --table-name jansahayak-data \
  --query "Table.TableStatus"
```

**Table design** (single-table pattern):
- Documents: `PK=DOC#<id>  SK=METADATA`
- Chunks: `PK=DOC#<id>  SK=CHUNK#001`
- Query logs: `PK=QUERY#<date>  SK=LOG#<time>#<id>`
- `GSI1` on `GSI1PK/GSI1SK` for status filtering and recent-query lookups

---

## 7. Amazon Bedrock

### 7a. Model Access — No Manual Step Needed

The "Model access" page has been **retired**. Bedrock models are now automatically enabled when first invoked in your account.

**For Anthropic models (Claude):** First-time users may need to submit use case details:
1. Bedrock Console → **Model catalog**
2. Search for **Claude 3 Sonnet** → click it
3. If prompted, fill in the use case form → submit
4. Access is usually granted within minutes

### 7b. Create the Knowledge Base (AWS Console)

> The Knowledge Base creates an OpenSearch Serverless collection automatically.
> **Remember**: this collection bills ~$0.24/OCU-hour even when idle. Delete it after the hackathon.

1. Bedrock Console → Left sidebar → **Knowledge Bases** (under "Build")
2. Click **Create knowledge base**
3. **Knowledge base name:** `jansahayak-kb`
4. **IAM role:** Select **Create and use a new service role**
5. Click **Next**
6. **Data source name:** `scheme-documents`
7. **S3 URI:** `s3://jansahayak-documents-686255980320/kb-chunks/`
8. Click **Next**
9. **Embeddings model:** Select **Titan Embeddings G1 - Text**
10. **Vector database:** Select **Quick create a new vector store**
11. Click **Next** → Review → **Create knowledge base**
12. Wait 5-10 minutes for creation to complete

```bash
# After creation, save the Knowledge Base ID from the console page
export KNOWLEDGE_BASE_ID=<paste-kb-id-here>
echo "KNOWLEDGE_BASE_ID=${KNOWLEDGE_BASE_ID}"
```

---

## 8. Lambda Functions

### 8a. Package the code

```bash
cd /path/to/bharat_hackers

# Create clean package directory
rm -rf lambda-package && mkdir lambda-package

# Install dependencies into package folder
pip install -r requirements.txt -t lambda-package/

# Copy source code
cp -r src lambda-package/

# Create ZIP
cd lambda-package && zip -r ../lambda_deployment.zip . && cd ..
ls -lh lambda_deployment.zip
```

### 8b. Deploy the three Lambda functions

```bash
# Common environment variables for all functions
ENV_VARS="AWS_REGION=${AWS_REGION},\
S3_BUCKET_NAME=${S3_BUCKET},\
DYNAMODB_TABLE_NAME=jansahayak-data,\
KNOWLEDGE_BASE_ID=${KNOWLEDGE_BASE_ID},\
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0,\
TITAN_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1"

# 1. Document Processor — heavy OCR work, needs 5 min + 2GB
aws lambda create-function \
  --function-name jansahayak-document-processor \
  --runtime python3.11 \
  --role ${LAMBDA_ROLE_ARN} \
  --handler src.handlers.document_handler.handler \
  --zip-file fileb://lambda_deployment.zip \
  --timeout 300 \
  --memory-size 2048 \
  --environment Variables="{${ENV_VARS}}"

# 2. Query Engine — fast response needed
aws lambda create-function \
  --function-name jansahayak-query-engine \
  --runtime python3.11 \
  --role ${LAMBDA_ROLE_ARN} \
  --handler src.handlers.query_handler.handler \
  --zip-file fileb://lambda_deployment.zip \
  --timeout 15 \
  --memory-size 1024 \
  --environment Variables="{${ENV_VARS}}"

# 3. Voice Interface — transcription can take ~30s
aws lambda create-function \
  --function-name jansahayak-voice-interface \
  --runtime python3.11 \
  --role ${LAMBDA_ROLE_ARN} \
  --handler src.handlers.voice_handler.handler \
  --zip-file fileb://lambda_deployment.zip \
  --timeout 30 \
  --memory-size 1536 \
  --environment Variables="{${ENV_VARS}}"

echo "✅ All Lambda functions created"
aws lambda list-functions --query "Functions[?starts_with(FunctionName,'jansahayak')].FunctionName"
```

### 8c. Update functions after code changes

```bash
# Rebuild ZIP and update all three
cd lambda-package && zip -r ../lambda_deployment.zip . && cd ..

for func in document-processor query-engine voice-interface; do
  aws lambda update-function-code \
    --function-name jansahayak-${func} \
    --zip-file fileb://lambda_deployment.zip
  echo "Updated: jansahayak-${func}"
done
```

---

## 9. API Gateway

```bash
# Create HTTP API (faster + cheaper than REST API)
export API_ID=$(aws apigatewayv2 create-api \
  --name jansahayak-api \
  --protocol-type HTTP \
  --cors-configuration \
    AllowOrigins='["*"]',AllowMethods='["GET","POST","PUT","DELETE","OPTIONS"]',AllowHeaders='["*"]' \
  --query "ApiId" --output text)

echo "API ID: ${API_ID}"

# Create Lambda integrations
for func in document-processor query-engine voice-interface; do
  FUNC_ARN="arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:jansahayak-${func}"
  INT_ID=$(aws apigatewayv2 create-integration \
    --api-id ${API_ID} \
    --integration-type AWS_PROXY \
    --integration-uri ${FUNC_ARN} \
    --payload-format-version 2.0 \
    --query "IntegrationId" --output text)
  echo "Integration for ${func}: ${INT_ID}"
done

# Get integration IDs to create routes (reuse the last INT_ID for simplicity —
# in production each route would point to its specific function)
# For hackathon: route everything through one integration (the query engine handles routing)

# Create routes
DOC_INT=$(aws apigatewayv2 get-integrations --api-id ${API_ID} \
  --query "Items[0].IntegrationId" --output text)

aws apigatewayv2 create-route --api-id ${API_ID} \
  --route-key 'GET /' --target integrations/${DOC_INT}
aws apigatewayv2 create-route --api-id ${API_ID} \
  --route-key 'POST /documents/upload' --target integrations/${DOC_INT}
aws apigatewayv2 create-route --api-id ${API_ID} \
  --route-key 'GET /documents' --target integrations/${DOC_INT}
aws apigatewayv2 create-route --api-id ${API_ID} \
  --route-key 'GET /documents/{document_id}/status' --target integrations/${DOC_INT}
aws apigatewayv2 create-route --api-id ${API_ID} \
  --route-key 'POST /query/text' --target integrations/${DOC_INT}
aws apigatewayv2 create-route --api-id ${API_ID} \
  --route-key 'POST /query/voice' --target integrations/${DOC_INT}

# Create prod stage with auto-deploy
aws apigatewayv2 create-stage \
  --api-id ${API_ID} \
  --stage-name prod \
  --auto-deploy

# Grant API Gateway permission to invoke each Lambda
for func in document-processor query-engine voice-interface; do
  aws lambda add-permission \
    --function-name jansahayak-${func} \
    --statement-id apigateway-prod-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${AWS_REGION}:${AWS_ACCOUNT_ID}:${API_ID}/*/*"
done

# Get your live API URL
export API_ENDPOINT=$(aws apigatewayv2 get-api \
  --api-id ${API_ID} --query "ApiEndpoint" --output text)

echo "✅ API live at: ${API_ENDPOINT}/prod"
echo "API_ENDPOINT=${API_ENDPOINT}/prod" >> .env
```

---

## 10. Additional AWS AI Services

These require **no setup** — they work automatically once IAM permissions are attached:

| Service | Auto-available | Verify with |
|---------|---------------|-------------|
| Amazon Textract | ✅ | `aws textract detect-document-text --document '{"S3Object":{"Bucket":"...","Name":"..."}}' --region us-east-1` |
| Amazon Transcribe | ✅ | `aws transcribe list-transcription-jobs --region us-east-1` |
| Amazon Translate | ✅ | `aws translate translate-text --text "Hello" --source-language-code en --target-language-code hi --region us-east-1` |
| Amazon Polly | ✅ | `aws polly describe-voices --language-code hi-IN --region us-east-1` |

---

## 11. Environment Variables

Create your `.env` file from `.env.example` and fill in every value:

```bash
cp .env.example .env
```

Your completed `.env` should look like this:

```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=<your-12-digit-account-id>
S3_BUCKET_NAME=jansahayak-documents-<your-account-id>
DYNAMODB_TABLE_NAME=jansahayak-data
KNOWLEDGE_BASE_ID=<bedrock-kb-id-from-console>
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
TITAN_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1
API_ENDPOINT=https://<api-id>.execute-api.us-east-1.amazonaws.com/prod
```

Verify everything is filled:
```bash
grep -E "^[A-Z_]+=<|=$" .env && echo "⚠️  Some values not filled" || echo "✅ .env looks complete"
```

---

## 12. Test Every Endpoint

Run all checks before submitting:

```bash
# Load your API endpoint
source .env

# ── Health check ──────────────────────────────────────────────────────────────
echo "--- Health Check ---"
curl -s ${API_ENDPOINT}/ | python3 -m json.tool

# ── Upload a document ────────────────────────────────────────────────────────
echo "--- Upload Document ---"
curl -s -X POST "${API_ENDPOINT}/documents/upload" \
  -F "file=@/path/to/sample-scheme.pdf" | python3 -m json.tool

# Save the document_id from the response
export DOC_ID=<paste-document_id-from-above>

# ── Check document status ─────────────────────────────────────────────────────
echo "--- Document Status ---"
curl -s "${API_ENDPOINT}/documents/${DOC_ID}/status" | python3 -m json.tool

# ── List documents ────────────────────────────────────────────────────────────
echo "--- List Documents ---"
curl -s "${API_ENDPOINT}/documents" | python3 -m json.tool

# ── Text query (English) ──────────────────────────────────────────────────────
echo "--- Text Query (English) ---"
curl -s -X POST "${API_ENDPOINT}/query/text" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the eligibility criteria?", "language": "en"}' \
  | python3 -m json.tool

# ── Text query (Hindi) ───────────────────────────────────────────────────────
echo "--- Text Query (Hindi) ---"
curl -s -X POST "${API_ENDPOINT}/query/text" \
  -H "Content-Type: application/json" \
  -d '{"query": "प्रधानमंत्री किसान योजना के लिए पात्रता क्या है?", "language": "hi"}' \
  | python3 -m json.tool

# ── Verify DynamoDB has data ──────────────────────────────────────────────────
echo "--- DynamoDB Records ---"
aws dynamodb scan \
  --table-name jansahayak-data \
  --select COUNT \
  --query "Count"

# ── Check Lambda logs ─────────────────────────────────────────────────────────
echo "--- Recent Lambda Logs ---"
aws logs tail /aws/lambda/jansahayak-query-engine --since 5m
```

All six endpoints passing = you are ready to submit.

---

## 13. Cost Monitoring & Avoiding Charges

### Check your current bill

```bash
# Current month cost by service
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query "ResultsByTime[0].Groups[?Metrics.UnblendedCost.Amount>'0.01'].[Keys[0],Metrics.UnblendedCost.Amount]" \
  --output table
```

### Check if credits are being used

```bash
# View applied credits and remaining balance
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics "UnblendedCost" "AmortizedCost" \
  --query "ResultsByTime[0].Total"
```

### Daily habit: watch the three biggest spenders

```bash
# How much has Bedrock cost today?
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-%d),End=$(date -d "+1 day" +%Y-%m-%d) \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Bedrock"]}}' \
  --query "ResultsByTime[0].Total.UnblendedCost.Amount" \
  --output text

# OpenSearch Serverless (used by Bedrock KB) — biggest surprise bill risk
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-%d),End=$(date -d "+1 day" +%Y-%m-%d) \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon OpenSearch Service"]}}' \
  --query "ResultsByTime[0].Total.UnblendedCost.Amount" \
  --output text
```

### Rules to avoid surprise charges

1. **Do not leave OpenSearch Serverless running.** Delete the Bedrock KB when you are not actively testing — it costs ~$5/day idle. Re-create it from the same S3 data in minutes.
2. **Use on-demand Bedrock** (not provisioned throughput). On-demand bills per call; provisioned bills per hour.
3. **Lambda is effectively free** for hackathon usage — do not worry about it.
4. **DynamoDB PAY_PER_REQUEST** = $0 until you hit significant traffic.
5. **Set S3 lifecycle rules** (already done in Section 5) — auto-deletes audio after 7 days.
6. **Don't keep large files in S3** unnecessarily — costs $0.023/GB/month.
7. Check billing **every morning** during the hackathon. Takes 30 seconds.

---

## 14. Cleanup When Done

Run this after the hackathon to stop all charges:

```bash
# ── Delete Lambda functions ───────────────────────────────────────────────────
for func in document-processor query-engine voice-interface; do
  aws lambda delete-function --function-name jansahayak-${func}
done

# ── Delete API Gateway ────────────────────────────────────────────────────────
aws apigatewayv2 delete-api --api-id ${API_ID}

# ── Delete DynamoDB table ─────────────────────────────────────────────────────
aws dynamodb delete-table --table-name jansahayak-data

# ── Empty and delete S3 bucket ────────────────────────────────────────────────
aws s3 rm s3://${S3_BUCKET} --recursive
aws s3api delete-bucket --bucket ${S3_BUCKET}

# ── Delete IAM resources ──────────────────────────────────────────────────────
aws iam detach-role-policy \
  --role-name JansahayakLambdaRole \
  --policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/JansahayakPolicy
aws iam detach-role-policy \
  --role-name JansahayakLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-policy \
  --policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/JansahayakPolicy
aws iam delete-role --role-name JansahayakLambdaRole

# ── Delete Bedrock Knowledge Base (AWS Console) ───────────────────────────────
# Bedrock Console → Knowledge bases → jansahayak-kb → Delete
# This also deletes the OpenSearch Serverless collection (stops the biggest charge)

echo "✅ All resources deleted. No further charges."
```

> **Most important cleanup step**: Delete the Bedrock Knowledge Base and its OpenSearch Serverless collection from the AWS Console. This is the one resource that cannot be cleanly deleted via a simple CLI command and is the source of the largest ongoing costs.

---

## Quick Reference

```bash
# Rebuild and redeploy code after changes
cd lambda-package && zip -r ../lambda_deployment.zip . && cd ..
for func in document-processor query-engine voice-interface; do
  aws lambda update-function-code \
    --function-name jansahayak-${func} \
    --zip-file fileb://lambda_deployment.zip
done

# Tail logs live during testing
aws logs tail /aws/lambda/jansahayak-document-processor --follow
aws logs tail /aws/lambda/jansahayak-query-engine --follow

# Check what's in DynamoDB
aws dynamodb scan --table-name jansahayak-data --limit 5

# Check S3 storage usage
aws s3 ls s3://${S3_BUCKET} --recursive --human-readable --summarize | tail -2
```
