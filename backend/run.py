import eventlet
eventlet.monkey_patch()

import os
import sys
import logging
from dotenv import load_dotenv

# Set up logging for startup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('startup')

logger.info("Starting AIT Backend initialization...")

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Load environment variables
load_dotenv()

try:
    from app import create_app, socketio
    app = create_app()
    logger.info("Flask app created successfully")
except Exception as e:
    logger.error(f"Failed to create Flask app: {e}")
    import traceback
    logger.error(traceback.format_exc())
    # We must raise here so Gunicorn knows the worker failed to boot
    raise

if __name__ == "__main__":
    # Get port from environment variable for Render deployment
    port = int(os.environ.get("PORT", 5000))
    
    logger.info(f"Starting AIT Backend on port {port} via socketio.run...")
    
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False
    )
