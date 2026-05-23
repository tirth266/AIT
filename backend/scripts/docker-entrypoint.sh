#!/bin/sh
echo "=== DOCKER CONTAINER STARTING ==="
echo "MONGO_URI present: $([ -n "$MONGO_URI" ] && echo YES || echo NO)"
python -c "
from pymongo import MongoClient
import os
uri = os.environ.get('MONGO_URI')
if not uri:
    print('[ENTRYPOINT] MONGO_URI is NOT set')
else:
    try:
        c = MongoClient(uri, serverSelectionTimeoutMS=5000)
        c.admin.command('ping')
        print('[ENTRYPOINT] MongoDB ping SUCCESS')
    except Exception as e:
        print(f'[ENTRYPOINT] MongoDB ping FAILED: {e}')
"
exec "$@"
