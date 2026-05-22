import logging
from flask import request, jsonify
from flask_cors import CORS

logger = logging.getLogger('trading_app')

def init_cors(app):
    """
    Initialize CORS with explicit origins and production-safe settings.
    Handles both REST API and global preflight requirements.
    """
    import os
    frontend_origin = os.getenv("FRONTEND_ORIGIN", "https://ait-flame.vercel.app")
    allowed_origins = [frontend_origin, "http://localhost:5173"]

    # 1. Configure Flask-CORS for production
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": allowed_origins
            }
        },
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # 2. Add global OPTIONS handler for robust preflight support
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            logger.info(f"Handling preflight OPTIONS request from: {request.origin}")
            response = jsonify({"status": "ok"})
            
            # Use dynamic origin if it's one of our allowed origins
            origin = request.headers.get("Origin")
            
            if origin in allowed_origins:
                response.headers.add("Access-Control-Allow-Origin", origin)
            else:
                # Fallback to requested production domain
                response.headers.add("Access-Control-Allow-Origin", frontend_origin)
                
            response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
            response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response, 200

    # 3. Ensure consistent CORS headers for every response
    @app.after_request
    def after_request(response):
        origin = request.headers.get("Origin")
        
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        else:
            response.headers["Access-Control-Allow-Origin"] = frontend_origin
            
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        # Log outgoing CORS headers for debugging
        if "/api/" in request.path:
            logger.debug(f"CORS response for {request.path}: {response.headers.get('Access-Control-Allow-Origin')}")
            
        return response

    logger.info("Production-grade CORS and Preflight handlers initialized")
