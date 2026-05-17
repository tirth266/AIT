"""
Strategy Execution Latency Benchmarking
Tests: Strategy execution time, signal generation, order placement latency
"""

import time
import random
import threading
import statistics
import logging
import json
import queue
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


@dataclass
class MarketData:
    """Market data snapshot"""
    symbol: str
    price: float
    volume: int
    bid: float
    ask: float
    timestamp: float


@dataclass
class Signal:
    """Trading signal"""
    symbol: str
    side: OrderSide
    quantity: int
    price: Optional[float]
    confidence: float
    timestamp: float
    strategy_name: str


@dataclass
class Order:
    """Order details"""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    price: Optional[float]
    timestamp: float
    status: str = "PENDING"


@dataclass
class BenchmarkResult:
    """Benchmark result"""
    operation: str
    iterations: int
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    min_ms: float
    throughput: float


class StrategyExecutor:
    """Simulated strategy execution engine"""

    def __init__(self):
        self.strategies = []
        self.execution_times: List[float] = []

    def execute_strategy(
        self,
        strategy_name: str,
        market_data: MarketData
    ) -> Optional[Signal]:
        """Execute a trading strategy"""
        start_time = time.perf_counter()

        # Simulate strategy computation (moving averages, indicators, etc.)
        time.sleep(random.uniform(0.001, 0.005))  # 1-5ms simulated work

        # Simple moving average calculation
        prices = [random.uniform(100, 5000) for _ in range(20)]
        sma = sum(prices) / len(prices)

        # RSI calculation
        gains = [random.uniform(0, 10) for _ in range(14)]
        losses = [random.uniform(0, 5) for _ in range(14)]
        avg_gain = sum(gains) / len(gains)
        avg_loss = sum(losses) / len(losses)
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        # Generate signal
        if rsi < 30:
            side = OrderSide.BUY
            confidence = (30 - rsi) / 30
        elif rsi > 70:
            side = OrderSide.SELL
            confidence = (rsi - 70) / 30
        else:
            return None

        execution_time = (time.perf_counter() - start_time) * 1000
        self.execution_times.append(execution_time)

        return Signal(
            symbol=market_data.symbol,
            side=side,
            quantity=random.randint(10, 1000),
            price=market_data.price,
            confidence=confidence,
            timestamp=time.time(),
            strategy_name=strategy_name
        )


class OrderPlacer:
    """Simulated order placement system"""

    def __init__(self, latency_ms: float = 10):
        self.latency_ms = latency_ms
        self.placement_times: List[float] = []

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None
    ) -> Order:
        """Place an order"""
        start_time = time.perf_counter()

        # Simulate order validation
        time.sleep(random.uniform(0.001, 0.003))

        # Simulate order book update
        time.sleep(random.uniform(0.001, 0.005))

        # Simulate exchange communication (simulated network latency)
        time.sleep(self.latency_ms / 1000)

        placement_time = (time.perf_counter() - start_time) * 1000
        self.placement_times.append(placement_time)

        return Order(
            order_id=f"ORD_{int(time.time() * 1000000)}",
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            timestamp=time.time(),
            status="FILLED"
        )

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        start_time = time.perf_counter()
        time.sleep(random.uniform(0.005, 0.015))
        cancel_time = (time.perf_counter() - start_time) * 1000
        return True


class StrategyBenchmark:
    """Strategy execution benchmarking framework"""

    def __init__(self):
        self.executor = StrategyExecutor()
        self.order_placer = OrderPlacer(latency_ms=10)
        self.results: Dict[str, BenchmarkResult] = {}

    def benchmark_strategy_execution(
        self,
        num_iterations: int = 10000,
        num_threads: int = 4
    ) -> BenchmarkResult:
        """Benchmark strategy execution latency"""
        logger.info(f"Benchmarking strategy execution: {num_iterations} iterations")

        times: List[float] = []
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        strategy_names = ["momentum", "mean_reversion", "breakout", "scalper"]

        def worker():
            for _ in range(num_iterations // num_threads):
                symbol = random.choice(symbols)
                market_data = MarketData(
                    symbol=symbol,
                    price=random.uniform(100, 5000),
                    volume=random.randint(10000, 1000000),
                    bid=random.uniform(99, 4999),
                    ask=random.uniform(101, 5001),
                    timestamp=time.time()
                )

                start = time.perf_counter()
                self.executor.execute_strategy(random.choice(strategy_names), market_data)
                times.append((time.perf_counter() - start) * 1000)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        return self._calculate_result("strategy_execution", times, num_iterations)

    def benchmark_order_placement(
        self,
        num_iterations: int = 10000,
        order_type: OrderType = OrderType.MARKET
    ) -> BenchmarkResult:
        """Benchmark order placement latency"""
        logger.info(f"Benchmarking order placement: {num_iterations} orders")

        times: List[float] = []
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]

        for _ in range(num_iterations):
            symbol = random.choice(symbols)
            side = random.choice([OrderSide.BUY, OrderSide.SELL])
            quantity = random.randint(10, 1000)
            price = random.uniform(100, 5000) if order_type == OrderType.LIMIT else None

            start = time.perf_counter()
            self.order_placer.place_order(symbol, side, quantity, order_type, price)
            times.append((time.perf_counter() - start) * 1000)

        return self._calculate_result(f"order_placement_{order_type.value}", times, num_iterations)

    def benchmark_end_to_end(
        self,
        num_iterations: int = 5000,
        num_threads: int = 4
    ) -> BenchmarkResult:
        """Benchmark end-to-end strategy execution + order placement"""
        logger.info(f"Benchmarking E2E: {num_iterations} iterations")

        times: List[float] = []
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]

        def worker():
            for _ in range(num_iterations // num_threads):
                symbol = random.choice(symbols)

                # Get market data
                market_data = MarketData(
                    symbol=symbol,
                    price=random.uniform(100, 5000),
                    volume=random.randint(10000, 1000000),
                    bid=random.uniform(99, 4999),
                    ask=random.uniform(101, 5001),
                    timestamp=time.time()
                )

                start = time.perf_counter()

                # Execute strategy
                signal = self.executor.execute_strategy("momentum", market_data)

                # Place order if signal generated
                if signal and random.random() > 0.3:
                    self.order_placer.place_order(
                        signal.symbol,
                        signal.side,
                        signal.quantity,
                        OrderType.MARKET
                    )

                times.append((time.perf_counter() - start) * 1000)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        return self._calculate_result("e2e_strategy_order", times, num_iterations)

    def benchmark_concurrent_strategies(
        self,
        num_strategies: int = 10,
        iterations_per_strategy: int = 1000
    ) -> Dict[str, BenchmarkResult]:
        """Benchmark concurrent strategy execution"""
        logger.info(f"Benchmarking concurrent strategies: {num_strategies} strategies")

        results = {}
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]

        def run_strategy(strategy_id: int):
            times = []
            for _ in range(iterations_per_strategy):
                market_data = MarketData(
                    symbol=random.choice(symbols),
                    price=random.uniform(100, 5000),
                    volume=random.randint(10000, 1000000),
                    bid=random.uniform(99, 4999),
                    ask=random.uniform(101, 5001),
                    timestamp=time.time()
                )

                start = time.perf_counter()
                self.executor.execute_strategy(f"strategy_{strategy_id}", market_data)
                times.append((time.perf_counter() - start) * 1000)

            return f"strategy_{strategy_id}", times

        with ThreadPoolExecutor(max_workers=num_strategies) as executor:
            futures = [executor.submit(run_strategy, i) for i in range(num_strategies)]
            for future in futures:
                name, times = future.result()
                results[name] = self._calculate_result(name, times, iterations_per_strategy)

        return results

    def benchmark_order_throughput(
        self,
        duration_seconds: int = 60,
        target_orders_per_second: int = 1000
    ) -> BenchmarkResult:
        """Benchmark order placement throughput"""
        logger.info(f"Benchmarking order throughput: {target_orders_per_second} orders/sec for {duration_seconds}s")

        orders_placed = {"count": 0, "lock": threading.Lock()}
        times: List[float] = []
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]

        interval = 1.0 / target_orders_per_second
        end_time = time.time() + duration_seconds

        while time.time() < end_time:
            start = time.perf_counter()

            symbol = random.choice(symbols)
            side = random.choice([OrderSide.BUY, OrderSide.SELL])
            quantity = random.randint(10, 1000)

            self.order_placer.place_order(symbol, side, quantity, OrderType.MARKET)

            with orders_placed["lock"]:
                orders_placed["count"] += 1

            times.append((time.perf_counter() - start) * 1000)

            sleep_time = interval - (time.perf_counter() - start)
            if sleep_time > 0:
                time.sleep(sleep_time)

        actual_throughput = orders_placed["count"] / duration_seconds
        logger.info(f"Actual throughput: {actual_throughput:.2f} orders/sec")

        return self._calculate_result("order_throughput", times, orders_placed["count"])

    def _calculate_result(self, operation: str, times: List[float], iterations: int) -> BenchmarkResult:
        """Calculate benchmark statistics"""
        if not times:
            return BenchmarkResult(operation, 0, 0, 0, 0, 0, 0, 0, 0)

        sorted_times = sorted(times)
        count = len(sorted_times)

        result = BenchmarkResult(
            operation=operation,
            iterations=iterations,
            avg_ms=statistics.mean(sorted_times),
            p50_ms=sorted_times[count // 2],
            p95_ms=sorted_times[int(count * 0.95)],
            p99_ms=sorted_times[int(count * 0.99)],
            max_ms=max(sorted_times),
            min_ms=min(sorted_times),
            throughput=iterations / (sum(times) / 1000) if sum(times) > 0 else 0
        )

        self.results[operation] = result

        logger.info(f"\n=== {operation} Results ===")
        logger.info(f"  Iterations: {result.iterations}")
        logger.info(f"  Avg: {result.avg_ms:.2f}ms")
        logger.info(f"  P50: {result.p50_ms:.2f}ms")
        logger.info(f"  P95: {result.p95_ms:.2f}ms")
        logger.info(f"  P99: {result.p99_ms:.2f}ms")
        logger.info(f"  Max: {result.max_ms:.2f}ms")
        logger.info(f"  Throughput: {result.throughput:.2f} ops/sec")

        return result

    def run_full_benchmark(self) -> Dict[str, BenchmarkResult]:
        """Run complete benchmark suite"""
        logger.info("=" * 50)
        logger.info("Starting Complete Strategy Benchmark Suite")
        logger.info("=" * 50)

        # Strategy execution
        self.benchmark_strategy_execution(num_iterations=20000, num_threads=4)

        # Order placement
        self.benchmark_order_placement(num_iterations=10000, order_type=OrderType.MARKET)
        self.benchmark_order_placement(num_iterations=10000, order_type=OrderType.LIMIT)

        # E2E
        self.benchmark_end_to_end(num_iterations=5000, num_threads=4)

        # Concurrent strategies
        self.benchmark_concurrent_strategies(num_strategies=10, iterations_per_strategy=1000)

        # Throughput
        self.benchmark_order_throughput(duration_seconds=30, target_orders_per_second=500)

        # Verify targets
        self._verify_targets()

        return self.results

    def _verify_targets(self):
        """Verify performance targets are met"""
        logger.info("\n=== Target Verification ===")

        targets = {
            "strategy_execution": 10.0,  # <10ms
            "order_placement_MARKET": 100.0,  # <100ms
            "e2e_strategy_order": 50.0  # <50ms
        }

        for op, target in targets.items():
            if op in self.results:
                result = self.results[op]
                status = "PASS" if result.p95_ms < target else "FAIL"
                logger.info(f"{op}: P95={result.p95_ms:.2f}ms (target: <{target}ms) [{status}]")


if __name__ == "__main__":
    benchmark = StrategyBenchmark()
    results = benchmark.run_full_benchmark()

    # Save results
    with open("strategy_benchmark_results.json", "w") as f:
        json.dump(
            {k: {
                "operation": v.operation,
                "iterations": v.iterations,
                "avg_ms": v.avg_ms,
                "p50_ms": v.p50_ms,
                "p95_ms": v.p95_ms,
                "p99_ms": v.p99_ms,
                "max_ms": v.max_ms,
                "throughput": v.throughput
            } for k, v in results.items()},
            f,
            indent=2
        )
    logger.info("Results saved to strategy_benchmark_results.json")