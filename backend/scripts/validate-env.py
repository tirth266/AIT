#!/usr/bin/env python3
"""
=============================================================================
ENVIRONMENT VALIDATION SCRIPT
=============================================================================
Validates all required environment variables and their values before
starting the application. This is critical for production deployments.

Usage:
    python scripts/validate-env.py

Exit codes:
    0 - All validations passed
    1 - Validation failed
"""

import os
import sys
import re
import socket
from typing import List, Tuple, Dict


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def log_info(msg: str) -> None:
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")


def log_success(msg: str) -> None:
    print(f"{Colors.GREEN}[PASS]{Colors.NC} {msg}")


def log_warning(msg: str) -> None:
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {msg}")


def log_error(msg: str) -> None:
    print(f"{Colors.RED}[FAIL]{Colors.NC} {msg}")


class EnvironmentValidator:
    """
    Validates environment variables for production deployment.
    """

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> bool:
        """Run all validations."""
        print("\n" + "=" * 60)
        print("  ENVIRONMENT VALIDATION")
        print("=" * 60 + "\n")

        self.validate_required_secrets()
        self.validate_database_urls()
        self.validate_cors_origins()
        self.validate_rate_limits()
        self.validate_trading_config()
        self.check_development_warnings()

        self.print_results()
        return len(self.errors) == 0

    def validate_required_secrets(self) -> None:
        """Validate secret keys meet security requirements."""
        log_info("Validating secret keys...")

        # SECRET_KEY validation
        secret_key = os.environ.get('SECRET_KEY', '')
        if not secret_key:
            self.errors.append("SECRET_KEY is not set")
        elif len(secret_key) < 32:
            self.errors.append("SECRET_KEY must be at least 32 characters")
        elif secret_key in ['dev-secret-key', 'change-this-to-a-secure-random-string']:
            self.errors.append("SECRET_KEY appears to be a default value")

        # JWT_SECRET_KEY validation
        jwt_secret = os.environ.get('JWT_SECRET_KEY', '')
        if not jwt_secret:
            self.errors.append("JWT_SECRET_KEY is not set")
        elif len(jwt_secret) < 32:
            self.errors.append("JWT_SECRET_KEY must be at least 32 characters")
        elif jwt_secret in ['jwt-secret-key', 'change-this-to-a-secure-random-string']:
            self.errors.append("JWT_SECRET_KEY appears to be a default value")

        log_success("Secret keys validated")

    def validate_database_urls(self) -> None:
        """Validate database connection strings."""
        log_info("Validating database URLs...")

        # MongoDB URI validation
        mongo_uri = os.environ.get('MONGO_URI', '')

        if not mongo_uri:
            self.errors.append("MONGO_URI is not set")
        elif 'localhost' in mongo_uri and os.environ.get('FLASK_ENV') == 'production':
            self.warnings.append("MONGO_URI contains localhost - not recommended for production")
        elif not re.search(r'mongodb(\+srv)?://', mongo_uri):
            self.errors.append("MONGO_URI format is invalid")

        # Redis URL validation
        redis_url = os.environ.get('REDIS_URL', '')
        if not redis_url:
            self.errors.append("REDIS_URL is not set")
        elif not redis_url.startswith('redis://'):
            self.errors.append("REDIS_URL must start with redis://")

        log_success("Database URLs validated")

    def validate_cors_origins(self) -> None:
        """Validate CORS configuration."""
        log_info("Validating CORS configuration...")

        cors_origins = os.environ.get('CORS_ORIGINS', '*')

        if cors_origins == '*':
            self.warnings.append(
                "CORS_ORIGINS is set to '*' - This is insecure for production. "
                "Please specify explicit domains."
            )
        elif ',' in cors_origins:
            origins = [o.strip() for o in cors_origins.split(',')]
            for origin in origins:
                if not re.match(r'^https?://', origin):
                    self.warnings.append(f"CORS origin '{origin}' should include protocol (http/https)")

        log_success("CORS configuration validated")

    def validate_rate_limits(self) -> None:
        """Validate rate limiting configuration."""
        log_info("Validating rate limiting...")

        ratelimit_enabled = os.environ.get('RATELIMIT_ENABLED', 'true').lower()
        ratelimit_default = os.environ.get('RATELIMIT_DEFAULT', '100/minute')

        if ratelimit_enabled not in ['true', '1', 'yes']:
            self.warnings.append("Rate limiting is disabled")

        # Validate rate limit format
        if not re.match(r'^\d+/minute$', ratelimit_default):
            self.warnings.append(
                f"RATELIMIT_DEFAULT format is invalid: '{ratelimit_default}'. "
                "Expected format: '100/minute'"
            )

        log_success("Rate limiting validated")

    def validate_trading_config(self) -> None:
        """Validate trading-specific configuration."""
        log_info("Validating trading configuration...")

        # Trading mode
        trading_mode = os.environ.get('TRADING_MODE', 'paper')
        if trading_mode not in ['paper', 'live']:
            self.errors.append(f"Invalid TRADING_MODE: '{trading_mode}'. Must be 'paper' or 'live'")

        # Paper balance
        try:
            paper_balance = float(os.environ.get('PAPER_BALANCE', '10000'))
            if paper_balance <= 0:
                self.errors.append("PAPER_BALANCE must be positive")
        except ValueError:
            self.errors.append("PAPER_BALANCE must be a valid number")

        # Risk management
        try:
            max_daily_loss = float(os.environ.get('RISK_MAX_DAILY_LOSS_PERCENT', '5.0'))
            if max_daily_loss > 20:
                self.warnings.append(
                    f"RISK_MAX_DAILY_LOSS_PERCENT is {max_daily_loss}% - Consider using lower values"
                )
        except ValueError:
            pass

        log_success("Trading configuration validated")

    def check_development_warnings(self) -> None:
        """Check for common development-only settings in production."""
        log_info("Checking for production issues...")

        flask_env = os.environ.get('FLASK_ENV', 'production')
        if flask_env == 'development':
            self.warnings.append(
                "FLASK_ENV is 'development' - This is insecure for production"
            )

        debug = os.environ.get('FLASK_DEBUG', '0')
        if debug == '1':
            self.errors.append(
                "FLASK_DEBUG is enabled - This is a major security risk in production"
            )

        log_success("Production checks completed")

    def print_results(self) -> None:
        """Print validation results."""
        print("\n" + "=" * 60)
        print("  VALIDATION RESULTS")
        print("=" * 60 + "\n")

        if self.warnings:
            print(f"{Colors.YELLOW}WARNINGS:{Colors.NC}")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
            print()

        if self.errors:
            print(f"{Colors.RED}ERRORS:{Colors.NC}")
            for error in self.errors:
                print(f"  ✗ {error}")
            print()

        if not self.errors and not self.warnings:
            log_success("All validations passed!")
            print(f"\n{Colors.GREEN}✓ Environment is ready for production{Colors.NC}\n")
        elif not self.errors:
            log_warning("Validation passed with warnings")
            print(f"\n{Colors.YELLOW}✓ Review warnings before deploying{Colors.NC}\n")
        else:
            log_error("Validation failed")
            print(f"\n{Colors.RED}✗ Please fix errors before deploying{Colors.NC}\n")


def check_port_available(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a port is available (not in use)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result != 0
    except Exception:
        return True


def main() -> int:
    """Main entry point."""
    validator = EnvironmentValidator()

    try:
        success = validator.validate_all()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nValidation cancelled by user")
        return 130


if __name__ == '__main__':
    sys.exit(main())