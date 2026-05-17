"""
Deployment Configuration for Horizontal Scaling
=================================================
Production deployment configuration for 1000+ concurrent users.
"""

import os

REDIS_CLUSTER_NODES = os.environ.get(
    'REDIS_CLUSTER_NODES',
    'redis://localhost:6379,redis://localhost:6380,redis://localhost:6381'
)

SOCKETIO_CLUSTER_MODE = os.environ.get('SOCKETIO_CLUSTER_MODE', 'true')
NODE_ID = os.environ.get('NODE_ID', 'node-1')

SOCKETIO_PING_TIMEOUT = int(os.environ.get('SOCKETIO_PING_TIMEOUT', '60'))
SOCKETIO_PING_INTERVAL = int(os.environ.get('SOCKETIO_PING_INTERVAL', '25'))

MAX_CONNECTIONS_PER_USER = int(os.environ.get('MAX_CONNECTIONS_PER_USER', '5'))
RATE_LIMIT_PER_MINUTE = int(os.environ.get('RATE_LIMIT_PER_MINUTE', '100'))

BATCH_INTERVAL_MS = int(os.environ.get('BATCH_INTERVAL_MS', '50'))
MAX_BATCH_SIZE = int(os.environ.get('MAX_BATCH_SIZE', '50'))

COMPRESSION_ENABLED = os.environ.get('COMPRESSION_ENABLED', 'true').lower() == 'true'
COMPRESSION_THRESHOLD = int(os.environ.get('COMPRESSION_THRESHOLD', '500'))

PRESENCE_TTL = int(os.environ.get('PRESENCE_TTL', '300'))
SESSION_TTL = int(os.environ.get('SESSION_TTL', '3600'))


def get_gunicorn_config():
    """Get gunicorn configuration for SocketIO workers."""
    return {
        'workers': int(os.environ.get('GUNICORN_WORKERS', '4')),
        'worker_class': 'eventlet',
        'worker_connections': int(os.environ.get('GUNICORN_WORKER_CONNECTIONS', '1000')),
        'max_requests': int(os.environ.get('GUNICORN_MAX_REQUESTS', '1000')),
        'max_requests_jitter': int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', '50')),
        'timeout': int(os.environ.get('GUNICORN_TIMEOUT', '120')),
        'keepalive': int(os.environ.get('GUNICORN_KEEPALIVE', '5')),
        'preload_app': True,
        'bind': os.environ.get('GUNICORN_BIND', '0.0.0.0:5000'),
        'accesslog': '-',
        'errorlog': '-',
        'loglevel': 'info'
    }


def get_nginx_config():
    """Get recommended nginx configuration."""
    return """
upstream socketio_cluster {
    server 127.0.0.1:5000;
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
    server 127.0.0.1:5003;
    keepalive 64;
}

server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 10M;

    location /socket.io {
        proxy_pass http://socketio_cluster;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 300s;
        proxy_send_timeout 300s;

        proxy_buffering off;
        proxy_request_buffering off;
    }

    location /api {
        proxy_pass http://socketio_cluster;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
"""


def get_docker_compose_config():
    """Get docker-compose configuration for scaling."""
    return """
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - trading_network

  redis-cluster:
    image: redis:7-alpine
    ports:
      - "6380:6379"
      - "6381:6379"
      - "6382:6379"
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf
    networks:
      - trading_network

  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - SOCKETIO_MESSAGE_QUEUE=redis://redis:6379/3
      - NODE_ID=node-1
      - GUNICORN_WORKERS=4
    depends_on:
      - redis
    networks:
      - trading_network
    deploy:
      replicas: 4

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app
    networks:
      - trading_network

volumes:
  redis_data:

networks:
  trading_network:
    driver: bridge
"""


SCALING_TARGETS = {
    '100_users': {
        'workers': 2,
        'redis_connections': 20,
        'batch_interval_ms': 50
    },
    '500_users': {
        'workers': 4,
        'redis_connections': 40,
        'batch_interval_ms': 50
    },
    '1000_users': {
        'workers': 8,
        'redis_connections': 50,
        'batch_interval_ms': 30
    },
    '2000_users': {
        'workers': 12,
        'redis_connections': 100,
        'batch_interval_ms': 20
    }
}