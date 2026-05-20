"""
Error Handlers
=============
Register global error handlers with Flask application.
"""

import logging
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError as MarshmallowValidationError

from app.errors.base import AppError

logger = logging.getLogger('trading_app')


def register_error_handlers(app: Flask) -> None:
    """Register all error handlers with Flask application."""

    @app.before_request
    def log_request():
        logger.info(f"Incoming request: {request.method} {request.path}")

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        logger.warning(f"Application error: {error.message}")
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(MarshmallowValidationError)
    def handle_validation_error(error: MarshmallowValidationError):
        return jsonify({
            'error': 'VALIDATION_ERROR',
            'message': 'Validation failed',
            'details': error.messages
        }), 400

    @app.errorhandler(404)
    def handle_not_found(error):
        logger.warning(f"404 Not Found: {request.method} {request.path}")
        return jsonify({
            'error': 'NOT_FOUND',
            'message': f'Resource not found: {request.path}'
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        logger.warning(f"405 Method Not Allowed: {request.method} {request.path}")
        return jsonify({
            'error': 'METHOD_NOT_ALLOWED',
            'message': f'Method {request.method} not allowed for {request.path}'
        }), 405

    @app.errorhandler(500)
    def handle_internal_error(error):
        logger.error(f"Internal server error: {str(error)}", exc_info=True)
        return jsonify({
            'error': 'VALIDATION_ERROR',
            'message': 'Validation failed',
            'details': error.messages
        }), 400

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            'error': 'NOT_FOUND',
            'message': 'Resource not found'
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({
            'error': 'METHOD_NOT_ALLOWED',
            'message': 'Method not allowed'
        }), 405

    @app.errorhandler(500)
    def handle_internal_error(error):
        logger.error(f"Internal server error: {str(error)}", exc_info=True)
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': 'Internal server error'
        }), 500

    @app.errorhandler(Exception)
    def handle_unhandled_exception(error: Exception):
        if isinstance(error, HTTPException):
            return error

        logger.error(f"Unhandled exception: {str(error)}", exc_info=True)

        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': 'An unexpected error occurred'
        }), 500

    logger.info("Error handlers registered")