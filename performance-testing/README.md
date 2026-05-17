# Trading Platform Performance Testing Framework

Comprehensive performance engineering and load testing framework for trading platforms. Supports testing for API load, WebSocket connections, tick throughput, strategy execution, database stress, and chaos testing.

## Overview

This framework provides tools for testing against the following targets:

| Metric | Target |
|--------|--------|
| Concurrent WebSocket users | 1000+ |
| Tick processing throughput | 50k ticks/sec |
| WebSocket latency | <20ms |
| Strategy execution latency | <10ms |
| Order placement latency | <100ms |

## Directory Structure

```
performance-testing/
├── locust/                    # Locust load testing scripts
│   ├── locustfile.py          # Main API load test definitions
│   └── README.md
├── k6/                        # k6 JavaScript load testing
│   ├── api-load-test.js       # API load test scenarios
│   ├── websocket-load-test.js # WebSocket test scenarios
│   └── README.md
├── websocket/                 # Python WebSocket testing
│   ├── websocket_stress.py    # WebSocket load tester
│   └── README.md
├── benchmarks/                # Performance benchmarks
│   ├── mongodb_stress_test.py # MongoDB stress tests
│   ├── redis_stress_test.py   # Redis stress tests
│   ├── strategy_execution_benchmark.py # Strategy latency tests
│   └── README.md
├── chaos/                     # Chaos engineering
│   ├── chaos_testing.py       # Failure simulation
│   └── README.md
├── metrics/                   # Metrics collection
│   ├── metrics_collector.py  # Metrics aggregation
│   └── README.md
├── profiles/                  # Load profiles
│   ├── load_profiles.py      # Test profiles library
│   └── README.md
├── bottleneck_analysis.py     # Bottleneck identification
└── README.md                  # This file
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- locust
- pymongo
- redis
- requests
- psutil
- numpy
- pandas

### 2. Run Tests

#### Run All Tests
```bash
python run_tests.py --all
```

#### Run Individual Tests
```bash
# Strategy benchmarks
python run_tests.py --strategy

# Chaos testing
python run_tests.py --chaos
```

#### Manual Test Execution

**Locust API Tests:**
```bash
cd locust
locust -f locustfile.py --host=http://localhost:3000/api --headless -u 100 -r 10 -t 30m
```

**WebSocket Tests:**
```bash
python websocket/websocket_stress.py ws://localhost:8080/ws
```

**MongoDB Tests:**
```bash
python benchmarks/mongodb_stress_test.py mongodb://localhost:27017
```

**Redis Tests:**
```bash
python benchmarks/redis_stress_test.py localhost 6379
```

**k6 Tests:**
```bash
k6 run k6/api-load-test.js -e BASE_URL=http://localhost:3000/api
```

## Test Types

### 1. API Load Testing (Locust)

Tests HTTP endpoints with various load patterns:

- **Smoke Test**: 10 users, 5 minutes
- **Load Test**: 200 users, 30 minutes
- **Stress Test**: 1000 users, 60 minutes
- **Spike Test**: Burst to 1500 users, 10 minutes
- **Soak Test**: 300 users, 4 hours

Run specific profile:
```bash
locust -f locustfile.py --headless --profile load
```

### 2. WebSocket Load Testing

Tests real-time connections:

- Connection handling (1000+ concurrent)
- Message throughput (50k ticks/sec)
- Latency measurement (P50, P95, P99)
- Reconnection handling

```bash
python websocket/websocket_stress.py ws://localhost:8080/ws --clients 1000
```

### 3. Database Stress Testing

**MongoDB:**
- CRUD operations under load
- Aggregation pipeline performance
- Connection pool behavior
- Bulk write performance

**Redis:**
- String/Hash/List/Set operations
- Pub/Sub throughput
- Connection pooling
- Pipelining

### 4. Strategy Benchmarks

Tests trading strategy execution:
- Strategy execution latency (<10ms target)
- Order placement latency (<100ms target)
- Concurrent strategy performance
- End-to-end processing time

```bash
python benchmarks/strategy_execution_benchmark.py
```

### 5. Chaos Testing

Tests system resilience:
- Network partition simulation
- High latency injection
- Service failures
- Database outages
- Circuit breaker behavior
- Recovery time measurement

```bash
python chaos/chaos_testing.py
```

## Load Profiles

Predefined load profiles in `profiles/load_profiles.py`:

```python
from profiles.load_profiles import LoadProfileLibrary

# Get a specific profile
profile = LoadProfileLibrary.stress_test()

# Execute with profile
profile.to_k6_options()  # Returns k6 config
profile.to_locust_config()  # Returns Locust config
```

| Profile | Users | Duration | Use Case |
|---------|-------|----------|----------|
| smoke | 10 | 5 min | Basic verification |
| load | 200 | 30 min | Normal production load |
| stress | 1000 | 60 min | Find breaking point |
| spike | 1500 | 10 min | Sudden traffic burst |
| soak | 300 | 4 hours | Long-running stability |
| hft | 100 | 15 min | High-frequency trading |

## Metrics Collection

Built-in metrics collection with Prometheus export:

```python
from metrics.metrics_collector import MetricsCollector

collector = MetricsCollector(flush_interval=10)
collector.start()

# Record metrics
collector.record_histogram("request_duration", 45.2)
collector.increment_counter("requests_total")
collector.set_gauge("active_users", 523)

collector.stop()
```

### Grafana Dashboard

Import dashboard from `metrics/metrics_collector.py` for visualization of:
- Request latency (P50, P95, P99)
- Order placement latency
- WebSocket connections
- CPU/Memory usage
- Error rates

## Bottleneck Analysis

Run analysis on test results:

```bash
python bottleneck_analysis.py
```

Generates:
- Identified bottlenecks with severity
- Optimization recommendations
- Performance score (0-100)
- Detailed reports in JSON

## Configuration

### Environment Variables

```bash
export BASE_URL=http://localhost:3000/api
export WS_URL=ws://localhost:8080/ws
export MONGO_URL=mongodb://localhost:27017
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

### Target Thresholds

Edit `metrics/metrics_collector.py` to adjust alert thresholds:

```python
THRESHOLDS = {
    "latency_p95_ms": 100,
    "order_latency_p95_ms": 150,
    "websocket_latency_p95_ms": 20,
    "error_rate_percent": 1.0,
    "cpu_percent": 80,
    "memory_percent": 85
}
```

## Reports

Test results are saved to:

- `test_results_summary.json` - Overall test summary
- `performance_analysis_report.json` - Bottleneck analysis
- `strategy_benchmark_results.json` - Strategy benchmarks
- `chaos_test_results.json` - Chaos test results

HTML reports (Locust):
```bash
locust -f locustfile.py --html=report.html
```

## Performance Tuning Recommendations

### API Layer
1. Enable connection pooling (50-100 connections)
2. Add Redis caching for market data
3. Implement request deduplication
4. Use async processing for bulk operations

### WebSocket Layer
1. Enable message compression
2. Implement message batching
3. Use binary protocols (Protobuf/MsgPack)
4. Configure worker processes = CPU cores

### Database Layer
- MongoDB: Compound indexes, WiredTiger cache
- Redis: Pipelining, appropriate eviction policy

### System Level
```bash
# Linux kernel tuning
sysctl -w net.core.somaxconn=65535
ulimit -n 1000000
```

## Troubleshooting

### High Latency
- Check connection pool settings
- Review database query performance
- Enable compression on WebSocket

### Connection Failures
- Verify OS file descriptor limits
- Check firewall rules
- Review timeout configurations

### Memory Issues
- Monitor JVM heap if applicable
- Check connection pool size
- Review cache eviction policy

## License

MIT License - See LICENSE file for details