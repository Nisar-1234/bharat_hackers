"""Lambda handler for query processing."""
from mangum import Mangum
from ..api.app import app

# Create Lambda handler
# Timeout: 15 seconds
# Memory: 1024MB
handler = Mangum(app, lifespan="off")
