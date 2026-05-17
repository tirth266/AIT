"""
Performance Bottleneck Analysis Framework
Analyzes test results and provides optimization recommendations
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BottleneckType(Enum):
    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    DATABASE = "database"
    CACHE = "cache"
    DISK_IO = "disk_io"
    CONNECTION_POOL = "connection_pool"
    LOCK_CONTENTION = "lock_contention"
    CODE_EXECUTION = "code_execution"
    EXTERNAL_SERVICE = "external_service"


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Bottleneck:
    """Identified performance bottleneck"""
    id: str
    type: BottleneckType
    severity: Severity
    component: str
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    impact: str = ""
    recommendations: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Analysis result summary"""
    test_type: str
    timestamp: str
    bottlenecks: List[Bottleneck]
    summary: str
    passed: bool
    score: float  # 0-100


class PerformanceAnalyzer:
    """Analyze performance test results and identify bottlenecks"""

    def __init__(self):
        self.bottlenecks: List[Bottleneck] = []

    def analyze_locust_results(self, results_file: str) -> AnalysisResult:
        """Analyze Locust test results"""
        logger.info(f"Analyzing Locust results from {results_file}")

        bottlenecks = []

        # Load results (simulated - in real use, parse actual CSV/JSON)
        sample_results = {
            "requests": 100000,
            "failures": 500,
            "avg_response_time": 150,
            "p95_response_time": 500,
            "p99_response_time": 1000,
            "errors": {
                "Connection timeout": 100,
                "500 Server Error": 300,
                "503 Service Unavailable": 100
            }
        }

        failure_rate = sample_results["failures"] / sample_results["requests"] * 100

        # Identify bottlenecks
        if failure_rate > 1.0:
            bottlenecks.append(Bottleneck(
                id="locust_1",
                type=BottleneckType.NETWORK,
                severity=Severity.HIGH,
                component="API Gateway",
                description=f"High failure rate: {failure_rate:.2f}%",
                evidence={"failure_rate": failure_rate, "total_failures": sample_results["failures"]},
                impact="Users experiencing request failures",
                recommendations=[
                    "Check API gateway timeout settings",
                    "Review backend service health",
                    "Implement circuit breaker pattern",
                    "Add retry logic with exponential backoff"
                ]
            ))

        if sample_results["p95_response_time"] > 200:
            bottlenecks.append(Bottleneck(
                id="locust_2",
                type=BottleneckType.CODE_EXECUTION,
                severity=Severity.MEDIUM,
                component="Order Service",
                description=f"P95 latency {sample_results['p95_response_time']}ms exceeds target",
                evidence={"p95_latency": sample_results["p95_response_time"]},
                impact="Slow order processing",
                recommendations=[
                    "Profile order placement code",
                    "Optimize database queries",
                    "Add caching for frequent operations",
                    "Consider async processing"
                ]
            ))

        score = self._calculate_score(bottlenecks)

        return AnalysisResult(
            test_type="locust",
            timestamp=datetime.now().isoformat(),
            bottlenecks=bottlenecks,
            summary=f"Found {len(bottlenecks)} bottlenecks with score {score:.0f}/100",
            passed=score >= 70,
            score=score
        )

    def analyze_websocket_results(self, results: Dict[str, Any]) -> AnalysisResult:
        """Analyze WebSocket test results"""
        logger.info("Analyzing WebSocket test results")

        bottlenecks = []

        latency_p95 = results.get("latency", {}).get("p95_ms", 0)

        if latency_p95 > 20:
            bottlenecks.append(Bottleneck(
                id="ws_1",
                type=BottleneckType.NETWORK,
                severity=Severity.CRITICAL,
                component="WebSocket Server",
                description=f"P95 latency {latency_p95}ms exceeds 20ms target",
                evidence={"p95_latency": latency_p95},
                impact="Real-time data delays affecting trading decisions",
                recommendations=[
                    "Optimize WebSocket message serialization",
                    "Implement message batching",
                    "Check network throughput limits",
                    "Consider CDN for WebSocket connections",
                    "Review CPU utilization on WebSocket servers"
                ]
            ))

        connections = results.get("connected_clients", 0)
        target_connections = 1000

        if connections < target_connections * 0.9:
            bottlenecks.append(Bottleneck(
                id="ws_2",
                type=BottleneckType.CONNECTION_POOL,
                severity=Severity.HIGH,
                component="WebSocket Connection Handler",
                description=f"Only {connections}/{target_connections} connections succeeded",
                evidence={
                    "actual_connections": connections,
                    "target_connections": target_connections
                },
                impact="Cannot handle required concurrent users",
                recommendations=[
                    "Increase connection pool size",
                    "Check OS file descriptor limits",
                    "Review connection timeout settings",
                    "Optimize connection cleanup"
                ]
            ))

        score = self._calculate_score(bottlenecks)

        return AnalysisResult(
            test_type="websocket",
            timestamp=datetime.now().isoformat(),
            bottlenecks=bottlenecks,
            summary=f"Found {len(bottlenecks)} bottlenecks",
            passed=score >= 70,
            score=score
        )

    def analyze_mongodb_results(self, results: Dict[str, Any]) -> AnalysisResult:
        """Analyze MongoDB stress test results"""
        logger.info("Analyzing MongoDB test results")

        bottlenecks = []

        for metric_name, metrics in results.get("metrics", {}).items():
            if metrics.get("p95_ms", 0) > 100:
                bottlenecks.append(Bottleneck(
                    id=f"mongo_{metric_name}",
                    type=BottleneckType.DATABASE,
                    severity=Severity.HIGH,
                    component="MongoDB",
                    description=f"{metric_name} P95 latency {metrics['p95_ms']}ms is high",
                    evidence=metrics,
                    impact="Database operations slow",
                    recommendations=[
                        "Add/verify indexes",
                        "Optimize queries",
                        "Consider read preferences (secondary preferred)",
                        "Review connection pooling",
                        "Check shard balancing if using clusters"
                    ]
                ))

        score = self._calculate_score(bottlenecks)

        return AnalysisResult(
            test_type="mongodb",
            timestamp=datetime.now().isoformat(),
            bottlenecks=bottlenecks,
            summary=f"Found {len(bottlenecks)} bottlenecks",
            passed=score >= 70,
            score=score
        )

    def analyze_redis_results(self, results: Dict[str, Any]) -> AnalysisResult:
        """Analyze Redis stress test results"""
        logger.info("Analyzing Redis test results")

        bottlenecks = []

        ops_per_sec = results.get("ops_per_sec", 0)
        if ops_per_sec < 50000:
            bottlenecks.append(Bottleneck(
                id="redis_1",
                type=BottleneckType.CACHE,
                severity=Severity.MEDIUM,
                component="Redis",
                description=f"Throughput {ops_per_sec} ops/sec below expected",
                evidence={"ops_per_sec": ops_per_sec},
                impact="Cache operations may be bottlenecking",
                recommendations=[
                    "Check Redis configuration (maxmemory-policy)",
                    "Review client pipeline usage",
                    "Consider Redis cluster for horizontal scaling",
                    "Optimize key design"
                ]
            ))

        score = self._calculate_score(bottlenecks)

        return AnalysisResult(
            test_type="redis",
            timestamp=datetime.now().isoformat(),
            bottlenecks=bottlenecks,
            summary=f"Found {len(bottlenecks)} bottlenecks",
            passed=score >= 70,
            score=score
        )

    def _calculate_score(self, bottlenecks: List[Bottleneck]) -> float:
        """Calculate overall score based on bottlenecks"""
        if not bottlenecks:
            return 100

        penalty = 0
        for b in bottlenecks:
            if b.severity == Severity.CRITICAL:
                penalty += 30
            elif b.severity == Severity.HIGH:
                penalty += 20
            elif b.severity == Severity.MEDIUM:
                penalty += 10
            elif b.severity == Severity.LOW:
                penalty += 5

        return max(0, 100 - penalty)


class PerformanceTuningAdvisor:
    """Provides performance tuning recommendations"""

    @staticmethod
    def get_api_optimizations() -> Dict[str, List[str]]:
        """Get API performance optimization recommendations"""
        return {
            "connection_pool": [
                "Increase connection pool size to 2x expected concurrent users",
                "Set minPoolSize to handle burst traffic",
                "Configure connection timeout (recommended: 10s)",
                "Enable connection health checks"
            ],
            "caching": [
                "Implement Redis for frequently accessed data (market quotes)",
                "Use CDN for static assets",
                "Add HTTP caching headers for immutable data",
                "Cache order book snapshots with short TTL"
            ],
            "database": [
                "Add indexes on frequently queried fields (symbol, user_id, status)",
                "Use connection pooling (recommended: 50-100 connections)",
                "Implement query result pagination",
                "Consider read replicas for heavy read operations"
            ],
            "code": [
                "Implement async/await for I/O operations",
                "Use batch processing for bulk operations",
                "Add request deduplication for rapid相同 requests",
                "Profile and optimize hot paths"
            ]
        }

    @staticmethod
    def get_websocket_optimizations() -> Dict[str, List[str]]:
        """Get WebSocket optimization recommendations"""
        return {
            "connection": [
                "Enable WebSocket compression (permessage-deflate)",
                "Implement connection multiplexing",
                "Use ping/pong for keepalive (interval: 30s)",
                "Configure appropriate max frame size"
            ],
            "message_handling": [
                "Implement message batching (batch every 10-50ms)",
                "Use binary protocol (Protocol Buffers/MsgPack)",
                "Compress tick data before sending",
                "Filter subscribers by relevant symbols only"
            ],
            "server": [
                "Use epoll/kqueue for Linux/macOS",
                "Enable SO_REUSEPORT for multiple workers",
                "Configure worker processes = CPU cores",
                "Set ulimit -n for high concurrent connections"
            ]
        }

    @staticmethod
    def get_database_optimizations() -> Dict[str, List[str]]:
        """Get database optimization recommendations"""
        return {
            "mongodb": [
                "Use compound indexes for common query patterns",
                "Enable WiredTiger cache (50% of RAM)",
                "Set appropriate write concern (w: majority)",
                "Use aggregation pipeline for complex queries",
                "Consider sharding for data > 100GB"
            ],
            "redis": [
                "Use pipeline for batch operations",
                "Set maxmemory and eviction policy (volatile-lru)",
                "Use hash tags for Redis Cluster",
                "Enable AOF persistence for critical data",
                "Use appropriate data structures (hash vs string)"
            ]
        }

    @staticmethod
    def get_system_optimizations() -> Dict[str, List[str]]:
        """Get system-level optimization recommendations"""
        return {
            "linux": [
                "sysctl -w net.core.somaxconn=65535",
                "sysctl -w net.ipv4.tcp_max_syn_backlog=65535",
                "sysctl -w net.ipv4.ip_local_port_range='1024 65535'",
                "ulimit -n 1000000 (file descriptors)",
                "Set cpufreq to performance mode"
            ],
            "kernel": [
                "Disable transparent huge pages",
                "Tune TCP keepalive parameters",
                "Configure connection tracking limits",
                "Enable TCP fast open"
            ]
        }


class PerformanceReportGenerator:
    """Generate comprehensive performance reports"""

    @staticmethod
    def generate_report(
        analysis_results: List[AnalysisResult],
        recommendations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report"""

        total_bottlenecks = sum(len(r.bottlenecks) for r in analysis_results)
        critical_count = sum(
            sum(1 for b in r.bottlenecks if b.severity == Severity.CRITICAL)
            for r in analysis_results
        )

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(analysis_results),
                "total_bottlenecks": total_bottlenecks,
                "critical_bottlenecks": critical_count,
                "overall_score": sum(r.score for r in analysis_results) / len(analysis_results) if analysis_results else 0,
                "all_passed": all(r.passed for r in analysis_results)
            },
            "results_by_test": {},
            "critical_recommendations": [],
            "optimization_roadmap": []
        }

        # Collect results
        for result in analysis_results:
            report["results_by_test"][result.test_type] = {
                "score": result.score,
                "passed": result.passed,
                "bottleneck_count": len(result.bottlenecks),
                "bottlenecks": [
                    {
                        "id": b.id,
                        "type": b.type.value,
                        "severity": b.severity.value,
                        "component": b.component,
                        "description": b.description,
                        "recommendations": b.recommendations
                    }
                    for b in result.bottlenecks
                ]
            }

        # Priority recommendations
        for result in analysis_results:
            for bottleneck in result.bottlenecks:
                if bottleneck.severity in [Severity.CRITICAL, Severity.HIGH]:
                    report["critical_recommendations"].append({
                        "component": bottleneck.component,
                        "issue": bottleneck.description,
                        "impact": bottleneck.impact,
                        "priority": bottleneck.severity.value,
                        "recommendations": bottleneck.recommendations
                    })

        return report


def run_analysis():
    """Run complete bottleneck analysis"""

    print("=" * 70)
    print("PERFORMANCE BOTTLENECK ANALYSIS")
    print("=" * 70)

    analyzer = PerformanceAnalyzer()

    # Analyze various test results
    locust_result = analyzer.analyze_locust_results("results.csv")
    print(f"\n=== Locust Analysis ===")
    print(f"  Score: {locust_result.score:.0f}/100")
    print(f"  Passed: {locust_result.passed}")
    print(f"  Bottlenecks: {len(locust_result.bottlenecks)}")

    ws_results = {
        "latency": {"p95_ms": 25},
        "connected_clients": 950,
        "total_clients": 1000
    }
    ws_result = analyzer.analyze_websocket_results(ws_results)
    print(f"\n=== WebSocket Analysis ===")
    print(f"  Score: {ws_result.score:.0f}/100")
    print(f"  Passed: {ws_result.passed}")
    print(f"  Bottlenecks: {len(ws_result.bottlenecks)}")

    mongo_results = {
        "metrics": {
            "orders_insert": {"p95_ms": 50},
            "orders_read": {"p95_ms": 80}
        }
    }
    mongo_result = analyzer.analyze_mongodb_results(mongo_results)
    print(f"\n=== MongoDB Analysis ===")
    print(f"  Score: {mongo_result.score:.0f}/100")

    redis_results = {"ops_per_sec": 45000}
    redis_result = analyzer.analyze_redis_results(redis_results)
    print(f"\n=== Redis Analysis ===")
    print(f"  Score: {redis_result.score:.0f}/100")

    # Generate recommendations
    advisor = PerformanceTuningAdvisor()

    print("\n" + "=" * 70)
    print("PERFORMANCE TUNING RECOMMENDATIONS")
    print("=" * 70)

    print("\n--- API Optimizations ---")
    for category, items in advisor.get_api_optimizations().items():
        print(f"\n{category.upper()}:")
        for item in items:
            print(f"  - {item}")

    print("\n--- WebSocket Optimizations ---")
    for category, items in advisor.get_websocket_optimizations().items():
        print(f"\n{category.upper()}:")
        for item in items:
            print(f"  - {item}")

    print("\n--- Database Optimizations ---")
    for category, items in advisor.get_database_optimizations().items():
        print(f"\n{category.upper()}:")
        for item in items:
            print(f"  - {item}")

    # Generate final report
    results = [locust_result, ws_result, mongo_result, redis_result]
    report = PerformanceReportGenerator.generate_report(results, {})

    with open("performance_analysis_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print(f"OVERALL SCORE: {report['summary']['overall_score']:.0f}/100")
    print(f"Tests Passed: {report['summary']['all_passed']}")
    print(f"Critical Issues: {report['summary']['critical_bottlenecks']}")
    print("=" * 70)
    print("\nFull report saved to performance_analysis_report.json")


if __name__ == "__main__":
    run_analysis()