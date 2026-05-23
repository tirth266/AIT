import logging
from flask import request
from flask_cors import CORS

logger = logging.getLogger('trading_app')

def init_cors(app):
    """
    Initialize CORS with the exact production-ready setup requested.
    This configuration supports credentials and handles all routes globally.
    """
    logger.info("Initializing production-ready CORS for https://ait-flame.vercel.app")
    
    # Configure CORS globally for all routes
    CORS(
        app,
        resources={r"/*": {
            "origins": [
                "https://ait-flame.vercel.app",
                "http://localhost:5173"
            ]
        }},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )
    
    @app.before_request
    def debug_cors():
        """Log CORS-related details for debugging."""
        if request.path.startswith('/api/'):
            origin = request.headers.get('Origin')
            method = request.method
            logger.info(f"CORS Request: {method} {request.path} | Origin: {origin}")
            
            # Note: We no longer manually handle OPTIONS here.
            # Flask-CORS handles preflight requests automatically based on the configuration above.

    logger.info("CORS successfully initialized for https://ait-flame.vercel.app and http://localhost:5173")
