"""Lambda handler for voice interface."""
from mangum import Mangum
from ..api.app import app

# Create Lambda handler
# Timeout: 30 seconds
# Memory: 1536MB
handler = Mangum(app, lifespan="off")
