# Production Deployment Recommendations
# Observability Stack for Algorithmic Trading Platform

## 1. Infrastructure Requirements

### Minimum Production Specs
| Component | CPU | Memory | Disk |
|-----------|-----|--------|------|
| Prometheus | 2 cores | 4 GB | 50 GB SSD |
| Grafana | 1 core | 2 GB | 10 GB |
| Loki | 2 cores | 4 GB | 100 GB |
| Tempo | 2 cores | 4 GB | 50 GB |
| Alertmanager | 1 core | 1 GB | 5 GB |

### Recommended High Availability
- Run 2+ replicas of each monitoring component
- Use load balancers for Prometheus and Grafana
- Enable Prometheus federation for scaling

## 2. Security Configuration

### Network Isolation
```yaml
# Create isolated network
networks:
  monitoring-internal:
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/24
```

### Authentication
- Enable basic auth for Prometheus: `htpasswd`
- Configure Grafana OAuth with your identity provider
- Use TLS for all inter-service communication

### Sample Nginx auth for Prometheus:
```nginx
location /prometheus {
    auth_basic "Prometheus";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://prometheus:9090;
}
```

## 3. Alert Configuration

### Critical Alert Response
1. **ServiceDown**: Immediate page via PagerDuty
2. **HighErrorRate**: Page within 2 minutes
3. **OrderFailures**: Alert trading team immediately
4. **MemoryExhaustion**: Auto-scale or page ops

### Recommended Escalation
- 1st level: On-call engineer (5 min)
- 2nd level: Engineering manager (15 min)
- 3rd level: VP Engineering (30 min)

## 4. Retention & Storage

### Metrics
- Raw data: 7 days at 15s granularity
- 5-minute averages: 30 days
- 1-hour averages: 1 year

### Logs
- Hot storage (SSD): 7 days
- Cold storage (HDD): 30 days
- Archive (S3): 90 days

### Traces
- Retain 7 days
- Index by trace_id and service name

## 5. Performance Tuning

### Prometheus
```yaml
# prometheus.yml optimizations
scrape_interval: 15s
evaluation_interval: 15s
max_samples_per_query: 10000
```

### Grafana
```ini
[analytics]
reporting_enabled = false
check_for_updates = false

[log]
mode = console
```

### Loki
```yaml
limits_config:
  ingestion_rate_mb: 50
  ingestion_burst_size_mb: 100
  max_streams_per_user: 10000
```

## 6. Backup & Recovery

### Prometheus
```bash
# Backup
tar -czf prometheus-backup.tar.gz /prometheus

# Restore
tar -xzf prometheus-backup.tar.gz -C /
```

### Grafana
- Export dashboards as JSON
- Backup SQLite/PostgreSQL database
- Store configurations in Git

## 7. Monitoring the Monitoring Stack

### Self-Monitoring Metrics
```yaml
- job_name: 'monitoring-self'
  static_configs:
    - targets: ['prometheus:9090', 'grafana:3000', 'loki:3100']
```

### Key SLAs
| Metric | Target |
|--------|--------|
| Prometheus uptime | 99.9% |
| Grafana load time | < 2s |
| Alert delivery | < 5 min |
| Query latency p95 | < 1s |

## 8. Cost Optimization

### Resource Allocation
- Right-size based on actual usage
- Use auto-scaling for batch jobs
- Implement data tiering (hot/warm/cold)

### Cost Saving Tips
1. Reduce scrape frequency for non-critical metrics
2. Use recording rules for complex queries
3. Enable compression for long-term storage
4. Delete old data automatically

## 9. Day 2 Operations

### Regular Tasks
- [ ] Daily: Review firing alerts
- [ ] Weekly: Update Grafana dashboards
- [ ] Monthly: Review retention policies
- [ ] Quarterly: Capacity planning

### Runbooks
Create runbooks for each alert:
```markdown
## HighErrorRate Runbook

### Diagnosis
1. Check Prometheus for error details
2. Review logs in Loki
3. Check traces in Tempo

### Resolution
1. Identify affected service
2. Check deployment history
3. Roll back if necessary

### Prevention
- Add circuit breakers
- Implement retry logic
- Increase alerting threshold
```

## 10. Integration with Trading Platform

### Custom Metrics
Add trading-specific metrics:
```python
# Order latency
histogram.observe(execution_time)

# Strategy performance
counter.inc(failure=has_failed)

# Risk metrics
gauge.set(position_size)
```

### Business Dashboards
- P&L tracking
- Strategy win rates
- Order fill rates
- Risk limits utilization

## 11. Troubleshooting Guide

### Prometheus Not Scraping
1. Check target status: http://prometheus:9090/targets
2. Verify network connectivity
3. Check firewall rules
4. Review scrape configs

### Grafana Dashboard Slow
1. Check Prometheus query performance
2. Reduce dashboard refresh rate
3. Use recording rules for common queries
4. Limit time range selection

### High Loki Memory
1. Check ingestion rate
2. Reduce retention period
3. Add label cardinality limits
4. Scale horizontally

## 12. Scaling Considerations

### Horizontal Scaling
- Prometheus: Use thanos for global view
- Loki: Use read/write path separation
- Tempo: Sharding by trace ID

### Vertical Scaling
- Increase memory for query-heavy workloads
- Add CPU for high scrape rates
- Use SSD for write-heavy workloads

## 13. Migration Checklist

- [ ] Deploy monitoring stack in staging
- [ ] Validate all dashboards render correctly
- [ ] Test alert notifications
- [ ] Configure backup procedures
- [ ] Document runbooks
- [ ] Train on-call teams
- [ ] Set up maintenance windows
- [ ] Configure cost tracking

## 14. Emergency Contacts

| Role | Contact | Escalation Time |
|------|---------|-----------------|
| On-call Engineer | PagerDuty | 5 min |
| DevOps Lead | Slack | 15 min |
| Engineering Manager | Phone | 30 min |

## 15. Useful Commands

```bash
# Check Prometheus status
curl http://prometheus:9090/-/healthy

# Query Prometheus API
curl 'http://prometheus:9090/api/v1/query?query=up'

# Check Grafana health
curl http://grafana:3000/api/health

# View Loki logs
curl -s -G --data-urlencode 'query={job="trading-backend"}' http://loki:3100/loki/api/v1/query_range | jq

# Check Alertmanager
curl http://alertmanager:9093/api/v1/status
```

## 16. Further Resources

- Prometheus: https://prometheus.io/docs/
- Grafana: https://grafana.com/docs/
- Loki: https://grafana.com/docs/loki/
- Tempo: https://grafana.com/docs/tempo/
- Alertmanager: https://prometheus.io/docs/alerting/latest/alertmanager/