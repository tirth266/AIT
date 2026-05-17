"""
Metrics Collection Framework
Collects and aggregates performance metrics from various sources
"""

import time
import threading
import statistics
import logging
import json
import psutil
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Central metrics collection and aggregation"""

    def __init__(self, flush_interval: int = 10):
        self.flush_interval = flush_interval
        self.metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()
        self.running = False
        self._start_time = time.time()

    def start(self):
        """Start metrics collection"""
        self.running = True
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
        self._system_thread = threading.Thread(target=self._collect_system_metrics, daemon=True)
        self._system_thread.start()
        logger.info("Metrics collection started")

    def stop(self):
        """Stop metrics collection"""
        self.running = False
        self._flush()

    def record_value(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a metric value"""
        with self.lock:
            self.metrics[name].append(MetricPoint(
                timestamp=time.time(),
                value=value,
                labels=labels or {}
            ))

    def increment_counter(self, name: str, value: float = 1.0):
        """Increment a counter"""
        with self.lock:
            self.counters[name] += value

    def set_gauge(self, name: str, value: float):
        """Set a gauge value"""
        with self.lock:
            self.gauges[name] = value

    def record_histogram(self, name: str, value: float):
        """Record histogram value"""
        with self.lock:
            self.histograms[name].append(value)

    def _collect_system_metrics(self):
        """Collect system-level metrics"""
        while self.running:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                network = psutil.net_io_counters()

                self.set_gauge("system.cpu.percent", cpu_percent)
                self.set_gauge("system.memory.percent", memory.percent)
                self.set_gauge("system.memory.used_mb", memory.used / 1024 / 1024)
                self.set_gauge("system.disk.percent", disk.percent)
                self.set_gauge("system.network.bytes_sent", network.bytes_sent)
                self.set_gauge("system.network.bytes_recv", network.bytes_recv)
            except Exception as e:
                logger.error(f"System metrics collection error: {e}")

            time.sleep(5)

    def _flush_loop(self):
        """Periodic flush of metrics"""
        while self.running:
            time.sleep(self.flush_interval)
            self._flush()

    def _flush(self):
        """Flush and summarize metrics"""
        with self.lock:
            summary = {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": time.time() - self._start_time,
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {}
            }

            # Calculate histogram statistics
            for name, values in self.histograms.items():
                if values:
                    sorted_vals = sorted(values)
                    count = len(sorted_vals)
                    summary["histograms"][name] = {
                        "count": count,
                        "avg": statistics.mean(sorted_vals),
                        "min": min(sorted_vals),
                        "max": max(sorted_vals),
                        "p50": sorted_vals[count // 2],
                        "p95": sorted_vals[int(count * 0.95)],
                        "p99": sorted_vals[int(count * 0.99)]
                    }

            # Calculate rate metrics
            for name in list(self.counters.keys()):
                elapsed = time.time() - self._start_time
                if elapsed > 0:
                    summary["rates"][f"{name}.per_second"] = self.counters[name] / elapsed

            logger.info(f"Metrics Summary: {json.dumps(summary, indent=2)}")

            # Clear old data
            self.metrics.clear()
            self.histograms.clear()

    def get_summary(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        with self.lock:
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histogram_samples": {k: len(v) for k, v in self.histograms.items()}
            }


class PrometheusExporter:
    """Export metrics in Prometheus format"""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector

    def export(self) -> str:
        """Export metrics as Prometheus format"""
        lines = []
        timestamp = int(time.time() * 1000)

        # Gauges
        for name, value in self.collector.gauges.items():
            metric_name = name.replace(".", "_")
            lines.append(f"{metric_name} {value} {timestamp}")

        # Counters
        for name, value in self.collector.counters.items():
            metric_name = name.replace(".", "_")
            lines.append(f"{metric_name}_total {value} {timestamp}")

        return "\n".join(lines)


class GrafanaDashboardConfig:
    """Generate Grafana dashboard configuration"""

    @staticmethod
    def generate_dashboard() -> Dict[str, Any]:
        """Generate Grafana dashboard JSON"""
        return {
            "dashboard": {
                "title": "Trading Platform Performance",
                "tags": ["trading", "performance"],
                "timezone": "browser",
                "refresh": "5s",
                "panels": [
                    {
                        "id": 1,
                        "title": "Request Latency P95",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                                "legendFormat": "P95 Latency"
                            }
                        ],
                        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8}
                    },
                    {
                        "id": 2,
                        "title": "Order Placement Latency",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "rate(order_placement_latency_ms_sum[5m]) / rate(order_placement_latency_ms_count[5m])",
                                "legendFormat": "Avg Latency"
                            }
                        ],
                        "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8}
                    },
                    {
                        "id": 3,
                        "title": "WebSocket Connections",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "ws_connected_clients",
                                "legendFormat": "Connected"
                            }
                        ],
                        "gridPos": {"x": 0, "y": 8, "w": 12, "h": 8}
                    },
                    {
                        "id": 4,
                        "title": "CPU Usage",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "system_cpu_percent",
                                "legendFormat": "CPU %"
                            }
                        ],
                        "gridPos": {"x": 12, "y": 8, "w": 12, "h": 8}
                    }
                ]
            }
        }


class AlertThresholds:
    """Define alerting thresholds for trading platform"""

    THRESHOLDS = {
        "latency_p95_ms": 100,
        "order_latency_p95_ms": 150,
        "websocket_latency_p95_ms": 20,
        "error_rate_percent": 1.0,
        "cpu_percent": 80,
        "memory_percent": 85,
        "disk_percent": 90,
        "connection_failures_per_min": 10,
        "tick_processing_lag_ms": 50
    }

    @classmethod
    def check_thresholds(cls, metrics: Dict[str, float]) -> List[str]:
        """Check metrics against thresholds"""
        alerts = []

        for metric, threshold in cls.THRESHOLDS.items():
            if metric in metrics and metrics[metric] > threshold:
                alerts.append(f"ALERT: {metric} = {metrics[metric]:.2f} exceeds threshold {threshold}")

        return alerts


if __name__ == "__main__":
    collector = MetricsCollector(flush_interval=10)
    collector.start()

    # Simulate metrics collection
    for i in range(100):
        collector.record_histogram("request_duration", random.uniform(5, 50))
        collector.increment_counter("requests_total")
        collector.set_gauge("active_users", random.randint(100, 1000))
        time.sleep(0.1)

    time.sleep(2)
    collector.stop()

    print(json.dumps(collector.get_summary(), indent=2))