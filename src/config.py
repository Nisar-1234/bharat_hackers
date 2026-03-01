"""Configuration management for Jansahayak."""
import os
from dataclasses import dataclass


@dataclass
class AWSConfig:
    """AWS service configuration."""
    region: str
    account_id: str
    s3_bucket: str
    dynamodb_table_name: str
    knowledge_base_id: str
    bedrock_model_id: str
    titan_embedding_model_id: str


def load_config() -> AWSConfig:
    """Load configuration from environment variables."""
    return AWSConfig(
        region=os.getenv("AWS_REGION", "us-east-1"),
        account_id=os.getenv("AWS_ACCOUNT_ID", ""),
        s3_bucket=os.getenv("S3_BUCKET_NAME", "jansahayak-documents"),
        dynamodb_table_name=os.getenv("DYNAMODB_TABLE_NAME", "jansahayak-data"),
        knowledge_base_id=os.getenv("KNOWLEDGE_BASE_ID", ""),
        bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"),
        titan_embedding_model_id=os.getenv("TITAN_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v1"),
    )
