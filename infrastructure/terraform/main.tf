terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 Bucket for documents
resource "aws_s3_bucket" "documents" {
  bucket = "jansahayak-documents-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name        = "Jansahayak Documents"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# DynamoDB Table (single-table design)
resource "aws_dynamodb_table" "jansahayak" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  tags = {
    Name        = "Jansahayak Data"
    Environment = var.environment
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_execution" {
  name = "jansahayak-lambda-execution"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda Functions
locals {
  lambda_env = {
    S3_BUCKET_NAME      = aws_s3_bucket.documents.id
    DYNAMODB_TABLE_NAME = aws_dynamodb_table.jansahayak.name
    KNOWLEDGE_BASE_ID   = var.knowledge_base_id
    AWS_ACCOUNT_ID      = data.aws_caller_identity.current.account_id
  }
}

resource "aws_lambda_function" "document_processor" {
  filename      = "lambda_deployment.zip"
  function_name = "jansahayak-document-processor"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "src.handlers.document_handler.handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 2048

  environment {
    variables = local.lambda_env
  }
}

resource "aws_lambda_function" "query_engine" {
  filename      = "lambda_deployment.zip"
  function_name = "jansahayak-query-engine"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "src.handlers.query_handler.handler"
  runtime       = "python3.11"
  timeout       = 15
  memory_size   = 1024

  environment {
    variables = local.lambda_env
  }
}

resource "aws_lambda_function" "voice_interface" {
  filename      = "lambda_deployment.zip"
  function_name = "jansahayak-voice-interface"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "src.handlers.voice_handler.handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 1536

  environment {
    variables = local.lambda_env
  }
}

# API Gateway
resource "aws_apigatewayv2_api" "jansahayak" {
  name          = "jansahayak-api"
  protocol_type = "HTTP"
  
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE"]
    allow_headers = ["*"]
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.jansahayak.id
  name        = "$default"
  auto_deploy = true
}

# Outputs
output "api_endpoint" {
  value = aws_apigatewayv2_api.jansahayak.api_endpoint
}

output "s3_bucket" {
  value = aws_s3_bucket.documents.id
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.jansahayak.name
}

data "aws_caller_identity" "current" {}
