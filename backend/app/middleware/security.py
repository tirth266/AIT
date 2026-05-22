"""
=============================================================================
SECURITY MIDDLEWARE
=============================================================================
Production-grade security middleware with:
- Secure HTTP headers (CSP, HSTS, etc.)
- Request validation
- SQL injection prevention
- XSS protection
- IP blocking/throttling
- Account lockout

Author: Staff Engineer
"""

import logging
import re
import time
from flask import Flask, request, jsonify, g, abort
from functools import wraps
from typing import Optional, Callable
import hashlib

logger = logging.getLogger('trading_app')


class SecurityMiddleware:
    """
    Security middleware for request validation and protection.
    """

    # Dangerous patterns to block
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|;|'|\"|%27|%22)",
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
    ]

    XSS_PATTERNS = [
        r"<script",
        r"javascript:",
        r"onerror=",
        r"onload=",
        r"alert\(",
        r"<iframe",
        r"eval\(",
        r"expression\(",
    ]

    PATHTraversal_PATTERNS = [
        r"\.\.\/",
        r"\.\.\\",
        r"%2e%2e",
        r"\/etc\/passwd",
        r"\/windows\/system32",
    ]

    def __init__(self, app: Flask = None):
        self.app = app
        self._blocked_ips = set()
        self._failed_logins = {}  # IP -> (count, first_attempt)
        self._lockout_threshold = 10  # Failed login attempts before lockout
        self._lockout_duration = 900  # 15 minutes

        if app:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize security middleware with Flask app."""
        self.app = app

        # Security headers
        @app.after_request
        def add_security_headers(response):
            """Add security headers to all responses."""
            # Prevent clickjacking
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'

            # Prevent XSS
            response.headers['X-XSS-Protection'] = '1; mode=block'

            # Prevent MIME sniffing
            response.headers['X-Content-Type-Options'] = 'nosniff'

            # HSTS (only for HTTPS - handled by reverse proxy)
            # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

            # Referrer policy
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

            # CSP (Content Security Policy) - adjust for your needs
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data: https:; "
                "connect-src 'self' wss: https:; "
                "frame-ancestors 'none';"
            )

            # Remove server identification
            response.headers['Server'] = 'Trading Platform'

            return response

        # Request validation
        @app.before_request
        def validate_request():
            """Validate incoming requests."""
            # 1. ALWAYS skip validation for OPTIONS (CORS preflight)
            if request.method == "OPTIONS":
                return None

            # 2. Skip validation for health and auth paths
            if request.path.startswith('/health') or \
               request.path.startswith('/api/v1/auth/login') or \
               request.path.startswith('/api/v1/broker/angelone/login') or \
               request.path == '/':
                return None

            # Check IP blocking
            client_ip = self._get_client_ip()
            if self._is_ip_blocked(client_ip):
                logger.warning(f"Blocked request from locked IP: {client_ip}")
                return jsonify({
                    'error': 'IP_LOCKED',
                    'message': 'Too many failed attempts. Try again later.'
                }), 403

            # Validate request method
            if not self._is_valid_method(request.method):
                return jsonify({
                    'error': 'INVALID_METHOD',
                    'message': f'Method {request.method} not allowed'
                }), 405

            # For POST/PUT requests, validate content type
            if request.method in ['POST', 'PUT', 'PATCH']:
                content_type = request.headers.get('Content-Type', '')
                if 'application/json' not in content_type and request.content_length > 0:
                    # Allow form data for auth endpoints
                    if '/auth/' not in request.path:
                        return jsonify({
                            'error': 'INVALID_CONTENT_TYPE',
                            'message': 'Content-Type must be application/json'
                        }), 415

            return None

        logger.info("Security middleware initialized")

    def _get_client_ip(self) -> str:
        """Get client IP, considering proxies."""
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        return request.remote_addr or '127.0.0.1'

    def _is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked due to failed attempts."""
        if ip in self._blocked_ips:
            return True

        if ip in self._failed_logins:
            count, first_attempt = self._failed_logins[ip]
            if count >= self._lockout_threshold:
                # Check if lockout duration has passed
                if time.time() - first_attempt < self._lockout_duration:
                    return True
                else:
                    # Lockout expired, reset
                    del self._failed_logins[ip]
        return False

    def record_failed_login(self, ip: str) -> None:
        """Record a failed login attempt."""
        current_time = time.time()

        if ip not in self._failed_logins:
            self._failed_logins[ip] = (1, current_time)
        else:
            count, first_attempt = self._failed_logins[ip]

            # Reset if more than 15 minutes since first attempt
            if current_time - first_attempt > 900:
                self._failed_logins[ip] = (1, current_time)
            else:
                new_count = count + 1
                self._failed_logins[ip] = (new_count, first_attempt)

                # Block IP if threshold exceeded
                if new_count >= self._lockout_threshold:
                    self._blocked_ips.add(ip)
                    logger.warning(f"IP {ip} locked due to failed login attempts")

    def reset_failed_logins(self, ip: str) -> None:
        """Reset failed login count on successful login."""
        if ip in self._failed_logins:
            del self._failed_logins[ip]

    def unblock_ip(self, ip: str) -> None:
        """Manually unblock an IP."""
        if ip in self._blocked_ips:
            self._blocked_ips.discard(ip)
        if ip in self._failed_logins:
            del self._failed_logins[ip]

    def _is_valid_method(self, method: str) -> bool:
        """Check if HTTP method is allowed."""
        allowed_methods = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'}
        return method.upper() in allowed_methods

    def validate_input(self, data: dict, rules: dict) -> tuple[bool, Optional[str]]:
        """
        Validate input data against rules.

        Args:
            data: Input data dictionary
            rules: Validation rules

        Returns:
            Tuple of (is_valid, error_message)
        """
        for field, rule in rules.items():
            value = data.get(field)

            # Required check
            if rule.get('required', False) and not value:
                return False, f"Field '{field}' is required"

            # Type check
            if value and 'type' in rule:
                expected_type = rule['type']
                if expected_type == 'string' and not isinstance(value, str):
                    return False, f"Field '{field}' must be a string"
                elif expected_type == 'int' and not isinstance(value, int):
                    return False, f"Field '{field}' must be an integer"
                elif expected_type == 'email' and not self._is_valid_email(value):
                    return False, f"Field '{field}' must be a valid email"

            # Length check
            if value and 'min_length' in rule and len(value) < rule['min_length']:
                return False, f"Field '{field}' must be at least {rule['min_length']} characters"
            if value and 'max_length' in rule and len(value) > rule['max_length']:
                return False, f"Field '{field}' must be at most {rule['max_length']} characters"

            # Pattern check
            if value and 'pattern' in rule:
                if not re.match(rule['pattern'], value):
                    return False, f"Field '{field}' format is invalid"

        return True, None

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def check_sql_injection(self, value: str) -> bool:
        """Check if value contains SQL injection patterns."""
        if not isinstance(value, str):
            return False

        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    def check_xss(self, value: str) -> bool:
        """Check if value contains XSS patterns."""
        if not isinstance(value, str):
            return False

        value_lower = value.lower()
        for pattern in self.XSS_PATTERNS:
            if pattern.lower() in value_lower:
                return True
        return False


# Global security middleware instance
security_middleware = None


def init_security(app: Flask) -> SecurityMiddleware:
    """Initialize security middleware."""
    global security_middleware
    security_middleware = SecurityMiddleware(app)
    return security_middleware


def get_security_middleware() -> Optional[SecurityMiddleware]:
    """Get the security middleware instance."""
    return security_middleware


# Decorators for request validation
def validate_json(fields: list):
    """
    Decorator to validate JSON request body.

    Usage:
        @validate_json(['email', 'password'])
        def login():
            ...
    """
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'error': 'INVALID_CONTENT_TYPE',
                    'message': 'Request must be JSON'
                }), 400

            data = request.get_json()
            if not data:
                return jsonify({
                    'error': 'EMPTY_REQUEST',
                    'message': 'Request body is empty'
                }), 400

            missing_fields = [field for field in fields if field not in data]
            if missing_fields:
                return jsonify({
                    'error': 'MISSING_FIELDS',
                    'message': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400

            g.request_data = data
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def sanitize_input(data: dict) -> dict:
    """
    Sanitize input data to prevent XSS and injection attacks.

    Args:
        data: Input data dictionary

    Returns:
        Sanitized data dictionary
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            # Remove potentially dangerous characters
            sanitized_value = value.replace('<', '').replace('>', '')
            sanitized_value = sanitized_value.replace('"', '').replace("'", '')
            sanitized[key] = sanitized_value.strip()
        elif isinstance(value, dict):
            sanitized[key] = sanitize_input(value)
        else:
            sanitized[key] = value

    return sanitized