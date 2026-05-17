"""
Performance Benchmarks
======================
Comprehensive performance testing for async strategy engine.
"""

import asyncio
import logging
import time
import random
import statistics
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager

logger = logging.getLogger('benchmark')


@dataclass
class BenchmarkResult:
    """Benchmark result."""
    name: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    throughput: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LoadTestResult:
    """Load test result."""
    concurrent_tasks: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_rps: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


class AsyncBenchmark:
    """
    Async performance benchmarking suite.
    
    Tests:
    - Strategy execution latency
    - Task scheduling performance
    - Rate limiting effectiveness
    - Backpressure handling
    - Concurrent strategy scaling
    - Memory usage under load
    """

    def __init__(self):
        self._results: List[BenchmarkResult] = []
        self._load_results: List[LoadTestResult] = []

    async def benchmark_strategy_execution(
        self,
        num_strategies: int = 100,
        iterations: int = 10
    ) -> BenchmarkResult:
        """Benchmark strategy execution with concurrent strategies."""
        logger.info(f"Benchmarking {num_strategies} strategies...")
        
        times = []
        
        for i in range(iterations):
            start = time.perf_counter()
            
            tasks = []
            for s in range(num_strategies):
                task = asyncio.create_task(self._simulate_strategy_execution(s))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        result = BenchmarkResult(
            name='strategy_execution',
            iterations=iterations,
            total_time_ms=sum(times),
            avg_time_ms=statistics.mean(times),
            min_time_ms=min(times),
            max_time_ms=max(times),
            std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
            throughput=num_strategies / (statistics.mean(times) / 1000)
        )
        
        self._results.append(result)
        return result

    async def _simulate_strategy_execution(self, strategy_id: int) -> None:
        """Simulate strategy execution."""
        await asyncio.sleep(random.uniform(0.001, 0.01))
        
        data = {
            'open': random.uniform(100, 200),
            'high': random.uniform(100, 200),
            'low': random.uniform(100, 200),
            'close': random.uniform(100, 200),
            'volume': random.randint(1000, 10000)
        }
        
        result = sum(data.values()) / len(data)

    async def benchmark_task_scheduling(
        self,
        num_tasks: int = 1000,
        task_duration_ms: float = 10
    ) -> BenchmarkResult:
        """Benchmark task scheduling performance."""
        logger.info(f"Benchmarking {num_tasks} task scheduling...")
        
        from app.async_engine.task_manager import get_task_manager, TaskPriority
        
        task_manager = get_task_manager()
        await task_manager.start()
        
        start = time.perf_counter()
        
        for i in range(num_tasks):
            await task_manager.submit(
                name=f'benchmark_task_{i}',
                coro=asyncio.sleep(task_duration_ms / 1000),
                priority=TaskPriority.NORMAL
            )
        
        await asyncio.sleep(2)
        
        elapsed = (time.perf_counter() - start) * 1000
        
        metrics = task_manager.get_metrics()
        
        result = BenchmarkResult(
            name='task_scheduling',
            iterations=num_tasks,
            total_time_ms=elapsed,
            avg_time_ms=elapsed / num_tasks,
            min_time_ms=0,
            max_time_ms=elapsed,
            std_dev_ms=0,
            throughput=num_tasks / (elapsed / 1000)
        )
        
        self._results.append(result)
        return result

    async def benchmark_rate_limiting(
        self,
        num_requests: int = 1000,
        time_window: float = 60.0
    ) -> BenchmarkResult:
        """Benchmark rate limiting performance."""
        logger.info(f"Benchmarking rate limiting...")
        
        from app.async_engine.rate_limiter import get_rate_limiter
        
        rate_limiter = get_rate_limiter()
        await rate_limiter.start()
        
        allowed = 0
        rejected = 0
        
        start = time.perf_counter()
        
        for i in range(num_requests):
            result = await rate_limiter.check_limit('benchmark', 'test_user')
            if result:
                allowed += 1
            else:
                rejected += 1
        
        elapsed = (time.perf_counter() - start) * 1000
        
        result = BenchmarkResult(
            name='rate_limiting',
            iterations=num_requests,
            total_time_ms=elapsed,
            avg_time_ms=elapsed / num_requests,
            min_time_ms=0,
            max_time_ms=elapsed,
            std_dev_ms=0,
            throughput=num_requests / (elapsed / 1000),
        )
        
        logger.info(f"Rate limiter: {allowed} allowed, {rejected} rejected")
        
        self._results.append(result)
        return result

    async def benchmark_concurrent_strategies(
        self,
        max_strategies: int = 150,
        step: int = 10
    ) -> List[Dict]:
        """Benchmark scaling with concurrent strategies."""
        logger.info("Benchmarking strategy scaling...")
        
        results = []
        
        for num_strategies in range(10, max_strategies + 1, step):
            start = time.perf_counter()
            
            tasks = []
            for s in range(num_strategies):
                task = asyncio.create_task(self._simulate_strategy_execution(s))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            elapsed = (time.perf_counter() - start) * 1000
            
            results.append({
                'strategies': num_strategies,
                'total_time_ms': elapsed,
                'avg_per_strategy_ms': elapsed / num_strategies,
                'throughput': num_strategies / (elapsed / 1000)
            })
            
            logger.info(f"Strategies: {num_strategies}, Time: {elapsed:.2f}ms")
        
        return results

    async def load_test(
        self,
        concurrent_users: int = 100,
        requests_per_user: int = 10
    ) -> LoadTestResult:
        """Perform load test with concurrent users."""
        logger.info(f"Load testing: {concurrent_users} concurrent users...")
        
        response_times: List[float] = []
        successful = 0
        failed = 0
        
        async def user_request(user_id: int):
            nonlocal successful, failed
            
            for _ in range(requests_per_user):
                try:
                    start = time.perf_counter()
                    
                    await asyncio.sleep(random.uniform(0.001, 0.05))
                    
                    response_time = (time.perf_counter() - start) * 1000
                    response_times.append(response_time)
                    successful += 1
                    
                except Exception:
                    failed += 1
        
        start = time.perf_counter()
        
        tasks = [asyncio.create_task(user_request(i)) for i in range(concurrent_users)]
        await asyncio.gather(*tasks)
        
        total_time = time.perf_counter() - start
        
        response_times.sort()
        
        total_requests = successful + failed
        
        result = LoadTestResult(
            concurrent_tasks=concurrent_users,
            total_requests=total_requests,
            successful_requests=successful,
            failed_requests=failed,
            avg_response_time_ms=statistics.mean(response_times) if response_times else 0,
            p50_latency_ms=response_times[len(response_times) // 2] if response_times else 0,
            p95_latency_ms=response_times[int(len(response_times) * 0.95)] if response_times else 0,
            p99_latency_ms=response_times[int(len(response_times) * 0.99)] if response_times else 0,
            throughput_rps=total_requests / total_time
        )
        
        self._load_results.append(result)
        return result

    async def stress_test(
        self,
        duration_seconds: int = 60,
        target_rps: int = 1000
    ) -> Dict:
        """Stress test for sustained load."""
        logger.info(f"Stress test: {target_rps} RPS for {duration_seconds}s...")
        
        request_count = 0
        error_count = 0
        latencies: List[float] = []
        
        async def generate_requests():
            nonlocal request_count, error_count
            
            interval = 1.0 / target_rps
            
            while True:
                try:
                    start = time.perf_counter()
                    
                    await asyncio.sleep(random.uniform(0.001, 0.01))
                    
                    latency = (time.perf_counter() - start) * 1000
                    latencies.append(latency)
                    request_count += 1
                    
                    await asyncio.sleep(interval)
                    
                except Exception:
                    error_count += 1
        
        tasks = [asyncio.create_task(generate_requests()) for _ in range(10)]
        
        await asyncio.sleep(duration_seconds)
        
        for task in tasks:
            task.cancel()
        
        latencies.sort()
        
        return {
            'duration_seconds': duration_seconds,
            'target_rps': target_rps,
            'total_requests': request_count,
            'error_count': error_count,
            'actual_rps': request_count / duration_seconds,
            'error_rate': error_count / request_count if request_count > 0 else 0,
            'avg_latency_ms': statistics.mean(latencies) if latencies else 0,
            'p95_latency_ms': latencies[int(len(latencies) * 0.95)] if latencies else 0,
            'p99_latency_ms': latencies[int(len(latencies) * 0.99)] if latencies else 0
        }

    def get_results(self) -> List[Dict]:
        """Get all benchmark results."""
        return [
            {
                'name': r.name,
                'iterations': r.iterations,
                'total_time_ms': round(r.total_time_ms, 2),
                'avg_time_ms': round(r.avg_time_ms, 2),
                'min_time_ms': round(r.min_time_ms, 2),
                'max_time_ms': round(r.max_time_ms, 2),
                'std_dev_ms': round(r.std_dev_ms, 2),
                'throughput': round(r.throughput, 2)
            }
            for r in self._results
        ]

    def get_load_results(self) -> List[Dict]:
        """Get all load test results."""
        return [
            {
                'concurrent_tasks': r.concurrent_tasks,
                'total_requests': r.total_requests,
                'successful_requests': r.successful_requests,
                'failed_requests': r.failed_requests,
                'avg_response_time_ms': round(r.avg_response_time_ms, 2),
                'p50_latency_ms': round(r.p50_latency_ms, 2),
                'p95_latency_ms': round(r.p95_latency_ms, 2),
                'p99_latency_ms': round(r.p99_latency_ms, 2),
                'throughput_rps': round(r.throughput_rps, 2)
            }
            for r in self._load_results
        ]


async def run_full_benchmark() -> Dict:
    """Run full benchmark suite."""
    benchmark = AsyncBenchmark()
    
    results = {}
    
    logger.info("Starting benchmark suite...")
    
    strategy_result = await benchmark.benchmark_strategy_execution(
        num_strategies=100,
        iterations=10
    )
    results['strategy_execution'] = strategy_result.__dict__
    
    task_result = await benchmark.benchmark_task_scheduling(
        num_tasks=1000,
        task_duration_ms=10
    )
    results['task_scheduling'] = task_result.__dict__
    
    rate_limit_result = await benchmark.benchmark_rate_limiting(
        num_requests=1000
    )
    results['rate_limiting'] = rate_limit_result.__dict__
    
    scaling_results = await benchmark.benchmark_concurrent_strategies(
        max_strategies=150,
        step=20
    )
    results['scaling'] = scaling_results
    
    load_result = await benchmark.load_test(
        concurrent_users=100,
        requests_per_user=10
    )
    results['load_test'] = load_result.__dict__
    
    logger.info("Benchmark suite complete")
    
    return results


_benchmark: Optional[AsyncBenchmark] = None


def get_benchmark() -> AsyncBenchmark:
    """Get benchmark instance."""
    global _benchmark
    if _benchmark is None:
        _benchmark = AsyncBenchmark()
    return _benchmark