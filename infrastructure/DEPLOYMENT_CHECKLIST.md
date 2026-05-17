# =============================================================================
# PRODUCTION DEPLOYMENT CHECKLIST
# =============================================================================
# Institutional-grade trading platform deployment verification

## Phase 1: Kafka Event Streaming

- [ ] Deploy Kafka cluster (3 brokers minimum)
- [ ] Configure Zookeeper ensemble
- [ ] Set up Schema Registry
- [ ] Create topics with appropriate partitions:
  - [ ] `ticks.raw` (16 partitions, 7 day retention)
  - [ ] `orders.created` (8 partitions, 90 day retention)
  - [ ] `trades.executed` (8 partitions, 7 year retention)
  - [ ] `audit.trading` (4 partitions, 10 year retention)
  - [ ] `dlq.errors` (2 partitions)
- [ ] Configure replication factor 3
- [ ] Set up consumer groups:
  - [ ] `tick-processor`
  - [ ] `order-handler`
  - [ ] `trade-processor`
  - [ ] `risk-engine`
  - [ ] `audit-logger`
- [ ] Configure dead letter queue handler
- [ ] Test exactly-once semantics
- [ ] Verify replay functionality

## Phase 2: Low Latency Optimization

- [ ] Install `orjson` for fast serialization
- [ ] Configure Redis connection pool
- [ ] Implement async batching for DB writes
- [ ] Benchmark tick processing (<5ms target)
- [ ] Benchmark order submission (<10ms target)
- [ ] Benchmark WebSocket latency (<20ms target)
- [ ] Tune event loop (uvloop/eventlet)
- [ ] Optimize Redis pipeline operations

## Phase 3: Observability & Monitoring

- [ ] Deploy Prometheus with custom metrics
- [ ] Import Grafana dashboards:
  - [ ] Trading Dashboard (orders, trades, P&L)
  - [ ] Technical Dashboard (latency, throughput)
  - [ ] Risk Dashboard (margin, exposure)
- [ ] Configure alert rules:
  - [ ] Trading platform down
  - [ ] High order latency (>100ms)
  - [ ] High tick latency (>5ms)
  - [ ] Kafka consumer lag (>1000)
  - [ ] High margin utilization (>80%)
  - [ ] Daily loss threshold
- [ ] Deploy ELK stack
- [ ] Configure structured logging
- [ ] Set up distributed tracing (Jaeger)
- [ ] Verify error tracking

## Phase 4: Disaster Recovery & HA

- [ ] Configure MongoDB replication
  - [ ] Primary-Replica set
  - [ ] Oplog sizing
  - [ ] Backup configuration
- [ ] Configure Redis replication
  - [ ] Master-slave setup
  - [ ] AOF persistence
- [ ] Configure Kafka replication
  - [ ] Cross-AZ replication
  - [ ] MirrorMaker setup
- [ ] Test failover procedures
- [ ] Verify backup restoration
- [ ] Document RTO/RPO targets
- [ ] Schedule DR drills

## Phase 5: Compliance & Security

- [ ] Enable audit logging
  - [ ] User activity logging
  - [ ] Trading event logging
  - [ ] API access logging
- [ ] Configure encryption at rest
- [ ] Set up secret management
- [ ] Implement RBAC
- [ ] Configure API rate limiting
- [ ] Enable TLS/mTLS
- [ ] Verify SEBI audit requirements
- [ ] Configure data retention policies:
  - [ ] Trades: 7 years
  - [ ] User logs: 10 years
  - [ ] System logs: 1 year

## Phase 6: Multi-Broker Infrastructure

- [ ] Register broker adapters:
  - [ ] Zerodha
  - [ ] Upstox
  - [ ] Dhan (planned)
- [ ] Configure broker router
- [ ] Test failover logic
- [ ] Enable circuit breakers
- [ ] Set up execution quality tracking
- [ ] Configure smart routing (latency-based)
- [ ] Test broker reconciliation

## Pre-Deployment Verification

- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Load tests passing
- [ ] Security scan completed
- [ ] Code review completed
- [ ] Documentation updated
- [ ] Runbooks created

## Post-Deployment Verification

- [ ] Health checks passing
- [ ] All services operational
- [ ] Metrics flowing
- [ ] Logs being collected
- [ ] Alerts configured
- [ ] Backups running
- [ ] DR procedures tested

## Monitoring Checklist

- [ ] Kafka:
  - [ ] Broker health
  - [ ] Consumer lag
  - [ ] Topic throughput
  - [ ] Disk usage

- [ ] Database:
  - [ ] MongoDB connection pool
  - [ ] Redis memory usage
  - [ ] Query performance

- [ ] Application:
  - [ ] Request latency
  - [ ] Error rate
  - [ ] Active connections

- [ ] Business:
  - [ ] Orders placed
  - [ ] Trades executed
  - [ ] P&L tracking
  - [ ] Margin utilization

## Rollback Plan

- [ ] Identify rollback triggers
- [ ] Document rollback procedures
- [ ] Test rollback in staging
- [ ] Keep previous version available

## Sign-off

- [ ] Platform Team Lead: _______________
- [ ] Security Team: _______________
- [ ] Compliance Officer: _______________
- [ ] Operations: _______________