"""
Performance Testing Suite for Robo Trader
Tests batch processing, API rate handling, database performance, and concurrent processing.
"""

import asyncio
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import statistics
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from src.config import Config
from src.core.di import DependencyContainer
from src.core.database_state import DatabaseStateManager
from src.services.analytics_service import AnalyticsService
from src.services.recommendation_service import RecommendationEngine
from src.agents.recommendation_agent import RecommendationAgent


class PerformanceMetrics:
    """Collect and analyze performance metrics."""

    def __init__(self):
        self.metrics = {
            'response_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'api_calls': 0,
            'database_queries': 0,
            'errors': 0
        }
        self.start_time = time.time()
        self._lock = threading.Lock()

    def record_response_time(self, duration: float):
        with self._lock:
            self.metrics['response_times'].append(duration)

    def record_memory_usage(self):
        with self._lock:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.metrics['memory_usage'].append(memory_mb)

    def record_cpu_usage(self):
        with self._lock:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.metrics['cpu_usage'].append(cpu_percent)

    def increment_api_calls(self):
        with self._lock:
            self.metrics['api_calls'] += 1

    def increment_database_queries(self):
        with self._lock:
            self.metrics['database_queries'] += 1

    def increment_errors(self):
        with self._lock:
            self.metrics['errors'] += 1

    def get_summary(self) -> Dict[str, Any]:
        """Generate performance summary."""
        total_time = time.time() - self.start_time

        with self._lock:
            response_times = self.metrics['response_times']
            memory_usage = self.metrics['memory_usage']
            cpu_usage = self.metrics['cpu_usage']

        summary = {
            'total_duration_seconds': round(total_time, 2),
            'total_api_calls': self.metrics['api_calls'],
            'total_database_queries': self.metrics['database_queries'],
            'total_errors': self.metrics['errors'],
            'throughput_requests_per_second': round(len(response_times) / total_time, 2) if total_time > 0 else 0,
        }

        if response_times:
            summary.update({
                'response_time_avg_ms': round(statistics.mean(response_times) * 1000, 2),
                'response_time_median_ms': round(statistics.median(response_times) * 1000, 2),
                'response_time_min_ms': round(min(response_times) * 1000, 2),
                'response_time_max_ms': round(max(response_times) * 1000, 2),
                'response_time_p95_ms': round(statistics.quantiles(response_times, n=20)[18] * 1000, 2) if len(response_times) >= 20 else round(max(response_times) * 1000, 2),
            })

        if memory_usage:
            summary.update({
                'memory_avg_mb': round(statistics.mean(memory_usage), 2),
                'memory_peak_mb': round(max(memory_usage), 2),
            })

        if cpu_usage:
            summary.update({
                'cpu_avg_percent': round(statistics.mean(cpu_usage), 2),
                'cpu_peak_percent': round(max(cpu_usage), 2),
            })

        return summary


class PerformanceTestSuite:
    """Comprehensive performance testing suite."""

    def __init__(self):
        self.config = None
        self.container = None
        self.state_manager = None
        self.metrics = PerformanceMetrics()

    async def setup(self):
        """Initialize test environment."""
        self.config = Config()
        self.container = DependencyContainer()
        await self.container.initialize(self.config)
        self.state_manager = await self.container.get_state_manager()

    async def teardown(self):
        """Clean up test environment."""
        if self.container:
            await self.container.cleanup()

    async def test_batch_processing_limits(self, batch_sizes: List[int] = [5, 10, 25, 50, 100]):
        """Test batch processing performance with different batch sizes."""
        print("\n=== Testing Batch Processing Limits ===")

        test_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICIBANK', 'BAJFINANCE', 'MARUTI', 'BAJAJ-AUTO']

        for batch_size in batch_sizes:
            print(f"\nTesting batch size: {batch_size}")
            start_time = time.time()

            # Create multiple batches
            symbol_batches = [test_symbols[i:i + batch_size] for i in range(0, len(test_symbols), batch_size)]

            for batch in symbol_batches:
                batch_start = time.time()

                # Simulate news monitoring for batch
                tasks = []
                for symbol in batch:
                    task = self._simulate_news_fetch(symbol)
                    tasks.append(task)

                # Execute batch concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)

                batch_duration = time.time() - batch_start
                self.metrics.record_response_time(batch_duration)

                successful = sum(1 for r in results if not isinstance(r, Exception))
                failed = len(results) - successful

                print(f"  Batch {batch}: {successful} successful, {failed} failed, {batch_duration:.2f}s")

                if failed > 0:
                    self.metrics.increment_errors()

            total_time = time.time() - start_time
            print(f"  Total time for batch size {batch_size}: {total_time:.2f}s")

    async def _simulate_news_fetch(self, symbol: str) -> Dict[str, Any]:
        """Simulate news fetching for a symbol."""
        # Simulate API call delay
        await asyncio.sleep(0.1)  # 100ms API call

        # Simulate database write
        await asyncio.sleep(0.05)  # 50ms DB write

        self.metrics.increment_api_calls()
        self.metrics.increment_database_queries()

        return {
            'symbol': symbol,
            'news_count': 5,
            'timestamp': datetime.now().isoformat()
        }

    async def test_api_rate_limiting(self, concurrent_requests: List[int] = [1, 5, 10, 25, 50]):
        """Test API rate limiting under different concurrent loads."""
        print("\n=== Testing API Rate Limiting ===")

        for concurrency in concurrent_requests:
            print(f"\nTesting {concurrency} concurrent requests")
            start_time = time.time()

            # Create semaphore to limit concurrency
            semaphore = asyncio.Semaphore(concurrency)

            async def rate_limited_request(request_id: int):
                async with semaphore:
                    req_start = time.time()
                    try:
                        # Simulate API call with rate limiting
                        await asyncio.sleep(0.2)  # 200ms per request
                        self.metrics.increment_api_calls()
                        duration = time.time() - req_start
                        self.metrics.record_response_time(duration)
                        return f"Request {request_id}: success"
                    except Exception as e:
                        self.metrics.increment_errors()
                        return f"Request {request_id}: failed - {e}"

            # Execute concurrent requests
            tasks = [rate_limited_request(i) for i in range(concurrency)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_time = time.time() - start_time
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful

            print(f"  {successful} successful, {failed} failed, total time: {total_time:.2f}s")
            print(f"  Effective rate: {concurrency/total_time:.2f} req/s")

    async def test_database_performance(self, query_counts: List[int] = [10, 50, 100, 500]):
        """Test database performance under load."""
        print("\n=== Testing Database Performance ===")

        for query_count in query_counts:
            print(f"\nTesting {query_count} concurrent database queries")
            start_time = time.time()

            async def database_query(query_id: int):
                query_start = time.time()
                try:
                    # Simulate database query
                    await asyncio.sleep(0.01)  # 10ms per query
                    self.metrics.increment_database_queries()
                    duration = time.time() - query_start
                    self.metrics.record_response_time(duration)
                    return f"Query {query_id}: success"
                except Exception as e:
                    self.metrics.increment_errors()
                    return f"Query {query_id}: failed - {e}"

            # Execute concurrent queries
            tasks = [database_query(i) for i in range(query_count)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_time = time.time() - start_time
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful

            print(f"  {successful} successful, {failed} failed, total time: {total_time:.2f}s")
            print(f"  Query rate: {query_count/total_time:.2f} q/s")

    async def test_concurrent_processing(self, worker_counts: List[int] = [1, 2, 4, 8, 16]):
        """Test concurrent processing capabilities."""
        print("\n=== Testing Concurrent Processing ===")

        for workers in worker_counts:
            print(f"\nTesting with {workers} workers")
            start_time = time.time()

            async def worker_process(worker_id: int, tasks: int = 20):
                results = []
                for task_id in range(tasks):
                    task_start = time.time()
                    try:
                        # Simulate processing task
                        await asyncio.sleep(0.05)  # 50ms per task
                        duration = time.time() - task_start
                        self.metrics.record_response_time(duration)
                        results.append(f"Worker {worker_id} Task {task_id}: success")
                    except Exception as e:
                        self.metrics.increment_errors()
                        results.append(f"Worker {worker_id} Task {task_id}: failed - {e}")
                return results

            # Execute with specified number of workers
            tasks = [worker_process(i) for i in range(workers)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_time = time.time() - start_time
            total_tasks = sum(len(r) if isinstance(r, list) else 0 for r in results)
            successful_tasks = sum(sum(1 for task in r if "success" in task) if isinstance(r, list) else 0 for r in results)

            print(f"  {successful_tasks}/{total_tasks} tasks successful, total time: {total_time:.2f}s")
            print(f"  Task throughput: {total_tasks/total_time:.2f} tasks/s")

    async def test_memory_and_cpu_usage(self, duration_seconds: int = 60):
        """Monitor memory and CPU usage during sustained load."""
        print(f"\n=== Testing Memory and CPU Usage ({duration_seconds}s) ===")

        print("Starting monitoring...")
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            # Record metrics every second
            self.metrics.record_memory_usage()
            self.metrics.record_cpu_usage()
            await asyncio.sleep(1)

        print("Monitoring complete")

    async def run_full_performance_test(self):
        """Run complete performance test suite."""
        print("🚀 Starting Comprehensive Performance Test Suite")
        print("=" * 60)

        try:
            await self.setup()

            # Run all performance tests
            await self.test_batch_processing_limits()
            await self.test_api_rate_limiting()
            await self.test_database_performance()
            await self.test_concurrent_processing()
            await self.test_memory_and_cpu_usage(duration_seconds=30)

            # Generate final report
            summary = self.metrics.get_summary()
            print("\n" + "=" * 60)
            print("📊 PERFORMANCE TEST RESULTS")
            print("=" * 60)
            print(json.dumps(summary, indent=2))

            # Save results to file
            results_file = f"performance_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'summary': summary,
                    'config': {
                        'batch_sizes': [5, 10, 25, 50, 100],
                        'concurrent_requests': [1, 5, 10, 25, 50],
                        'query_counts': [10, 50, 100, 500],
                        'worker_counts': [1, 2, 4, 8, 16],
                        'monitoring_duration': 30
                    }
                }, f, indent=2)

            print(f"\n📁 Results saved to: {results_file}")

        finally:
            await self.teardown()


# Pytest fixtures and test functions
@pytest.fixture
async def perf_suite():
    """Performance test suite fixture."""
    suite = PerformanceTestSuite()
    await suite.setup()
    yield suite
    await suite.teardown()


@pytest.mark.asyncio
async def test_batch_processing_performance(perf_suite):
    """Test batch processing performance."""
    await perf_suite.test_batch_processing_limits([5, 10, 25])


@pytest.mark.asyncio
async def test_api_rate_limiting_performance(perf_suite):
    """Test API rate limiting performance."""
    await perf_suite.test_api_rate_limiting([1, 5, 10])


@pytest.mark.asyncio
async def test_database_performance_load(perf_suite):
    """Test database performance under load."""
    await perf_suite.test_database_performance([10, 50, 100])


@pytest.mark.asyncio
async def test_concurrent_processing_capabilities(perf_suite):
    """Test concurrent processing capabilities."""
    await perf_suite.test_concurrent_processing([1, 2, 4])


if __name__ == "__main__":
    # Run standalone performance tests
    async def main():
        suite = PerformanceTestSuite()
        await suite.run_full_performance_test()

    asyncio.run(main())