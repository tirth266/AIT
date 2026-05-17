# Audit Infrastructure Quick Start Guide

## 1. Start ELK Stack

```bash
# Start Elasticsearch, Logstash, Kibana
docker-compose -f docker-compose.elk.yml up -d

# Verify services are running
docker-compose -f docker-compose.elk.yml ps

# Check Elasticsearch health
curl -u elastic:changeme_in_production http://localhost:9200/_cluster/health

# Access Kibana (credentials: elastic / changeme_in_production)
# http://localhost:5601
```

## 2. Configure Backend

Add to your `.env` file:

```env
# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
ENABLE_LOGSTASH=true
LOGSTASH_HOST=logstash
LOGSTASH_PORT=5044

# Audit
AUDIT_SECRET_KEY=your-secure-audit-key-min-32-chars
AUDIT_BATCH_SIZE=10
```

## 3. Use in Your Code

### Basic Logging

```python
from app.logs import get_logger

logger = get_logger('my_module')
logger.info("Order placed", extra={'order_id': '123', 'symbol': 'RELIANCE'})
```

### Correlation IDs (Automatic)

```python
from app.logs import get_correlation_id, trace_operation

# Every request automatically gets correlation ID
@app.route('/api/orders')
def get_orders():
    correlation_id = get_correlation_id()
    # Logs automatically include correlation_id
    return jsonify({...})

# Trace operations across services
@trace_operation('execute_trade')
def execute_trade(order_data):
    # Automatic logging with timing
    pass
```

### Audit Logging

```python
from app.logs import log_order_action, log_user_login, log_strategy_decision, log_risk_violation

# Trade audit - every order action
log_order_action(
    action='order_placed',
    order_data={
        'order_id': 'ORD-12345',
        'user_id': 'user_001',
        'symbol': 'RELIANCE',
        'side': 'BUY',
        'quantity': 100,
        'price': 2500.00,
        'status': 'executed'
    }
)

# User audit - login tracking
log_user_login(
    user_id='user_001',
    username='trader1',
    ip_address='192.168.1.100',
    success=True
)

# Strategy audit - decision tracking
log_strategy_decision(
    strategy_id='strat_001',
    user_id='user_001',
    decision_data={
        'signal_type': 'bullish',
        'decision': 'BUY',
        'symbol': 'INFY',
        'entry_price': 1500.00,
        'stop_loss': 1480.00,
        'target_price': 1550.00,
        'indicators': {'rsi': 65, 'macd': 'bullish'}
    }
)

# Risk audit - violations
log_risk_violation(
    user_id='user_001',
    risk_data={
        'risk_type': 'position_limit_exceeded',
        'severity': 'high',
        'threshold': 100000.00,
        'current_value': 150000.00,
        'action_taken': 'rejected'
    }
)
```

### Using Decorators

```python
from app.logs import audit_order_action, audit_strategy_decision, audit_risk_violation

@audit_order_action('order_placed')
def place_order(order_data):
    # Order automatically logged
    return {'order_id': '...', 'status': 'executed'}

@audit_strategy_decision
def generate_signal(strategy_id, user_id, market_data):
    # Decision automatically logged
    return {'decision': 'BUY', 'symbol': '...', 'entry_price': 100}

@audit_risk_violation('margin_call', 'critical')
def check_margin(user_id, position_value):
    # Risk violations automatically logged
    return {'violated': True, 'threshold': 50000, 'current_value': 60000}
```

### Batch Audit Context

```python
from app.logs import AuditContext

with AuditContext(user_id='user_001', event_category='trade') as ctx:
    ctx.add_event('order_placed', {'order_id': '1', 'symbol': 'AAPL', 'quantity': 10})
    ctx.add_event('order_executed', {'order_id': '1', 'price': 150.00})
# Automatically flushed on exit
```

## 4. Import Kibana Dashboards

```bash
# Via Kibana UI
# 1. Go to Stack Management > Saved Objects
# 2. Import docker/kibana/trading-dashboards.ndjson

# Or via API
curl -X POST "localhost:5601/api/kibana/dashboards/import" \
  -H "Content-Type: application/json" \
  -u elastic:changeme_in_production \
  -d @docker/kibana/trading-dashboards.ndjson
```

## 5. View Dashboards

Navigate to Kibana > Dashboard:

| Dashboard | Purpose |
|-----------|---------|
| Trading Platform Overview | All events, top users, trends |
| Trade Audit Dashboard | Order trail, volume, status |
| Security Events | Login attempts, threats |
| Risk Events | Limit violations, severity |
| Strategy Execution | Signal tracking |
| API Performance | Latency, errors |

## 6. Retention & Compliance

Index lifecycle (automated via Curator):

- **90 days**: Close system logs
- **3 years**: Archive strategy logs
- **7 years**: Keep trade/risk/security (regulatory)

Manual retention verification:
```bash
docker exec trading-elasticsearch curl -u elastic:password \
  "localhost:9200/_cat/indices/trading-trades-*/?h=index,docs.count,store.size"
```

## Troubleshooting

```bash
# Check Logstash pipeline
docker logs trading-logstash --tail 50

# Verify Filebeat connectivity
docker exec trading-filebeat filebeat test output

# Query specific index
curl -u elastic:password "localhost:9200/trading-trades-*/_search?pretty&q=*"
```