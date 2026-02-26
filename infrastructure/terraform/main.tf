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

# Aurora PostgreSQL Cluster
resource "aws_rds_cluster" "jansahayak" {
  cluster_identifier      = "jansahayak-db"
  engine                  = "aurora-postgresql"
  engine_mode             = "provisioned"
  engine_version          = "15.3"
  database_name           = "jansahayak"
  master_username         = var.db_username
  master_password         = var.db_password
  backup_retention_period = 7
  preferred_backup_window = "03:00-04:00"
  skip_final_snapshot     = var.environment == "dev"
  
  serverlessv2_scaling_configuration {
    max_capacity = 2.0
    min_capacity = 0.5
  }
  
  tags = {
    Name        = "Jansahayak DB"
    Environment = var.environment
  }
}

resource "aws_rds_cluster_instance" "jansahayak" {
  identifier         = "jansahayak-db-instance"
  cluster_identifier = aws_rds_cluster.jansahayak.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.jansahayak.engine
  engine_version     = aws_rds_cluster.jansahayak.engine_version
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
resource "aws_lambda_function" "document_processor" {
  filename      = "lambda_deployment.zip"
  function_name = "jansahayak-document-processor"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "src.handlers.document_handler.handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 2048
  
  environment {
    variables = {
      S3_BUCKET_NAME     = aws_s3_bucket.documents.id
      DB_HOST            = aws_rds_cluster.jansahayak.endpoint
      DB_NAME            = aws_rds_cluster.jansahayak.database_name
      KNOWLEDGE_BASE_ID  = var.knowledge_base_id
    }
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
    variables = {
      S3_BUCKET_NAME     = aws_s3_bucket.documents.id
      DB_HOST            = aws_rds_cluster.jansahayak.endpoint
      DB_NAME            = aws_rds_cluster.jansahayak.database_name
      KNOWLEDGE_BASE_ID  = var.knowledge_base_id
    }
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
    variables = {
      S3_BUCKET_NAME     = aws_s3_bucket.documents.id
      DB_HOST            = aws_rds_cluster.jansahayak.endpoint
      DB_NAME            = aws_rds_cluster.jansahayak.database_name
      KNOWLEDGE_BASE_ID  = var.knowledge_base_id
    }
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

output "db_endpoint" {
  value = aws_rds_cluster.jansahayak.endpoint
}

data "aws_caller_identity" "current" {}
