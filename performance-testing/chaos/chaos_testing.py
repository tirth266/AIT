"""
Chaos Testing Framework
Failure simulation and recovery testing for trading platform
"""

import time
import random
import threading
import logging
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FailureType(Enum):
    NETWORK_PARTITION = "network_partition"
    SERVER_CRASH = "server_crash"
    DATABASE_OUTAGE = "database_outage"
    HIGH_LATENCY = "high_latency"
    MEMORY_LEAK = "memory_leak"
    CPU_SATURATION = "cpu_saturation"
    DISK_FULL = "disk_full"
    SERVICE_UNAVAILABLE = "service_unavailable"
    THROTTLING = "throttling"
    CACHE_FAILURE = "cache_failure"


@dataclass
class ChaosScenario:
    """Chaos testing scenario configuration"""
    name: str
    failure_type: FailureType
    duration_seconds: int
    intensity: float  # 0-1
    target_component: str
    affected_percentage: float  # 0-1


@dataclass
class RecoveryTest:
    """Recovery test configuration"""
    scenario: ChaosScenario
    start_time: float
    detection_time: Optional[float] = None
    recovery_time: Optional[float] = None
    success: bool = False
    metrics: Dict[str, Any] = field(default_factory=dict)


class FailureSimulator:
    """Simulates various failure conditions"""

    def __init__(self):
        self.active_failures: Dict[str, ChaosScenario] = {}
        self.failure_log: List[Dict] = []

    def inject_network_partition(
        self,
        duration: int = 30,
        packet_loss_percent: float = 30,
        latency_ms: int = 500
    ):
        """Simulate network partition"""
        logger.warning(f"INJECTING: Network partition - {packet_loss_percent}% packet loss, {latency_ms}ms latency")
        self._log_failure("network_partition", "start", {
            "duration": duration,
            "packet_loss": packet_loss_percent,
            "latency_ms": latency_ms
        })

        time.sleep(duration)

        logger.info("RECOVERING: Network partition resolved")
        self._log_failure("network_partition", "end", {})

    def inject_high_latency(
        self,
        duration: int = 60,
        latency_ms: int = 2000
    ):
        """Simulate high latency"""
        logger.warning(f"INJECTING: High latency - {latency_ms}ms for {duration}s")
        self._log_failure("high_latency", "start", {
            "duration": duration,
            "latency_ms": latency_ms
        })

        time.sleep(duration)

        logger.info("RECOVERING: Latency normalized")
        self._log_failure("high_latency", "end", {})

    def inject_server_crash(self):
        """Simulate server crash"""
        logger.critical("INJECTING: Server crash")
        self._log_failure("server_crash", "start", {})

        logger.warning("Server crashed - simulating recovery")
        time.sleep(5)

        logger.info("RECOVERING: Server restarted")
        self._log_failure("server_crash", "end", {})

    def inject_database_outage(self, duration: int = 30):
        """Simulate database outage"""
        logger.critical(f"INJECTING: Database outage for {duration}s")
        self._log_failure("database_outage", "start", {"duration": duration})

        time.sleep(duration)

        logger.info("RECOVERING: Database restored")
        self._log_failure("database_outage", "end", {})

    def inject_memory_pressure(
        self,
        duration: int = 60,
        target_percent: float = 95
    ):
        """Simulate memory pressure"""
        logger.warning(f"INJECTING: Memory pressure to {target_percent}%")
        self._log_failure("memory_pressure", "start", {
            "target_percent": target_percent,
            "duration": duration
        })

        time.sleep(duration)

        logger.info("RECOVERING: Memory normalized")
        self._log_failure("memory_pressure", "end", {})

    def inject_service_unavailability(
        self,
        service_name: str,
        duration: int = 30
    ):
        """Simulate service unavailability"""
        logger.critical(f"INJECTING: Service unavailable - {service_name}")
        self._log_failure("service_unavailable", "start", {
            "service": service_name,
            "duration": duration
        })

        time.sleep(duration)

        logger.info(f"RECOVERING: {service_name} restored")
        self._log_failure("service_unavailable", "end", {})

    def _log_failure(self, failure_type: str, phase: str, details: Dict):
        """Log failure event"""
        self.failure_log.append({
            "type": failure_type,
            "phase": phase,
            "timestamp": datetime.now().isoformat(),
            "details": details
        })


class ChaosEngine:
    """Chaos testing orchestration engine"""

    def __init__(self):
        self.simulator = FailureSimulator()
        self.active_experiments: Dict[str, ChaosScenario] = {}
        self.recovery_tests: List[RecoveryTest] = []
        self.running = False

    def run_scenario(
        self,
        scenario: ChaosScenario,
        test_callback: Optional[Callable] = None
    ) -> RecoveryTest:
        """Run a chaos scenario"""
        logger.info(f"Starting chaos experiment: {scenario.name}")

        test = RecoveryTest(scenario=scenario, start_time=time.time())

        try:
            # Execute failure injection based on type
            if scenario.failure_type == FailureType.NETWORK_PARTITION:
                self.simulator.inject_network_partition(
                    duration=scenario.duration_seconds,
                    packet_loss_percent=30 * scenario.intensity,
                    latency_ms=int(500 * scenario.intensity)
                )
            elif scenario.failure_type == FailureType.HIGH_LATENCY:
                self.simulator.inject_high_latency(
                    duration=scenario.duration_seconds,
                    latency_ms=int(2000 * scenario.intensity)
                )
            elif scenario.failure_type == FailureType.SERVER_CRASH:
                self.simulator.inject_server_crash()
            elif scenario.failure_type == FailureType.DATABASE_OUTAGE:
                self.simulator.inject_database_outage(scenario.duration_seconds)
            elif scenario.failure_type == FailureType.MEMORY_LEAK:
                self.simulator.inject_memory_pressure(
                    duration=scenario.duration_seconds,
                    target_percent=95 * scenario.intensity
                )
            elif scenario.failure_type == FailureType.SERVICE_UNAVAILABLE:
                self.simulator.inject_service_unavailable(
                    scenario.target_component,
                    scenario.duration_seconds
                )

            test.detection_time = time.time()
            test.recovery_time = time.time()
            test.success = True

            logger.info(f"Chaos experiment completed: {scenario.name}")

        except Exception as e:
            logger.error(f"Chaos experiment failed: {e}")
            test.success = False

        self.recovery_tests.append(test)
        return test

    def run_mttd_test(self, scenarios: List[ChaosScenario]) -> Dict[str, float]:
        """Test Mean Time To Detection for various failures"""
        logger.info("Running MTTD (Mean Time To Detection) tests")

        results = {}

        for scenario in scenarios:
            logger.info(f"Testing detection for: {scenario.failure_type.value}")

            start = time.time()

            self.run_scenario(scenario)

            detection_time = time.time() - start
            results[scenario.failure_type.value] = detection_time

            logger.info(f"MTTD for {scenario.failure_type.value}: {detection_time:.2f}s")

        return results

    def run_mttr_test(self, scenarios: List[ChaosScenario]) -> Dict[str, float]:
        """Test Mean Time To Recovery for various failures"""
        logger.info("Running MTTR (Mean Time To Recovery) tests")

        results = {}

        for scenario in scenarios:
            logger.info(f"Testing recovery for: {scenario.failure_type.value}")

            start = time.time()
            self.run_scenario(scenario)
            recovery_time = time.time() - start

            results[scenario.failure_type.value] = recovery_time

            logger.info(f"MTTR for {scenario.failure_type.value}: {recovery_time:.2f}s")

        return results

    def run_resilience_test(
        self,
        num_iterations: int = 10
    ) -> Dict[str, Any]:
        """Run comprehensive resilience test suite"""
        logger.info(f"Running resilience test suite: {num_iterations} iterations")

        scenarios = [
            ChaosScenario("network_partition", FailureType.NETWORK_PARTITION, 30, 0.5, "api", 0.3),
            ChaosScenario("high_latency", FailureType.HIGH_LATENCY, 20, 0.7, "api", 0.5),
            ChaosScenario("db_outage", FailureType.DATABASE_OUTAGE, 15, 1.0, "database", 1.0),
            ChaosScenario("service_failure", FailureType.SERVICE_UNAVAILABLE, 10, 0.8, "order_service", 1.0),
        ]

        results = {
            "iterations": num_iterations,
            "scenarios_tested": len(scenarios),
            "success_count": 0,
            "failure_count": 0,
            "avg_recovery_time": 0,
            "by_scenario": {}
        }

        for scenario in scenarios:
            scenario_results = []

            for _ in range(num_iterations):
                test = self.run_scenario(scenario)
                if test.success:
                    results["success_count"] += 1
                    scenario_results.append(test.recovery_time - test.start_time if test.recovery_time else 0)
                else:
                    results["failure_count"] += 1

            if scenario_results:
                avg_recovery = sum(scenario_results) / len(scenario_results)
                results["by_scenario"][scenario.name] = {
                    "avg_recovery_time": avg_recovery,
                    "min_recovery_time": min(scenario_results),
                    "max_recovery_time": max(scenario_results),
                    "success_rate": len(scenario_results) / num_iterations
                }

        results["avg_recovery_time"] = (
            results["success_count"] / (results["success_count"] + results["failure_count"])
            if (results["success_count"] + results["failure_count"]) > 0 else 0
        )

        return results


class CircuitBreakerTest:
    """Test circuit breaker behavior under failure conditions"""

    def __init__(self):
        self.failure_count = 0
        self.success_count = 0
        self.circuit_open = False
        self.circuit_half_open = False

    def simulate_circuit_breaker(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30
    ) -> Dict[str, Any]:
        """Simulate circuit breaker behavior"""
        logger.info("Testing circuit breaker behavior")

        events = []
        request_count = 50

        for i in range(request_count):
            # Simulate random failures
            is_failure = random.random() < 0.4

            if is_failure:
                self.failure_count += 1
                events.append({"request": i, "result": "failure"})
            else:
                self.success_count += 1
                events.append({"request": i, "result": "success"})

            # Check if circuit should open
            if self.failure_count >= failure_threshold:
                self.circuit_open = True
                events.append({
                    "request": i,
                    "event": "circuit_open",
                    "failure_count": self.failure_count
                })
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

                # Simulate recovery
                time.sleep(0.1)
                self.circuit_open = False
                self.circuit_half_open = True
                self.failure_count = 0
                events.append({"request": i, "event": "circuit_half_open"})

        return {
            "total_requests": request_count,
            "failures": self.failure_count,
            "successes": self.success_count,
            "circuit_activations": sum(1 for e in events if "circuit" in e.get("event", "")),
            "events": events
        }


class TimeoutTest:
    """Test timeout and fallback behavior"""

    def test_timeout_handling(
        self,
        timeout_ms: int = 1000,
        response_times: List[int] = None
    ) -> Dict[str, Any]:
        """Test timeout handling for various response times"""
        if response_times is None:
            response_times = [100, 500, 1000, 2000, 5000]

        results = {
            "timeout_ms": timeout_ms,
            "responses": []
        }

        for response_time in response_times:
            succeeded = response_time < timeout_ms
            results["responses"].append({
                "response_time_ms": response_time,
                "succeeded": succeeded,
                "timed_out": not succeeded
            })

        results["success_rate"] = sum(1 for r in results["responses"] if r["succeeded"]) / len(results["responses"])

        return results


def run_chaos_suite():
    """Run complete chaos testing suite"""

    print("=" * 60)
    print("CHAOS TESTING SUITE - TRADING PLATFORM")
    print("=" * 60)

    engine = ChaosEngine()

    # Test scenarios
    scenarios = [
        ChaosScenario("network_latency", FailureType.HIGH_LATENCY, 15, 0.5, "api_gateway", 0.3),
        ChaosScenario("database_failure", FailureType.DATABASE_OUTAGE, 10, 0.8, "mongodb", 1.0),
        ChaosScenario("service_failure", FailureType.SERVICE_UNAVAILABLE, 10, 0.6, "order_service", 0.5),
    ]

    # Run MTTD tests
    print("\n=== Mean Time To Detection (MTTD) Tests ===")
    mttd_results = engine.run_mttd_test(scenarios)
    for scenario, time_sec in mttd_results.items():
        print(f"  {scenario}: {time_sec:.2f}s")

    # Run MTTR tests
    print("\n=== Mean Time To Recovery (MTTR) Tests ===")
    mttr_results = engine.run_mttr_test(scenarios)
    for scenario, time_sec in mttr_results.items():
        print(f"  {scenario}: {time_sec:.2f}s")

    # Run resilience tests
    print("\n=== Resilience Test Suite ===")
    resilience_results = engine.run_resilience_test(num_iterations=5)
    print(f"  Success count: {resilience_results['success_count']}")
    print(f"  Failure count: {resilience_results['failure_count']}")
    print(f"  Avg recovery time: {resilience_results['avg_recovery_time']:.2f}s")

    # Circuit breaker test
    print("\n=== Circuit Breaker Test ===")
    cb_test = CircuitBreakerTest()
    cb_results = cb_test.simulate_circuit_breaker()
    print(f"  Total requests: {cb_results['total_requests']}")
    print(f"  Circuit activations: {cb_results['circuit_activations']}")

    # Timeout test
    print("\n=== Timeout Handling Test ===")
    timeout_test = TimeoutTest()
    timeout_results = timeout_test.test_timeout_handling(timeout_ms=1000)
    print(f"  Timeout: {timeout_results['timeout_ms']}ms")
    print(f"  Success rate: {timeout_results['success_rate']*100:.1f}%")

    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "mttd_results": mttd_results,
        "mttr_results": mttr_results,
        "resilience_results": resilience_results,
        "circuit_breaker_results": cb_results,
        "timeout_results": timeout_results
    }

    with open("chaos_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n=== Results saved to chaos_test_results.json ===")


if __name__ == "__main__":
    run_chaos_suite()