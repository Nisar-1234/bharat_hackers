# AWS_COMMANDS.md — Copy-Paste Commands for Windows Git Bash

All commands tested on Windows Git Bash. Run from `~/phase_hack/bharat_hackers`.

**Account ID:** 686255980320
**Region:** us-east-1 (N. Virginia)

```bash
cd ~/phase_hack/bharat_hackers
export AWS_ACCOUNT_ID=686255980320
export AWS_REGION=us-east-1
```

---

## 1. Cost Protection ✅ DONE

```bash
aws cloudwatch put-metric-alarm --alarm-name "Jansahayak-Billing-10USD" --alarm-description "Alert when estimated charges exceed 10 USD" --metric-name EstimatedCharges --namespace AWS/Billing --statistic Maximum --period 86400 --threshold 10 --comparison-operator GreaterThanThreshold --dimensions Name=Currency,Value=USD --evaluation-periods 1 --region us-east-1
```

Also set up a budget in AWS Console: **Billing → Budgets → Create budget → Cost budget → $50**

---

## 2. IAM Role & Policies ✅ DONE

### 2a. Create Lambda Role

```bash
aws iam create-role --role-name JansahayakLambdaRole --assume-role-policy-document file://lambda-trust-policy.json
```

### 2b. Attach Basic Lambda Logging

```bash
aws iam attach-role-policy --role-name JansahayakLambdaRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### 2c. Create Custom Policy

```bash
aws iam create-policy --policy-name JansahayakPolicy --policy-document file://jansahayak-policy.json
```

### 2d. Attach Custom Policy to Role

```bash
aws iam attach-role-policy --role-name JansahayakLambdaRole --policy-arn arn:aws:iam::686255980320:policy/JansahayakPolicy
```

### 2e. Verify Role

```bash
aws iam get-role --role-name JansahayakLambdaRole --query "Role.Arn" --output text
```

Expected: `arn:aws:iam::686255980320:role/JansahayakLambdaRole`

---

## 3. Amazon S3 ✅ DONE

### 3a. Create Bucket

```bash
aws s3api create-bucket --bucket jansahayak-documents-686255980320 --region us-east-1
```

### 3b. Enable Versioning

```bash
aws s3api put-bucket-versioning --bucket jansahayak-documents-686255980320 --versioning-configuration Status=Enabled
```

### 3c. Enable Encryption

```bash
aws s3api put-bucket-encryption --bucket jansahayak-documents-686255980320 --server-side-encryption-configuration "{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"AES256\"}}]}"
```

### 3d. Block Public Access

```bash
aws s3api put-public-access-block --bucket jansahayak-documents-686255980320 --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

### 3e. Create Folder Structure

```bash
aws s3api put-object --bucket jansahayak-documents-686255980320 --key raw/
aws s3api put-object --bucket jansahayak-documents-686255980320 --key processed/
aws s3api put-object --bucket jansahayak-documents-686255980320 --key kb-chunks/
aws s3api put-object --bucket jansahayak-documents-686255980320 --key audio/
```

### 3f. Add Lifecycle Rule (auto-delete audio after 7 days)

```bash
aws s3api put-bucket-lifecycle-configuration --bucket jansahayak-documents-686255980320 --lifecycle-configuration "{\"Rules\":[{\"ID\":\"DeleteOldAudio\",\"Status\":\"Enabled\",\"Filter\":{\"Prefix\":\"audio/\"},\"Expiration\":{\"Days\":7}}]}"
```

### 3g. Verify

```bash
aws s3 ls s3://jansahayak-documents-686255980320/
```

---

## 4. Amazon DynamoDB ✅ DONE

### 4a. Create Table

```bash
aws dynamodb create-table --table-name jansahayak-data --attribute-definitions AttributeName=PK,AttributeType=S AttributeName=SK,AttributeType=S AttributeName=GSI1PK,AttributeType=S AttributeName=GSI1SK,AttributeType=S --key-schema AttributeName=PK,KeyType=HASH AttributeName=SK,KeyType=RANGE --billing-mode PAY_PER_REQUEST --global-secondary-indexes "[{\"IndexName\":\"GSI1\",\"KeySchema\":[{\"AttributeName\":\"GSI1PK\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"GSI1SK\",\"KeyType\":\"RANGE\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}}]" --tags Key=Project,Value=Jansahayak
```

### 4b. Wait for Table to Be Active

```bash
aws dynamodb wait table-exists --table-name jansahayak-data
```

### 4c. Enable Point-in-Time Recovery

```bash
aws dynamodb update-continuous-backups --table-name jansahayak-data --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### 4d. Verify

```bash
aws dynamodb describe-table --table-name jansahayak-data --query "Table.TableStatus" --output text
```

Expected: `ACTIVE`

---

## 5. Amazon Bedrock ⏳ IN PROGRESS

### 5a. Model Access — NO MANUAL STEP NEEDED

Bedrock models are now automatically enabled when first invoked. The old "Model access" page has been retired.

For Anthropic models (Claude), first-time users may need to submit use case details. If you get an access error when testing, go to:
1. Bedrock Console → **Model catalog**
2. Search **Claude 3 Sonnet** → click it
3. If prompted, fill in the use case form → submit
4. Access is usually granted within minutes

### 5b. Create Knowledge Base (AWS Console)

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

### 5c. Save Knowledge Base ID

After the KB is created, copy the Knowledge Base ID from the console page (shown at the top, format like `ABCDE12345`).

```bash
export KNOWLEDGE_BASE_ID=export KNOWLEDGE_BASE_ID=RQCSEPKGME

echo "KB ID: ${KNOWLEDGE_BASE_ID}"
```
export KNOWLEDGE_BASE_ID=<paste-kb-id-here>

---

## 6. Lambda Functions

### 6a. Package the Code

```bash
cd ~/phase_hack/bharat_hackers
rm -rf lambda-package lambda_deployment.zip
mkdir lambda-package
pip install -r requirements.txt -t lambda-package/
cp -r src lambda-package/
cd lambda-package && zip -r ../lambda_deployment.zip . && cd ..
ls -lh lambda_deployment.zip
```

### 6b. Save Role ARN

```bash
export LAMBDA_ROLE_ARN=$(aws iam get-role --role-name JansahayakLambdaRole --query "Role.Arn" --output text)
echo "Role ARN: ${LAMBDA_ROLE_ARN}"
```

### 6c. Deploy Document Processor Lambda (300s timeout, 2GB)

```bash
aws lambda create-function --function-name jansahayak-document-processor --runtime python3.11 --role ${LAMBDA_ROLE_ARN} --handler src.handlers.document_handler.handler --zip-file fileb://lambda_deployment.zip --timeout 300 --memory-size 2048 --environment "Variables={AWS_REGION=us-east-1,S3_BUCKET_NAME=jansahayak-documents-686255980320,DYNAMODB_TABLE_NAME=jansahayak-data,KNOWLEDGE_BASE_ID=${KNOWLEDGE_BASE_ID},BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0,TITAN_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1}"
```

### 6d. Deploy Query Engine Lambda (15s timeout, 1GB)

```bash
aws lambda create-function --function-name jansahayak-query-engine --runtime python3.11 --role ${LAMBDA_ROLE_ARN} --handler src.handlers.query_handler.handler --zip-file fileb://lambda_deployment.zip --timeout 15 --memory-size 1024 --environment "Variables={AWS_REGION=us-east-1,S3_BUCKET_NAME=jansahayak-documents-686255980320,DYNAMODB_TABLE_NAME=jansahayak-data,KNOWLEDGE_BASE_ID=${KNOWLEDGE_BASE_ID},BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0,TITAN_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1}"
```

### 6e. Deploy Voice Interface Lambda (30s timeout, 1.5GB)

```bash
aws lambda create-function --function-name jansahayak-voice-interface --runtime python3.11 --role ${LAMBDA_ROLE_ARN} --handler src.handlers.voice_handler.handler --zip-file fileb://lambda_deployment.zip --timeout 30 --memory-size 1536 --environment "Variables={AWS_REGION=us-east-1,S3_BUCKET_NAME=jansahayak-documents-686255980320,DYNAMODB_TABLE_NAME=jansahayak-data,KNOWLEDGE_BASE_ID=${KNOWLEDGE_BASE_ID},BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0,TITAN_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1}"
```

### 6f. Verify All 3 Functions

```bash
aws lambda list-functions --query "Functions[?starts_with(FunctionName,'jansahayak')].FunctionName" --output table
```

---

## 7. API Gateway

### 7a. Create HTTP API

```bash
export API_ID=$(aws apigatewayv2 create-api --name jansahayak-api --protocol-type HTTP --cors-configuration "AllowOrigins=*,AllowMethods=GET,POST,PUT,DELETE,OPTIONS,AllowHeaders=*" --query "ApiId" --output text)
echo "API ID: ${API_ID}"
```

### 7b. Create Lambda Integration (routes all traffic to document-processor)

```bash
export INTEGRATION_ID=$(aws apigatewayv2 create-integration --api-id ${API_ID} --integration-type AWS_PROXY --integration-uri arn:aws:lambda:us-east-1:686255980320:function:jansahayak-document-processor --payload-format-version 2.0 --query "IntegrationId" --output text)
echo "Integration ID: ${INTEGRATION_ID}"
```

### 7c. Create Routes

```bash
aws apigatewayv2 create-route --api-id ${API_ID} --route-key "GET /" --target integrations/${INTEGRATION_ID}
aws apigatewayv2 create-route --api-id ${API_ID} --route-key "POST /documents/upload" --target integrations/${INTEGRATION_ID}
aws apigatewayv2 create-route --api-id ${API_ID} --route-key "GET /documents" --target integrations/${INTEGRATION_ID}
aws apigatewayv2 create-route --api-id ${API_ID} --route-key "GET /documents/{document_id}/status" --target integrations/${INTEGRATION_ID}
aws apigatewayv2 create-route --api-id ${API_ID} --route-key "POST /query/text" --target integrations/${INTEGRATION_ID}
aws apigatewayv2 create-route --api-id ${API_ID} --route-key "POST /query/voice" --target integrations/${INTEGRATION_ID}
```

### 7d. Create Prod Stage

```bash
aws apigatewayv2 create-stage --api-id ${API_ID} --stage-name prod --auto-deploy
```

### 7e. Grant API Gateway Permission to Invoke Lambda

```bash
aws lambda add-permission --function-name jansahayak-document-processor --statement-id apigateway-invoke --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:us-east-1:686255980320:${API_ID}/*/*"
```

### 7f. Get Your Live API URL

```bash
export API_ENDPOINT=$(aws apigatewayv2 get-api --api-id ${API_ID} --query "ApiEndpoint" --output text)/prod
echo "API LIVE AT: ${API_ENDPOINT}"
```

---

## 8. Create .env File

```bash
cat > ~/phase_hack/bharat_hackers/.env << EOF
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=686255980320
S3_BUCKET_NAME=jansahayak-documents-686255980320
DYNAMODB_TABLE_NAME=jansahayak-data
KNOWLEDGE_BASE_ID=${KNOWLEDGE_BASE_ID}
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
TITAN_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1
API_ENDPOINT=${API_ENDPOINT}
EOF
cat ~/phase_hack/bharat_hackers/.env
```

---

## 9. Test Endpoints

### 9a. Health Check

```bash
curl -s ${API_ENDPOINT}/
```

Expected: `{"status":"healthy","service":"Jansahayak"}`

### 9b. Upload Test PDF

```bash
curl -s -X POST "${API_ENDPOINT}/documents/upload" -F "file=@../compendium_of_govt._of_india_schemes_programmes.pdf"
```

### 9c. List Documents

```bash
curl -s "${API_ENDPOINT}/documents"
```

### 9d. Text Query (English)

```bash
curl -s -X POST "${API_ENDPOINT}/query/text" -H "Content-Type: application/json" -d "{\"query\":\"What is PM-KISAN scheme eligibility?\",\"language\":\"en\"}"
```

### 9e. Text Query (Hindi)

```bash
curl -s -X POST "${API_ENDPOINT}/query/text" -H "Content-Type: application/json" -d "{\"query\":\"प्रधानमंत्री किसान योजना के लिए पात्रता क्या है?\",\"language\":\"hi\"}"
```

### 9f. Check DynamoDB

```bash
aws dynamodb scan --table-name jansahayak-data --select COUNT
```

---

## 10. Update Lambda Code After Changes

```bash
cd ~/phase_hack/bharat_hackers
rm -rf lambda-package lambda_deployment.zip
mkdir lambda-package
pip install -r requirements.txt -t lambda-package/
cp -r src lambda-package/
cd lambda-package && zip -r ../lambda_deployment.zip . && cd ..
aws lambda update-function-code --function-name jansahayak-document-processor --zip-file fileb://lambda_deployment.zip
aws lambda update-function-code --function-name jansahayak-query-engine --zip-file fileb://lambda_deployment.zip
aws lambda update-function-code --function-name jansahayak-voice-interface --zip-file fileb://lambda_deployment.zip
```

---

## 11. Watch Logs

```bash
aws logs tail /aws/lambda/jansahayak-document-processor --follow
aws logs tail /aws/lambda/jansahayak-query-engine --follow
```

---

## 12. Cleanup (After Hackathon)

```bash
aws lambda delete-function --function-name jansahayak-document-processor
aws lambda delete-function --function-name jansahayak-query-engine
aws lambda delete-function --function-name jansahayak-voice-interface
aws apigatewayv2 delete-api --api-id ${API_ID}
aws dynamodb delete-table --table-name jansahayak-data
aws s3 rm s3://jansahayak-documents-686255980320 --recursive
aws s3api delete-bucket --bucket jansahayak-documents-686255980320
aws iam detach-role-policy --role-name JansahayakLambdaRole --policy-arn arn:aws:iam::686255980320:policy/JansahayakPolicy
aws iam detach-role-policy --role-name JansahayakLambdaRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-policy --policy-arn arn:aws:iam::686255980320:policy/JansahayakPolicy
aws iam delete-role --role-name JansahayakLambdaRole
echo "All resources deleted. Delete Bedrock Knowledge Base from console manually."
```
