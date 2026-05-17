# Institutional Risk Management - Production Recommendations

## 1. Architecture Recommendations

### Real-Time Processing
- Use asyncio-based event loops for non-blocking risk calculations
- Implement Redis pub/sub for real-time position updates
- Deploy risk calculations on dedicated worker nodes
- Target latency: < 100ms for risk checks, < 500ms for stress tests

### Scalability
- Horizontal scaling with Kubernetes for risk workers
- Separate read/write paths for portfolio calculations
- Implement caching for market data and Greeks
- Database sharding by user_id for position data

### High Availability
- Active-passive risk engine failover
- Geographic redundancy for critical deployments
- Circuit breakers should be resilient to network issues

## 2. VaR Calculation Best Practices

### Historical Data Requirements
- Minimum 252 trading days for historical VaR
- Update returns data daily at market close
- Store both raw returns and rolling windows
- Consider weekend/holiday effects

### Method Selection
| Scenario | Recommended Method |
|----------|-------------------|
| Normal markets | Historical simulation |
| Options-heavy | Monte Carlo |
| Real-time checks | Parametric (fast) |
| Regulatory reporting | All methods with comparison |

### Validation
- Backtest VaR against actual losses monthly
- Use Kupiec test for coverage validation
- Track exceedance rate (should be ~5% for 95% VaR)
- Compare parametric vs historical results

## 3. Stress Testing Guidelines

### Scenario Coverage
- **Historical**: 2008 crisis, 2020 crash, flash crashes, black Monday
- **Hypothetical**: Parallel shifts, volatility spikes, correlation breakdown
- **Custom**: Sector-specific, event-based, reverse stress tests

### Execution Frequency
- Full portfolio stress: End of day
- Key scenarios: Every 15 minutes during market hours
- Pre-trade stress: On request

### Interpretation
- Use stress results as loss limits, not just warnings
- Consider stressed margin requirements
- Correlate stress results with circuit breaker thresholds

## 4. Greeks Management

### Calculation Requirements
- Use real-time volatility (not historical)
- Recalculate on significant price moves
- Store Greeks by strike and expiry buckets
- Aggregate at portfolio level

### Limits Framework
| Greek | Typical Limit | Warning Threshold |
|-------|---------------|-------------------|
| Delta | ±100,000 | 70% of limit |
| Gamma | ±50,000 | 70% of limit |
| Theta | -10,000/day | -5,000/day |
| Vega | ±50,000 | 70% of limit |

### Hedging
- Implement automated delta hedging
- Monitor gamma risk for option positions
- Track theta burn rate vs. expected revenue

## 5. Order Throttling & Protection

### Rate Limits
- Default: 100 orders/minute, 1000 orders/hour
- Adjust by user risk profile
- Implement graduated throttling
- Add IP-based limits for brute force protection

### Fat Finger Protection
- Max single order: 20% of portfolio value
- Confirmation required: 50% of portfolio value
- Auto-cancel: 100% of portfolio value
- Block prices > 10% from last traded

### Cooldown Logic
- After breach: 60-second cooldown
- Escalating cooldowns for repeated breaches
- Manual override capability with audit trail
- Alert on cooldown activation

## 6. Circuit Breaker Configuration

### Loss Circuit Breaker
- Trigger: 5% portfolio loss in 5 minutes
- Action: Block new orders
- Auto-reset: After 1 hour if no further breaches
- Override: Senior trader approval required

### Margin Circuit Breaker
- Trigger: 90% margin utilization
- Action: Block new margin positions
- Reset: Manual after margin increase
- Alert: Immediate to risk team

### Drawdown Circuit Breaker
- Trigger: 10% drawdown from peak
- Action: Halt strategy, allow closes only
- Override: Risk committee approval required
- Track: Monthly and yearly drawdowns

## 7. Monitoring & Alerting

### Real-Time Metrics
| Metric | Dashboard | Alert Threshold |
|--------|-----------|-----------------|
| VaR utilization | Always | > 80% |
| Margin utilization | Always | > 70% warning, > 90% critical |
| Drawdown | Always | > 5% warning, > 10% critical |
| Greeks limits | Always | Per-user thresholds |
| Circuit breakers | Always | Any OPEN state |

### Alert Channels
- Critical: PagerDuty + SMS + Email
- Warning: Slack + Email
- Info: Dashboard only

### Response Times
| Severity | Target Response | Max Response |
|----------|----------------|--------------|
| Emergency | 1 min | 5 min |
| Critical | 5 min | 15 min |
| Warning | 15 min | 1 hour |
| Info | 1 hour | 24 hours |

## 8. Database Schema Optimization

### Collection Design
- `risk_positions`: Indexed on (user_id, symbol), (strategy_id)
- `risk_metrics`: TTL of 90 days for raw metrics
- `risk_alerts`: TTL of 1 year, indexed on (user_id, severity, timestamp)
- `risk_scenarios`: Archive after 30 days, keep summary indefinitely

### Query Optimization
- Use aggregation pipelines for risk calculations
- Implement time-series collections for metrics
- Cache frequent queries in Redis
- Partition large user datasets

## 9. Security & Compliance

### Access Control
- Role-based access: View, Trade, Admin, Risk
- Audit all configuration changes
- Encrypt sensitive risk parameters
- Two-factor authentication for risk overrides

### Compliance
- Maintain audit trail for 7 years
- Daily risk reports generation
- VaR backtesting reports monthly
- Regulatory reporting capabilities

### Data Protection
- Mask P&L in logs
- Secure storage for historical data
- Encryption at rest and in transit
- Regular security assessments

## 10. Performance Tuning

### Calculation Optimization
- Pre-compute correlation matrices
- Use numpy/pandas vectorization
- Cache historical returns
- Batch similar calculations

### Database Performance
- Read replicas for queries
- Write optimization for real-time updates
- Index on query patterns
- Connection pooling

### Infrastructure
- GPU acceleration for Greeks (if needed)
- In-memory database for critical state
- CDN for dashboard data
- Load balancing for API

## 11. Disaster Recovery

### Backup Strategy
- Real-time replication of risk state
- Daily full backups of database
- Weekly backups of configuration
- Monthly backups of historical data

### Recovery Procedures
- RTO: 15 minutes for critical systems
- RPO: 1 minute for position data
- Regular DR drills
- Documented runbooks

### Failover
- Automatic failover for risk engine
- Manual intervention for circuit breakers
- Graceful degradation (stricter limits)
- Communication protocol for outages

## 12. Testing Recommendations

### Unit Tests
- VaR calculation accuracy
- Greeks calculation correctness
- Throttling logic
- Circuit breaker triggers

### Integration Tests
- End-to-end risk flow
- Alert delivery
- Database persistence
- API responses

### Performance Tests
- Load testing with real data
- Stress testing at 10x volume
- Latency profiling
- Memory leak detection

### Chaos Testing
- Network partition handling
- Database failure recovery
- Service restart impacts
- Circuit breaker stress

## 13. Key Metrics & KPIs

### Operational Metrics
- Risk check latency (p50, p95, p99)
- VaR calculation time
- Alert delivery time
- System availability

### Risk Metrics
- VaR exceedance rate (target: < 5%)
- Average margin utilization
- Maximum drawdown (daily, monthly)
- Number of limit breaches

### Business Metrics
- Orders blocked by throttling
- Orders blocked by circuit breakers
- False positive alert rate
- Risk team's investigation time

## 14. Implementation Checklist

- [ ] Deploy risk engine in staging
- [ ] Validate all VaR calculations against benchmarks
- [ ] Test all stress scenarios
- [ ] Configure alert channels
- [ ] Set up circuit breaker auto-reset
- [ ] Configure rate limiting
- [ ] Test fat finger protection
- [ ] Set up Grafana dashboards
- [ ] Configure PagerDuty integration
- [ ] Train users on system
- [ ] Document runbooks
- [ ] Conduct DR drill