"""
Performance Testing Framework - Main Runner
Executes all performance tests and generates comprehensive reports
"""

import sys
import os
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestRunner:
    """Main test runner orchestrator"""

    def __init__(self, base_url: str = "http://localhost:3000/api"):
        self.base_url = base_url
        self.results = {}
        self.start_time = None
        self.end_time = None

    def run_all_tests(self, test_types: list = None):
        """Run all or selected performance tests"""
        self.start_time = datetime.now()

        if test_types is None:
            test_types = ["locust", "websocket", "mongodb", "redis", "strategy", "chaos"]

        logger.info(f"Starting performance test suite at {self.start_time}")
        logger.info(f"Tests to run: {', '.join(test_types)}")

        if "locust" in test_types:
            self._run_locust_tests()

        if "websocket" in test_types:
            self._run_websocket_tests()

        if "mongodb" in test_types:
            self._run_mongodb_tests()

        if "redis" in test_types:
            self._run_redis_tests()

        if "strategy" in test_types:
            self._run_strategy_benchmarks()

        if "chaos" in test_types:
            self._run_chaos_tests()

        self.end_time = datetime.now()
        self._generate_summary()

    def _run_locust_tests(self):
        """Run Locust API load tests"""
        logger.info("=" * 50)
        logger.info("Running Locust API Load Tests")
        logger.info("=" * 50)

        logger.info("Note: Install Locust first: pip install locust")
        logger.info("To run manually: cd locust && locust -f locustfile.py --host=$BASE_URL")

        self.results["locust"] = {
            "status": "skipped",
            "message": "Run manually with: locust -f locustfile.py --host={}".format(self.base_url)
        }

    def _run_websocket_tests(self):
        """Run WebSocket load tests"""
        logger.info("=" * 50)
        logger.info("Running WebSocket Load Tests")
        logger.info("=" * 50)

        logger.info("Note: Requires WebSocket server running at ws://localhost:8080/ws")
        logger.info("To run: python websocket/websocket_stress.py ws://localhost:8080/ws")

        self.results["websocket"] = {
            "status": "skipped",
            "message": "Run manually: python websocket/websocket_stress.py"
        }

    def _run_mongodb_tests(self):
        """Run MongoDB stress tests"""
        logger.info("=" * 50)
        logger.info("Running MongoDB Stress Tests")
        logger.info("=" * 50)

        logger.info("Note: Requires MongoDB running at mongodb://localhost:27017")
        logger.info("To run: python benchmarks/mongodb_stress_test.py")

        self.results["mongodb"] = {
            "status": "skipped",
            "message": "Run manually: python benchmarks/mongodb_stress_test.py"
        }

    def _run_redis_tests(self):
        """Run Redis stress tests"""
        logger.info("=" * 50)
        logger.info("Running Redis Stress Tests")
        logger.info("=" * 50)

        logger.info("Note: Requires Redis running at localhost:6379")
        logger.info("To run: python benchmarks/redis_stress_test.py")

        self.results["redis"] = {
            "status": "skipped",
            "message": "Run manually: python benchmarks/redis_stress_test.py"
        }

    def _run_strategy_benchmarks(self):
        """Run strategy execution benchmarks"""
        logger.info("=" * 50)
        logger.info("Running Strategy Execution Benchmarks")
        logger.info("=" * 50)

        try:
            from benchmarks.strategy_execution_benchmark import StrategyBenchmark

            benchmark = StrategyBenchmark()
            results = benchmark.run_full_benchmark()

            self.results["strategy"] = {
                "status": "completed",
                "results": {k: {
                    "avg_ms": v.avg_ms,
                    "p95_ms": v.p95_ms,
                    "p99_ms": v.p99_ms,
                    "throughput": v.throughput
                } for k, v in results.items()}
            }

            logger.info("Strategy benchmarks completed")

        except Exception as e:
            logger.error(f"Strategy benchmark failed: {e}")
            self.results["strategy"] = {"status": "failed", "error": str(e)}

    def _run_chaos_tests(self):
        """Run chaos testing"""
        logger.info("=" * 50)
        logger.info("Running Chaos Tests")
        logger.info("=" * 50)

        try:
            from chaos.chaos_testing import run_chaos_suite
            run_chaos_suite()

            self.results["chaos"] = {"status": "completed"}

        except Exception as e:
            logger.error(f"Chaos tests failed: {e}")
            self.results["chaos"] = {"status": "failed", "error": str(e)}

    def _generate_summary(self):
        """Generate test summary report"""
        duration = (self.end_time - self.start_time).total_seconds()

        summary = {
            "test_run": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_seconds": duration,
                "tests_run": len(self.results),
                "tests_passed": sum(1 for r in self.results.values() if r.get("status") == "completed")
            },
            "results": self.results
        }

        logger.info("\n" + "=" * 70)
        logger.info("PERFORMANCE TEST SUITE SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Tests run: {len(self.results)}")

        for test_name, result in self.results.items():
            status = result.get("status", "unknown")
            logger.info(f"  {test_name}: {status}")

        with open("test_results_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        logger.info("\nResults saved to test_results_summary.json")


def print_usage():
    """Print usage information"""
    print("""
Performance Testing Framework - Trading Platform
===================================================

Usage:
    python run_tests.py [options]

Options:
    --all              Run all tests (default)
    --locust           Run Locust API tests
    --websocket        Run WebSocket tests
    --mongodb          Run MongoDB stress tests
    --redis            Run Redis stress tests
    --strategy         Run strategy benchmarks
    --chaos            Run chaos tests
    --base-url URL     Set API base URL (default: http://localhost:3000/api)

Examples:
    python run_tests.py --all
    python run_tests.py --strategy --chaos --base-url https://api.example.com
    python run_tests.py --locust --mongodb --redis
    """)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Performance Testing Framework")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--locust", action="store_true", help="Run Locust tests")
    parser.add_argument("--websocket", action="store_true", help="Run WebSocket tests")
    parser.add_argument("--mongodb", action="store_true", help="Run MongoDB tests")
    parser.add_argument("--redis", action="store_true", help="Run Redis tests")
    parser.add_argument("--strategy", action="store_true", help="Run strategy benchmarks")
    parser.add_argument("--chaos", action="store_true", help="Run chaos tests")
    parser.add_argument("--base-url", default="http://localhost:3000/api", help="API base URL")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        print_usage()
        sys.exit(1)

    test_types = []
    if args.all:
        test_types = ["locust", "websocket", "mongodb", "redis", "strategy", "chaos"]
    else:
        if args.locust:
            test_types.append("locust")
        if args.websocket:
            test_types.append("websocket")
        if args.mongodb:
            test_types.append("mongodb")
        if args.redis:
            test_types.append("redis")
        if args.strategy:
            test_types.append("strategy")
        if args.chaos:
            test_types.append("chaos")

    runner = TestRunner(base_url=args.base_url)
    runner.run_all_tests(test_types)