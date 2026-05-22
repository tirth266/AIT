import logging
from flask import request, jsonify
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
    
    @app.before_request
    def debug_cors():
        """Log CORS-related details for debugging."""
        if request.path.startswith('/api/'):
            origin = request.headers.get('Origin')
            method = request.method
            logger.info(f"CORS Request: {method} {request.path} | Origin: {origin}")
            
            # Global OPTIONS bypass for preflight
            if method == "OPTIONS":
                logger.info(f"Handling global OPTIONS preflight for {request.path}")
                response = app.make_default_options_response()
                # Flask-CORS will still wrap this response if it matches the resources
                return response

    logger.info("CORS successfully initialized for https://ait-flame.vercel.app and http://localhost:5173")
