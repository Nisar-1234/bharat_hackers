"""Configuration management for Jansahayak."""
import os
from dataclasses import dataclass


@dataclass
class AWSConfig:
    """AWS service configuration."""
    region: str
    account_id: str
    s3_bucket: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    knowledge_base_id: str
    bedrock_model_id: str
    titan_embedding_model_id: str


def load_config() -> AWSConfig:
    """Load configuration from environment variables."""
    return AWSConfig(
        region=os.getenv("AWS_REGION", "us-east-1"),
        account_id=os.getenv("AWS_ACCOUNT_ID", ""),
        s3_bucket=os.getenv("S3_BUCKET_NAME", "jansahayak-documents"),
        db_host=os.getenv("DB_HOST", ""),
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=os.getenv("DB_NAME", "jansahayak"),
        db_user=os.getenv("DB_USER", "admin"),
        db_password=os.getenv("DB_PASSWORD", ""),
        knowledge_base_id=os.getenv("KNOWLEDGE_BASE_ID", ""),
        bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"),
        titan_embedding_model_id=os.getenv("TITAN_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v1")
    )
