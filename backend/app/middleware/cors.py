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
    
    # Get configuration from environment
    # Be strict: if it's production, we should have a FRONTEND_ORIGIN
    frontend_origin = os.getenv("FRONTEND_ORIGIN", "https://ait-flame.vercel.app")
    
    # Allow local development and the production frontend
    allowed_origins = [
        frontend_origin,
        "http://localhost:5173",
        "http://localhost:3000",
        "https://ait-flame.vercel.app" # Backup hardcoded origin
    ]

    logger.info(f"CORS initialized with allowed origins: {allowed_origins}")

    # 1. Configure Flask-CORS
    # We apply this globally to the app
    CORS(
        app,
        resources={
            r"/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept"],
                "supports_credentials": True,
                "expose_headers": ["Content-Type", "Authorization"],
                "max_age": 600
            }
        }
    )

    # 2. Manual Preflight Failsafe
    # This ensures that even if a route or blueprint has issues, OPTIONS requests are handled.
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            origin = request.headers.get("Origin")
            
            # Create response
            response = jsonify({"status": "preflight_ok"})
            
            # Determine which origin to allow
            if origin in allowed_origins:
                response.headers.add("Access-Control-Allow-Origin", origin)
            else:
                response.headers.add("Access-Control-Allow-Origin", frontend_origin)
                
            response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Requested-With,Accept")
            response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS,PATCH")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            response.headers.add("Access-Control-Max-Age", "600")
            
            return response, 200

    # 3. Global Header Injector (Failsafe for 4xx/5xx errors)
    @app.after_request
    def add_cors_headers(response):
        # If the header is already present (e.g. by Flask-CORS), don't duplicate it
        if "Access-Control-Allow-Origin" not in response.headers:
            origin = request.headers.get("Origin")
            if origin in allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
            else:
                response.headers["Access-Control-Allow-Origin"] = frontend_origin
        
        # Ensure credentials header is present if origin is not '*'
        if response.headers.get("Access-Control-Allow-Origin") != "*":
            response.headers["Access-Control-Allow-Credentials"] = "true"
            
        return response

    logger.info("Production-grade CORS initialized")
