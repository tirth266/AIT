import logging
from flask_cors import CORS

logger = logging.getLogger('trading_app')

def init_cors(app):
    """
    Initialize CORS with the exact production-ready setup requested.
    This configuration supports credentials and handles /api/* routes.
    """
    logger.info("Initializing production-ready CORS...")
    
    CORS(
        app,
        resources={r"/api/*": {"origins": [
            "https://ait-flame.vercel.app",
            "http://localhost:5173"
        ]}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )
    
    logger.info("CORS successfully initialized for https://ait-flame.vercel.app and http://localhost:5173")
