"""
Performance Benchmark - Performance testing and profiling utilities.
"""
import gc
import json
import time
import tracemalloc
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class BenchmarkResult:
    """Container for benchmark execution results."""
    name: str
    iterations: int
    duration_seconds: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    ops_per_second: float
    memory_bytes: int
    peak_memory_bytes: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "duration_seconds": self.duration_seconds,
            "avg_latency_ms": self.avg_latency_ms,
            "min_latency_ms": self.min_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "ops_per_second": self.ops_per_second,
            "memory_bytes": self.memory_bytes,
            "peak_memory_bytes": self.peak_memory_bytes,
            "timestamp": self.timestamp
        }


class PerformanceBenchmark:
    """
    Comprehensive performance benchmarking suite for contract testing.
    
    Provides timing, throughput, memory profiling, and comparative
    analysis capabilities for performance validation.
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize performance benchmark with configuration.
        
        Args:
            config: Configuration dictionary containing:
                - warmup_iterations: number of warmup runs before measurement
                - default_iterations: default number of benchmark iterations
                - default_duration: default duration for throughput tests
                - memory_profiling: whether to enable memory profiling
                - report_format: format for reports (json, html, csv)
        """
        self.config = config
        self.warmup_iterations = config.get("warmup_iterations", 3)
        self.default_iterations = config.get("default_iterations", 1000)
        self.default_duration = config.get("default_duration", 10.0)
        self.memory_profiling = config.get("memory_profiling", True)
        self.report_format = config.get("report_format", "json")
        self.results_history: List[BenchmarkResult] = []
    
    def benchmark(self, func: Callable, iterations: Optional[int] = None) -> Dict[str, Any]:
        """
        Run comprehensive benchmark on a function.
        
        Args:
            func: Function to benchmark
            iterations: Number of iterations (defaults to config value)
            
        Returns:
            Dictionary containing detailed benchmark metrics
        """
        if iterations is None:
            iterations = self.default_iterations
        
        for _ in range(self.warmup_iterations):
            func()
        
        latencies = []
        memory_start = None
        memory_end = None
        peak_memory = 0
        
        if self.memory_profiling:
            tracemalloc.start()
            memory_start = tracemalloc.get_traced_memory()[0]
        
        start_time = time.perf_counter()
        
        for _ in range(iterations):
            iter_start = time.perf_counter()
            func()
            iter_end = time.perf_counter()
            latencies.append((iter_end - iter_start) * 1000)
        
        end_time = time.perf_counter()
        total_duration = end_time - start_time
        
        if self.memory_profiling:
            memory_end, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
        
        latencies.sort()
        
        result = BenchmarkResult(
            name=getattr(func, "__name__", "anonymous"),
            iterations=iterations,
            duration_seconds=total_duration,
            avg_latency_ms=sum(latencies) / len(latencies),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            p50_latency_ms=latencies[len(latencies) // 2],
            p95_latency_ms=latencies[int(len(latencies) * 0.95)],
            p99_latency_ms=latencies[int(len(latencies) * 0.99)],
            ops_per_second=iterations / total_duration if total_duration > 0 else 0,
            memory_bytes=(memory_end - memory_start) if memory_start is not None and memory_end is not None else 0,
            peak_memory_bytes=peak_memory
        )
        
        self.results_history.append(result)
        return result.to_dict()
    
    def measure_latency(self, func: Callable) -> Dict[str, Any]:
        """
        Measure the latency of a single function call.
        
        Args:
            func: Function to measure
            
        Returns:
            Dictionary with latency metrics in milliseconds
        """
        mem_before = None
        if self.memory_profiling:
            tracemalloc.start()
            gc.collect()
            mem_before = tracemalloc.get_traced_memory()[0]
        
        start = time.perf_counter()
        result = func()
        end = time.perf_counter()
        
        latency_ms = (end - start) * 1000
        
        memory_bytes = 0
        if self.memory_profiling:
            mem_after, peak = tracemalloc.get_traced_memory()
            if mem_before is not None:
                memory_bytes = mem_after - mem_before
            tracemalloc.stop()
        
        return {
            "latency_ms": latency_ms,
            "latency_seconds": latency_ms / 1000,
            "memory_bytes": memory_bytes,
            "timestamp": datetime.now().isoformat(),
            "function": getattr(func, "__name__", "anonymous"),
            "result_preview": str(result)[:100] if result else None
        }
    
    def measure_throughput(self, func: Callable, duration: Optional[float] = None) -> Dict[str, Any]:
        """
        Measure throughput (operations per second) over a duration.
        
        Args:
            func: Function to measure
            duration: Duration in seconds (defaults to config value)
            
        Returns:
            Dictionary with throughput metrics
        """
        if duration is None:
            duration = self.default_duration
        
        count = 0
        mem_start = None
        if self.memory_profiling:
            gc.collect()
            tracemalloc.start()
            mem_start = tracemalloc.get_traced_memory()[0]
        
        start_time = time.perf_counter()
        end_time = start_time + duration
        
        latencies = []
        while time.perf_counter() < end_time:
            iter_start = time.perf_counter()
            func()
            iter_end = time.perf_counter()
            latencies.append((iter_end - iter_start) * 1000)
            count += 1
        
        actual_duration = time.perf_counter() - start_time
        
        memory_bytes = 0
        if self.memory_profiling:
            mem_end, peak = tracemalloc.get_traced_memory()
            memory_bytes = mem_end - mem_start
            tracemalloc.stop()
        
        latencies.sort()
        
        return {
            "ops_per_second": count / actual_duration,
            "total_operations": count,
            "duration_seconds": actual_duration,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
            "p50_latency_ms": latencies[len(latencies) // 2] if latencies else 0,
            "p95_latency_ms": latencies[int(len(latencies) * 0.95)] if latencies else 0,
            "memory_bytes": memory_bytes,
            "timestamp": datetime.now().isoformat(),
            "function": getattr(func, "__name__", "anonymous")
        }
    
    def profile_memory(self, func: Callable) -> Dict[str, Any]:
        """
        Profile memory usage of a function.
        
        Args:
            func: Function to profile
            
        Returns:
            Dictionary with memory profiling metrics
        """
        gc.collect()
        
        tracemalloc.start()
        mem_before = tracemalloc.get_traced_memory()[0]
        
        result = func()
        
        mem_after, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        allocated = mem_after - mem_before
        
        return {
            "memory_allocated_bytes": allocated,
            "memory_allocated_mb": allocated / (1024 * 1024),
            "peak_memory_bytes": peak,
            "peak_memory_mb": peak / (1024 * 1024),
            "current_memory_bytes": mem_after,
            "current_memory_mb": mem_after / (1024 * 1024),
            "timestamp": datetime.now().isoformat(),
            "function": getattr(func, "__name__", "anonymous"),
            "result_type": type(result).__name__
        }
    
    def compare_results(self, baseline: Dict, current: Dict) -> Dict[str, Any]:
        """
        Compare two benchmark results and calculate deltas.
        
        Args:
            baseline: Baseline benchmark results
            current: Current benchmark results
            
        Returns:
            Dictionary with comparison metrics and percentage changes
        """
        def safe_div(a, b):
            return (a / b - 1) * 100 if b != 0 else 0
        
        comparison = {
            "baseline_timestamp": baseline.get("timestamp"),
            "current_timestamp": current.get("timestamp"),
            "iterations": {
                "baseline": baseline.get("iterations"),
                "current": current.get("iterations"),
                "match": baseline.get("iterations") == current.get("iterations")
            }
        }
        
        latency_fields = ["avg_latency_ms", "min_latency_ms", "max_latency_ms", "p50_latency_ms"]
        for field_name in latency_fields:
            baseline_val = baseline.get(field_name, 0)
            current_val = current.get(field_name, 0)
            if field_name in baseline and field_name in current:
                comparison[field_name] = {
                    "baseline": baseline_val,
                    "current": current_val,
                    "delta_ms": current_val - baseline_val,
                    "delta_percent": safe_div(current_val, baseline_val)
                }
        
        if "ops_per_second" in baseline and "ops_per_second" in current:
            baseline_ops = baseline.get("ops_per_second", 0)
            current_ops = current.get("ops_per_second", 0)
            comparison["ops_per_second"] = {
                "baseline": baseline_ops,
                "current": current_ops,
                "delta_ops": current_ops - baseline_ops,
                "delta_percent": safe_div(current_ops, baseline_ops)
            }
        
        if "memory_bytes" in baseline and "memory_bytes" in current:
            baseline_mem = baseline.get("memory_bytes", 0)
            current_mem = current.get("memory_bytes", 0)
            comparison["memory_bytes"] = {
                "baseline": baseline_mem,
                "current": current_mem,
                "delta_bytes": current_mem - baseline_mem,
                "delta_percent": safe_div(current_mem, baseline_mem)
            }
        
        comparison["summary"] = self._generate_comparison_summary(comparison)
        
        return comparison
    
    def _generate_comparison_summary(self, comparison: Dict) -> str:
        """Generate human-readable comparison summary."""
        summary_parts = []
        
        if "avg_latency_ms" in comparison:
            delta = comparison["avg_latency_ms"]["delta_percent"]
            direction = "slower" if delta > 0 else "faster"
            summary_parts.append(f"Latency is {abs(delta):.1f}% {direction}")
        
        if "ops_per_second" in comparison:
            delta = comparison["ops_per_second"]["delta_percent"]
            direction = "lower" if delta < 0 else "higher"
            summary_parts.append(f"Throughput is {abs(delta):.1f}% {direction}")
        
        if "memory_bytes" in comparison:
            delta = comparison["memory_bytes"]["delta_percent"]
            direction = "higher" if delta > 0 else "lower"
            summary_parts.append(f"Memory usage is {abs(delta):.1f}% {direction}")
        
        return ". ".join(summary_parts) if summary_parts else "No significant changes detected"
