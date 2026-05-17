# Trading Platform Audit Infrastructure

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│  Backend    │────▶│   Logstash   │────▶│Elasticsearch│────▶│   Kibana    │
│  (Python)   │     │  (Pipeline)  │     │  (Storage)  │     │  (Visualize)│
└─────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
  ┌─────────┐        ┌─────────┐        ┌─────────┐        ┌─────────┐
  │ Filebeat│        │ Filters │        │ Index   │        │ Dashboards│
  │ (Ship)  │        │ Parse   │        │ Lifecycle│        │ (6 total) │
  └─────────┘        └─────────┘        └─────────┘        └─────────┘
```

## Log Types & Index Mapping

| Event Category | Index Pattern | Retention | Description |
|---------------|---------------|-----------|-------------|
| trade | trading-trades-* | 7 years | Order actions, executions |
| user | trading-users-* | 5 years | Login/logout, activity |
| strategy | trading-strategies-* | 3 years | Strategy decisions |
| risk | trading-risk-events-* | 7 years | Violations, limits |
| security | trading-security-* | 7 years | Auth events, threats |
| request | trading-requests-* | 90 days | HTTP request logs |
| system | trading-logs-* | 90 days | General application logs |

## Audit Requirements Compliance

### Critical Audit Events (100% Coverage Required)

1. **Order Actions**
   - ORDER_PLACED: Every buy/sell order submitted
   - ORDER_MODIFIED: Any order modification
   - ORDER_CANCELLED: Order cancellation
   - ORDER_EXECUTED: Fill confirmation
   - ORDER_REJECTED: Rejection with reason

2. **User Authentication**
   - LOGIN_SUCCESS: Successful login
   - LOGIN_FAILED: Failed attempt with reason
   - LOGOUT: User logout
   - SESSION_EXPIRED: Automatic session timeout
   - TOKEN_REFRESHED: JWT refresh event

3. **Strategy Decisions**
   - STRATEGY_SIGNAL_GENERATED: Signal output
   - STRATEGY_DECISION_MADE: Buy/sell/hold decision
   - STRATEGY_STARTED: Strategy activation
   - STRATEGY_STOPPED: Strategy deactivation

4. **Risk Violations**
   - RISK_CHECK_FAILED: Pre-trade check failure
   - RISK_LIMIT_VIOLATION: Position/drawdown limits
   - MARGIN_CALL: Margin requirement breach
   - CIRCUIT_BREAKER_TRIGGERED: Trading halt
   - KILL_SWITCH_ACTIVATED: Emergency stop

## Retention Strategy

### Data Lifecycle

```
Hot (SSD) ──▶ Warm (HDD) ──▶ Cold (Archive) ──▶ Delete
 0-30 days    30-90 days    90 days-7 years    7+ years
```

### Curator Actions

| Time | Action | Rationale |
|------|--------|------------|
| 7 days | Force merge | Optimize for search |
| 30 days | Shrink to 1 shard | Reduce storage |
| 90 days | Close index | Stop writes, keep read |
| 1 year | Move to cold storage | Cost optimization |
| 7 years | Delete | Compliance expiry |

### Storage Requirements

- Trade logs: ~500MB/day (assuming 10k trades/day)
- User logs: ~50MB/day
- Strategy logs: ~100MB/day
- Risk events: ~20MB/day
- Security logs: ~30MB/day

**Total**: ~700MB/day × 365 days = ~255GB/year

## Compliance Recommendations

### Regulatory Alignment

1. **SEBI Requirements**
   - Trade audit trail: 7 years
   - Client KYC logs: 5 years
   - Order modification logs: 7 years

2. **GDPR (if applicable)**
   - User activity: 3 years post-relationship
   - Right to erasure: Implement data purge pipeline

3. **PCI-DSS (if payment handling)**
   - Security events: 1 year
   - Access logs: 90 days minimum

### Security Controls

1. **Log Integrity**
   - HMAC-SHA256 hash per audit record
   - Chain integrity verification
   - Immutable storage (WORM)

2. **Access Control**
   - RBAC for Kibana access
   - Audit logs viewable by compliance only
   - No write access to logs

3. **Alerting**
   - High-severity security events → Real-time alert
   - Risk limit violations → Immediate notification
   - Failed login attempts > 5 → Security alert

### Implementation Checklist

- [ ] Elasticsearch cluster (3 nodes minimum for HA)
- [ ] Logstash pipeline with JSON parsing
- [ ] Kibana dashboards (6 pre-configured)
- [ ] Curator for index lifecycle
- [ ] Filebeat sidecar on backend
- [ ] Audit integrity verification script
- [ ] Retention policy automation
- [ ] Alert rules configuration
- [ ] Access control implementation

## ELK Stack Startup

```bash
# Start ELK services
docker-compose -f docker-compose.elk.yml up -d

# Check health
curl -u elastic:password http://localhost:9200/_cluster/health
curl http://localhost:5601/api/status

# Import dashboards
curl -X POST "localhost:5601/api/kibana/dashboards/import" -H "Content-Type: application/json" -d @docker/kibana/trading-dashboards.ndjson
```

## Dashboard List

1. **Trading Platform Overview** - All events summary
2. **Trade Audit Dashboard** - Complete trade trail
3. **Security Events Dashboard** - Auth & threat monitoring
4. **Risk Events Dashboard** - Limit violations
5. **Strategy Execution Dashboard** - Signal tracking
6. **API Performance Dashboard** - Latency metrics