"""Error handling and response formatting."""
import logging
from typing import Dict, Any
from fastapi import HTTPException
from fastapi.responses import JSONResponse


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorCategory:
    """Error categories with HTTP status codes and user messages."""
    
    INVALID_INPUT = {
        "status_code": 400,
        "message": "Invalid input provided"
    }
    
    FILE_TOO_LARGE = {
        "status_code": 413,
        "message": "File exceeds 50MB limit"
    }
    
    UNSUPPORTED_FORMAT = {
        "status_code": 415,
        "message": "Unsupported file type"
    }
    
    DOCUMENT_NOT_FOUND = {
        "status_code": 404,
        "message": "Document not found"
    }
    
    TRANSCRIPTION_FAILED = {
        "status_code": 422,
        "message": "Could not transcribe audio. Please try again with clearer audio."
    }
    
    SERVICE_UNAVAILABLE = {
        "status_code": 503,
        "message": "Service temporarily unavailable. Please try again."
    }
    
    INTERNAL_ERROR = {
        "status_code": 500,
        "message": "An unexpected error occurred"
    }


def format_error_response(
    error: Exception,
    include_details: bool = False
) -> Dict[str, Any]:
    """
    Format error for user-facing response.
    
    Args:
        error: The exception that occurred
        include_details: Whether to include error details (for debugging)
    
    Returns:
        Dictionary with error information
    """
    error_type = type(error).__name__
    
    # Map exception types to error categories
    if "FileTooLarge" in error_type:
        category = ErrorCategory.FILE_TOO_LARGE
    elif "UnsupportedFormat" in error_type:
        category = ErrorCategory.UNSUPPORTED_FORMAT
    elif "NotFound" in error_type:
        category = ErrorCategory.DOCUMENT_NOT_FOUND
    elif "Transcription" in error_type:
        # Pass through the actual transcription error message so user sees what went wrong
        return {
            "error": True,
            "message": str(error),
            "error_type": error_type
        }
    elif "ServiceUnavailable" in error_type or "Throttling" in error_type:
        category = ErrorCategory.SERVICE_UNAVAILABLE
    elif "ValidationError" in error_type:
        category = ErrorCategory.INVALID_INPUT
    else:
        category = ErrorCategory.INTERNAL_ERROR
    
    response = {
        "error": True,
        "message": category["message"],
        "error_type": error_type
    }
    
    # Only include details in development/debugging
    if include_details:
        response["details"] = str(error)
    
    return response


def log_error(
    error: Exception,
    context: Dict[str, Any] = None,
    level: str = "error"
):
    """
    Log error with context for debugging.
    
    Args:
        error: The exception that occurred
        context: Additional context (request info, user data, etc.)
        level: Log level (debug, info, warning, error)
    """
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {}
    }
    
    # Log based on level
    if level == "debug":
        logger.debug(f"Error occurred: {error_info}")
    elif level == "info":
        logger.info(f"Error occurred: {error_info}")
    elif level == "warning":
        logger.warning(f"Error occurred: {error_info}")
    else:
        logger.error(f"Error occurred: {error_info}", exc_info=True)


def create_error_response(
    error: Exception,
    context: Dict[str, Any] = None
) -> JSONResponse:
    """
    Create FastAPI error response.
    
    Args:
        error: The exception that occurred
        context: Additional context for logging
    
    Returns:
        JSONResponse with appropriate status code and message
    """
    # Log error with full details
    log_error(error, context)
    
    # Format user-facing response (no internal details)
    error_data = format_error_response(error, include_details=False)
    
    # Determine status code
    error_type = type(error).__name__
    if "FileTooLarge" in error_type:
        status_code = 413
    elif "UnsupportedFormat" in error_type:
        status_code = 415
    elif "NotFound" in error_type:
        status_code = 404
    elif "Transcription" in error_type:
        status_code = 422
    elif "ServiceUnavailable" in error_type or "Throttling" in error_type:
        status_code = 503
    elif "ValidationError" in error_type:
        status_code = 400
    else:
        status_code = 500
    
    return JSONResponse(
        status_code=status_code,
        content=error_data
    )
