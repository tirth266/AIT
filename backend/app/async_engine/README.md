"""
Async Strategy Engine Architecture
===================================

## Overview

This module provides a fully async architecture for high-performance strategy execution,
supporting 100+ concurrent strategies with minimal latency.

## Architecture Components

### 1. AsyncStrategyEngine (`engine.py`)
- Single global event loop for all async operations
- Task-based strategy execution
- Built-in rate limiting and backpressure
- Error recovery with retry logic
- Event-driven architecture
- Graceful shutdown handling

### 2. TaskManager (`task_manager.py`)
- Priority queue for task execution
- Task timeout handling
- Automatic retry with exponential backoff
- Task metrics and monitoring
- Task cancellation
- Task tagging and filtering

### 3. StrategyScheduler (`scheduler.py`)
- Interval-based scheduling
- Cron-like scheduling
- One-time scheduling
- Continuous execution
- Priority-based execution

### 4. RateLimiter (`rate_limiter.py`)
- Token bucket algorithm for smooth rate limiting
- Sliding window for accurate limiting
- Per-user and per-strategy limits
- Automatic cleanup of stale entries

### 5. BackpressureHandler (`backpressure.py`)
- Queue size monitoring
- Memory pressure detection
- Response time monitoring
- Automatic throttling
- Strategy prioritization
- Graceful degradation

### 6. ErrorRecovery (`recovery.py`)
- Configurable retry policies
- Exponential backoff with jitter
- Circuit breaker pattern
- Error categorization
- Recovery strategies

### 7. EventBus (`event_bus.py`)
- Topic-based subscription
- Event filtering
- Async event handlers
- Dead letter queue

### 8. AsyncMarketDataIngestion (`market_data.py`)
- Async data stream processing
- Symbol-based subscriptions
- Data buffering and batching
- Real-time tick aggregation

## Usage

### Starting the Engine

```python
from app.async_engine import get_async_engine, initialize_async_engine

# Initialize and start
engine = await initialize_async_engine()

# Or get existing instance
engine = get_async_engine()
await engine.start()
```

### Adding and Running Strategies

```python
# Add strategy
strategy_id = await engine.add_strategy({
    'user_id': 'user123',
    'strategy_name': 'My Strategy',
    'symbol': 'RELIANCE',
    'timeframe': '1m',
    'mode': 'paper',
    'execution_interval': 5.0
})

# Start strategy
await engine.start_strategy(strategy_id)

# Stop strategy
await engine.stop_strategy(strategy_id)
```

### Monitoring

```python
# Get engine metrics
metrics = engine.get_metrics()

# Get strategy status
status = engine.get_strategy_status(strategy_id)

# Get all strategies
strategies = engine.get_all_strategies()
```

## Performance Targets

| Metric | Target |
|--------|--------|
| Concurrent Strategies | 100+ |
| Avg Execution Time | <10ms |
| P99 Latency | <50ms |
| Throughput | 10,000+ tasks/sec |
| Memory Usage | <512MB |

## Configuration

### Recommended Settings for 100+ Strategies

```python
# Rate Limiter
rate_limiter.set_strategy_limit(
    strategy_id,
    'signal_generate',
    RateLimitConfig(max_requests=1000, window_seconds=60)
)

# Backpressure
config = BackpressureConfig(
    max_concurrent_strategies=150,
    max_queue_size=2000,
    auto_throttle=True,
    throttle_factor=0.5
)

# Task Manager
task_manager = TaskManager(max_concurrent=200, default_timeout=60.0)
```

## Error Handling

The system includes automatic error recovery:

1. **Retry Policy**: Failed operations are retried with exponential backoff
2. **Circuit Breaker**: Prevents cascading failures
3. **Isolation**: Strategy failures don't affect others

## Graceful Shutdown

```python
# Stop all strategies and cleanup
await engine.stop(timeout=30.0)
```

All tasks are cancelled gracefully, and resources are properly released.
"""