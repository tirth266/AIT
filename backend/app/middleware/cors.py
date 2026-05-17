"""
CORS Middleware
==============
Configure CORS for the Flask application.
"""

from flask import Flask, request
import logging

logger = logging.getLogger('trading_app')


def init_cors(app: Flask) -> None:
    """Initialize CORS middleware."""

    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')

        if origin:
            allowed_origins = app.config.get('CORS_ORIGINS', ['*'])
            if '*' in allowed_origins or origin in allowed_origins:
                response.headers.add('Access-Control-Allow-Origin', origin)
            else:
                response.headers.add('Access-Control-Allow-Origin', allowed_origins[0])

        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Expose-Headers', 'Content-Length,X-Total-Count')

        return response

    @app.route('/api/v1/auth/login', methods=['OPTIONS'])
    @app.route('/api/v1/auth/refresh', methods=['OPTIONS'])
    def cors_preflight(*args, **kwargs):
        return '', 200

    logger.info("CORS middleware initialized")