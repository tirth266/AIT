import os
from flask_cors import CORS

def init_cors(app):
    raw_origins = os.getenv("FRONTEND_URL", "")
    allowed_origins = [origin.strip() for origin in raw_origins.split(',') if origin.strip()]
    if not allowed_origins:
        raise RuntimeError(
            'FRONTEND_URL is not set. Set FRONTEND_URL to your frontend deployment URL(s) before starting the backend.'
        )

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": allowed_origins
            }
        },
        supports_credentials=True
    )
