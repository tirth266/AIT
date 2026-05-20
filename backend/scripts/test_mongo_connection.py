"""
MongoDB Connection Test Script
==============================
Validates the MongoDB connection URI and tests connectivity.
"""

import os
import sys
import logging
from pymongo import MongoClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('mongo_test')

if __name__ == "__main__":
    # Add backend directory to sys.path to import build_mongo_uri
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.config import build_mongo_uri

    print("-" * 50)
    print("MongoDB Connection Test")
    print("-" * 50)

    # Securely build URI using centralized logic
    mongo_uri = build_mongo_uri()
    
    print("\nAttempting connection...")
    try:
        # Avoid logging the full URI as it contains credentials
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # The hello command is cheap and confirms connectivity
        client.admin.command('hello')
        print("SUCCESS: Connected to MongoDB successfully!")
        
        # List databases to verify authentication
        db_names = client.list_database_names()
        print(f"Databases found: {db_names}")
        success = True
    except Exception as e:
        print(f"FAILURE: Could not connect to MongoDB.")
        print(f"Error Details: {str(e)}")
        success = False
    
    sys.exit(0 if success else 1)
