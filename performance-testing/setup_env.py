"""
Environment Setup Script
Creates .env file and validates test environment
"""

import os
import sys


DEFAULT_ENV = """
# Trading Platform Performance Testing Environment
# Copy this to .env and adjust values as needed

# API Configuration
BASE_URL=http://localhost:3000/api
WS_URL=ws://localhost:8080/ws

# MongoDB Configuration
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=trading_platform
MONGO_URL=mongodb://localhost:27017

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Test Configuration
LOCUST_HOST=http://localhost:3000
LOCUST_PORT=8089
K6_VUS=100
K6_DURATION=30m

# Test Targets
TARGET_WS_CONNECTIONS=1000
TARGET_TICK_THROUGHPUT=50000
TARGET_WS_LATENCY_MS=20
TARGET_STRATEGY_LATENCY_MS=10
TARGET_ORDER_LATENCY_MS=100

# Reporting
REPORT_DIR=./reports
RESULTS_DIR=./results
"""


def create_env_file():
    """Create .env file with default values"""
    env_file = ".env"

    if os.path.exists(env_file):
        response = input(".env already exists. Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Aborted. Existing .env preserved.")
            return

    with open(env_file, 'w') as f:
        f.write(DEFAULT_ENV)

    print(f"Created {env_file} with default configuration")
    print("Edit the file to match your environment")


def validate_environment():
    """Validate test environment"""
    print("\n=== Environment Validation ===\n")

    checks_passed = 0
    checks_failed = 0

    # Check Python version
    if sys.version_info >= (3, 8):
        print("[PASS] Python version: {}.{}.{}".format(*sys.version_info[:3]))
        checks_passed += 1
    else:
        print("[FAIL] Python 3.8+ required")
        checks_failed += 1

    # Check required packages
    required_packages = [
        "locust",
        "pymongo",
        "redis",
        "requests",
        "psutil"
    ]

    for package in required_packages:
        try:
            __import__(package)
            print(f"[PASS] Package: {package}")
            checks_passed += 1
        except ImportError:
            print(f"[FAIL] Package not found: {package}")
            checks_failed += 1

    # Check environment variables
    env_vars = ["BASE_URL", "WS_URL"]
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"[INFO] {var}={value}")
        else:
            print(f"[WARN] {var} not set (using defaults)")

    # Check connectivity (placeholder)
    print("\n[INFO] To check connectivity:")
    print("  - Test API: curl $BASE_URL/health")
    print("  - Test WebSocket: wscat -c $WS_URL")
    print("  - Test MongoDB: mongosh $MONGO_URL")
    print("  - Test Redis: redis-cli -h $REDIS_HOST")

    print(f"\n=== Results: {checks_passed} passed, {checks_failed} failed ===")

    return checks_failed == 0


def print_status():
    """Print setup status"""
    print("""
Trading Platform Performance Testing Framework
=================================================

Quick Start:
1. Create environment: python setup_env.py --create
2. Validate setup:   python setup_env.py --validate
3. Run tests:        python run_tests.py --all

Documentation: See README.md
    """)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--create":
            create_env_file()
        elif sys.argv[1] == "--validate":
            if not validate_environment():
                sys.exit(1)
        else:
            print("Unknown option:", sys.argv[1])
            print("Usage: python setup_env.py [--create|--validate]")
    else:
        print_status()