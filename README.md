
# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

# AIT

# Stocker v2.0 - Institutional Algorithmic Trading Platform

A premium Indian stock market trading platform built with React, TypeScript, and Vite, now evolved into an institutional-grade distributed financial infrastructure.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TRADING PLATFORM v2.0                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │  Frontend   │  │   Backend   │  │   Celery    │  │    Kafka    │       │
│  │   (React)   │  │   (Flask)   │  │   Worker    │  │   Consumer  │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
│         │                │                │                │                │
│         └────────────────┼────────────────┼────────────────┘                │
│                          │                │                                 │
│                    ┌─────┴────────────────┴─────┐                            │
│                    │    KAFKA EVENT STREAMING  │                            │
│                    │  ticks | orders | trades  │                            │
│                    └────────────────────────────┘                            │
│                          │                                                  │
│  ┌─────────────┐  ┌───────┴────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  MongoDB   │  │     Redis      │  │  PostgreSQL │  │ TimescaleDB │     │
│  │ (Primary)  │  │ (Cache/Queue)  │  │ (Compliance)│  │    (OHLCV)  │     │
│  └─────────────┘  └────────────────┘  └─────────────┘  └─────────────┘     │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │              OBSERVABILITY: Prometheus | Grafana | ELK             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Core
- **Frontend**: React 18, TypeScript, Vite, Zustand
- **Backend**: Flask, Python 3.11, Celery
- **WebSocket**: Flask-SocketIO with Redis message queue

### Data Layer
- **Kafka**: Event streaming with schema registry
- **MongoDB**: Primary data store with replica sets
- **Redis**: Caching, sessions, Celery broker
- **TimescaleDB**: Time-series OHLCV data (planned)

### Infrastructure
- **Docker**: Container orchestration
- **Kubernetes**: Production deployment
- **Nginx**: Reverse proxy and load balancer

### Monitoring
- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **ELK Stack**: Log aggregation
- **Jaeger**: Distributed tracing

## Project Structure

```
├── frontend/                    # React/Vite frontend
├── backend/app/                # Flask application
│   ├── api/                    # REST API endpoints
│   ├── websocket/              # WebSocket handlers
│   ├── trading_engine/         # Trading logic
│   ├── async_engine/           # Async processing
│   ├── observability/          # Metrics & monitoring
│   └── risk_management/        # Risk controls
├── infrastructure/             # Infrastructure configs
│   ├── kafka/                  # Kafka setup
│   │   ├── schemas/            # Avro schemas
│   │   ├── topics/             # Topic configs
│   │   ├── producers/          # Producer implementations
│   │   ├── consumers/          # Consumer implementations
│   │   └── scripts/            # Topic management
│   ├── monitoring/             # Monitoring setup
│   │   ├── prometheus_metrics.py
│   │   ├── alerts/rules.yaml
│   │   └── dashboards/
│   ├── dr/                     # Disaster recovery
│   ├── security/               # Security & audit
│   │   └── audit/audit_logger.py
│   ├── brokers/                # Multi-broker infrastructure
│   └── lowlatency/            # Performance optimization
├── kubernetes/                  # K8s manifests
├── docker/                     # Docker configs
├── docs/                       # Documentation
└── SPEC.md                     # Architecture specification
```

## Quick Start

### Development

```bash
# Start all services
docker-compose up -d

# Or start with full infrastructure (includes Kafka, monitoring)
docker-compose -f docker-compose.kafka.yml up -d
docker-compose -f docker-compose.production.yml up -d
```

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/v1/auth/*` | Authentication |
| `/api/v1/orders/*` | Order management |
| `/api/v1/trades/*` | Trade history |
| `/api/v1/strategies/*` | Strategy management |
| `/api/v1/market/*` | Market data |
| `/api/v1/health` | Health check |

### WebSocket Events

- `tick`: Real-time tick data
- `order`: Order status updates
- `trade`: Trade execution events
- `signal`: Strategy signals

## Kafka Event Streaming

### Topics

| Topic | Partitions | Retention | Purpose |
|-------|------------|------------|---------|
| `ticks.raw` | 16 | 7 days | Market ticks |
| `orders.created` | 8 | 90 days | Order creation |
| `trades.executed` | 8 | 7 years | Trade execution |
| `risk.events` | 4 | 30 days | Risk alerts |
| `audit.trading` | 4 | 10 years | SEBI audit trail |

### Schemas (Avro)

- `tick.v1.avsc` - Market tick data
- `order.v1.avsc` - Order events
- `trade.v1.avsc` - Trade execution
- `signal.v1.avsc` - Trading signals

### Consumer Groups

- `tick-processor` - Tick normalization
- `order-handler` - Order lifecycle
- `trade-processor` - Trade capture
- `risk-engine` - Risk calculations
- `audit-logger` - Compliance logging

## Performance Targets

| Metric | Target | Critical |
|--------|--------|----------|
| Tick Processing | < 2ms | < 5ms |
| Order Submission | < 5ms | < 10ms |
| WebSocket Latency | < 10ms | < 20ms |
| Redis Operation | < 1ms | < 2ms |
| MongoDB Write | < 5ms | < 10ms |

## Compliance

- **SEBI Audit Trail**: Immutable 7-year trade retention
- **User Activity**: 10-year log retention
- **Encryption**: AES-256 at rest
- **Access Control**: RBAC with JWT

## Monitoring

- Dashboard: `http://localhost:3001` (Grafana)
- Metrics: `http://localhost:9090` (Prometheus)
- Logs: `http://localhost:5601` (Kibana)
- Kafka UI: `http://localhost:8085` (Kafka UI)

## Deployment

```bash
# Development
docker-compose up -d

# Production with full stack
docker-compose -f docker-compose.production.yml up -d

# Kubernetes
kubectl apply -f kubernetes/base/
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB connection | mongodb://localhost:27017 |
| `REDIS_URL` | Redis connection | redis://localhost:6379 |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka servers | localhost:9092 |
| `FLASK_ENV` | Environment | production |
| `SECRET_KEY` | Application secret | - |

## License

MIT License

