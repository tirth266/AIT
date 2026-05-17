# Quick Start Guide
# Trading Platform Observability Stack

## Prerequisites
- Docker and Docker Compose
- 8GB+ RAM available
- Ports: 3000, 5000, 9090, 3100, 4317, 9093, 9100, 9216, 9121

## Quick Start

### 1. Start Monitoring Stack (Standalone)
```bash
cd T:\1311
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. Start Full Platform (With Monitoring)
```bash
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

### 3. Verify Services
```bash
# Prometheus
curl http://localhost:9090/-/healthy

# Grafana
curl http://localhost:3000/api/health

# Loki
curl http://localhost:3100/ready

# Backend Metrics
curl http://localhost:5000/metrics
```

## Access Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / admin123 |
| Prometheus | http://localhost:9090 | - |
| Alertmanager | http://localhost:9093 | - |
| Loki | http://localhost:3100 | - |
| Tempo | http://localhost:4317 | - |

## Check Health
```bash
# Backend health
curl http://localhost:5000/health

# Detailed health
curl http://localhost:5000/health/detailed
```

## View Metrics
```bash
# Application metrics
curl http://localhost:5000/metrics | head -50

# Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].health'
```

## Stop Services
```bash
# Stop monitoring only
docker-compose -f docker-compose.monitoring.yml down

# Stop everything
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml down
```

## Adding Custom Metrics

In your Flask routes:
```python
from app.observability import metrics_collector, histogram_time

@app.route('/api/v1/trades')
def get_trades():
    start = time.time()
    result = fetch_trades()
    histogram_time('trading_trades_fetch_time', time.time() - start)
    return result
```

In WebSocket handlers:
```python
from app.observability import track_websocket_message

@manager.on('market_update')
@track_websocket_message('market_update')
def handle_market_update(data):
    process_update(data)
```

## Alert Management

View firing alerts:
```bash
curl http://localhost:9093/api/v1/alerts | jq
```

Test alert:
```bash
# Trigger a test alert by hitting an endpoint that doesn't exist
curl http://localhost:5000/api/v1/nonexistent
```

## Troubleshooting

### Metrics Not Showing
1. Check Prometheus targets: http://localhost:9090/targets
2. Verify /metrics endpoint: http://localhost:5000/metrics
3. Check service logs: `docker-compose logs prometheus`

### Grafana Dashboards Empty
1. Check Prometheus connectivity in Grafana UI
2. Verify data source is set to Prometheus
3. Check time range in dashboard

### High Memory Usage
1. Reduce retention period
2. Limit scrape frequency
3. Add more exporters to distributed load

## Production Checklist
- [ ] Change Grafana password
- [ ] Enable TLS/SSL
- [ ] Configure alert notifications
- [ ] Set up backup procedures
- [ ] Document runbooks
- [ ] Configure authentication