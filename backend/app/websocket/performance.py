"""
Performance Optimization Guide
==============================
Recommendations for achieving sub-20ms websocket latency under load.
"""

import logging

logger = logging.getLogger(__name__)


PERFORMANCE_OPTIMIZATIONS = {
    'batching': {
        'description': 'Batch multiple events together to reduce network overhead',
        'impact': '40-60% reduction in network calls',
        'implementation': 'EventBatcher with 50ms interval'
    },
    'compression': {
        'description': 'Compress messages larger than 500 bytes',
        'impact': '70-90% reduction in payload size',
        'implementation': 'zlib compression level 6'
    },
    'adaptive_heartbeat': {
        'description': 'Adjust heartbeat interval based on latency',
        'impact': '20-30% reduction in heartbeat overhead',
        'implementation': 'AdaptiveHeartbeat with latency tracking'
    },
    'connection_pooling': {
        'description': 'Use Redis connection pooling',
        'impact': '10-15% reduction in Redis latency',
        'implementation': '50 connection pool size'
    },
    'async_processing': {
        'description': 'Process messages asynchronously',
        'impact': 'Non-blocking message handling',
        'implementation': 'asyncio queues for message processing'
    },
    'local_caching': {
        'description': 'Cache frequently accessed data locally',
        'impact': '50-80% reduction in DB calls',
        'implementation': 'In-memory caches with TTL'
    }
}


class PerformanceMonitor:
    """
    Monitor and report WebSocket performance metrics.
    """

    def __init__(self):
        self._metrics = {
            'latencies': [],
            'throughput': 0,
            'errors': 0,
            'queue_depth': 0
        }
        self._window_size = 1000

    def record_latency(self, latency_ms: float):
        """Record message latency."""
        self._metrics['latencies'].append(latency_ms)
        if len(self._metrics['latencies']) > self._window_size:
            self._metrics['latencies'].pop(0)

    def get_p50_latency(self) -> float:
        """Get 50th percentile latency."""
        if not self._metrics['latencies']:
            return 0
        sorted_latencies = sorted(self._metrics['latencies'])
        idx = len(sorted_latencies) // 2
        return sorted_latencies[idx]

    def get_p99_latency(self) -> float:
        """Get 99th percentile latency."""
        if not self._metrics['latencies']:
            return 0
        sorted_latencies = sorted(self._metrics['latencies'])
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[idx]

    def get_avg_latency(self) -> float:
        """Get average latency."""
        if not self._metrics['latencies']:
            return 0
        return sum(self._metrics['latencies']) / len(self._metrics['latencies'])

    def get_report(self) -> dict:
        """Get performance report."""
        return {
            'p50_latency_ms': self.get_p50_latency(),
            'p99_latency_ms': self.get_p99_latency(),
            'avg_latency_ms': self.get_avg_latency(),
            'throughput': self._metrics['throughput'],
            'errors': self._metrics['errors'],
            'queue_depth': self._metrics['queue_depth']
        }


class LatencyOptimizer:
    """
    Optimize latency based on current conditions.
    """

    @staticmethod
    def should_batch(message_size: int, batcher) -> bool:
        """Determine if message should be batched."""
        if not batcher:
            return False
        stats = batcher.get_stats()
        return stats.get('total_queued', 0) > 10

    @staticmethod
    def should_compress(data: dict) -> bool:
        """Determine if message should be compressed."""
        import json
        return len(json.dumps(data)) > 500

    @staticmethod
    def adjust_heartbeat_interval(avg_latency: float, current_interval: float) -> float:
        """Adjust heartbeat interval based on latency."""
        if avg_latency < 50:
            return min(current_interval * 1.2, 60)
        elif avg_latency > 200:
            return max(current_interval * 0.8, 10)
        return current_interval


OPTIMIZATION_CHECKLIST = [
    'Enable Redis connection pooling',
    'Enable message batching with 50ms interval',
    'Enable compression for messages > 500 bytes',
    'Use adaptive heartbeat intervals',
    'Configure proper ping/pong intervals (25s/60s)',
    'Use message queue for horizontal scaling',
    'Enable Redis Pub/Sub for cross-node communication',
    'Use connection limits to prevent resource exhaustion',
    'Monitor latency with p50/p99 metrics',
    'Configure nginx for WebSocket proxy (no buffering)',
    'Use eventlet async mode',
    'Enable gzip compression at nginx level'
]


def get_optimization_recommendations() -> dict:
    """Get comprehensive optimization recommendations."""
    return {
        'optimizations': PERFORMANCE_OPTIMIZATIONS,
        'checklist': OPTIMIZATION_CHECKLIST,
        'target_latency_ms': 20,
        'scaling_tiers': {
            'tier_1': {'users': 100, 'workers': 2, 'target_latency': 10},
            'tier_2': {'users': 500, 'workers': 4, 'target_latency': 15},
            'tier_3': {'users': 1000, 'workers': 8, 'target_latency': 20},
            'tier_4': {'users': 2000, 'workers': 12, 'target_latency': 25}
        }
    }