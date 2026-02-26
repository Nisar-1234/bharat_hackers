"""Lambda handler for document processing."""
from mangum import Mangum
from ..api.app import app

# Create Lambda handler
# Timeout: 5 minutes (300 seconds)
# Memory: 2048MB
handler = Mangum(app, lifespan="off")
