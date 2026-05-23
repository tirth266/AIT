import logging
from flask import request, jsonify
from flask_cors import CORS

logger = logging.getLogger('trading_app')

def init_cors(app):
    """
    Initialize CORS with a robust production-ready setup.
    Handles all routes globally and includes explicit OPTIONS handling for compatibility.
    """
    logger.info("Initializing robust CORS for AIT Trading Platform")
    
    # Configure CORS globally for all routes
    CORS(
        app,
        origins=[
            "https://ait-flame.vercel.app",
            "http://localhost:5173"
        ],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=True
    )
    
    @app.before_request
    def handle_options():
        """Explicitly handle OPTIONS preflight requests for maximum compatibility."""
        if request.method == "OPTIONS":
            response = jsonify({})
            origin = request.headers.get('Origin')
            
            # Use dynamic origin if it's in our allowed list
            allowed_origins = ["https://ait-flame.vercel.app", "http://localhost:5173"]
            if origin in allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
            else:
                response.headers["Access-Control-Allow-Origin"] = "https://ait-flame.vercel.app"
                
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.status_code = 200
            return response

    @app.after_request
    def add_cors_headers(response):
        """Ensure CORS headers are present on all responses."""
        origin = request.headers.get('Origin')
        allowed_origins = ["https://ait-flame.vercel.app", "http://localhost:5173"]
        
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            
        return response

    logger.info("CORS successfully initialized with explicit preflight handling")
