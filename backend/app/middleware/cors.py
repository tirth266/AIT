"""
CORS Middleware
==============
Centralized CORS configuration using Flask-CORS only.
"""

import logging
from flask import Flask
import os
from flask_cors import CORS

logger = logging.getLogger('cors_middleware')

def init_cors(app: Flask) -> None:
    """
    Initialize CORS with Flask-CORS.
    Single source of truth for CORS configuration.
    """
    raw_origins = os.environ.get('FRONTEND_URL', 'http://localhost:5173')
    allowed_origins = [origin.strip() for origin in raw_origins.split(',') if origin.strip()]

    # Local development and recommended Vercel production origin.
    default_origins = [
        'http://localhost:3000',
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'https://YOUR_VERCEL_DOMAIN.vercel.app'
    ]

    for origin in default_origins:
        if origin not in allowed_origins:
            allowed_origins.append(origin)

    CORS(app,
         resources={r"/api/*": {"origins": allowed_origins}},
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
         allow_headers=[
             'Content-Type',
             'Authorization',
             'X-Correlation-ID',
             'Accept',
             'Origin',
             'Access-Control-Request-Method',
             'Access-Control-Request-Headers'
         ],
         expose_headers=['Content-Length', 'X-Total-Count', 'X-Correlation-ID'],
         supports_credentials=True,
         max_age=3600,
         send_wildcard=False,
         vary_header=True
    )

    logger.info(f'CORS middleware configured with origins: {allowed_origins}')