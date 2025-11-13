"""
Performance monitoring utilities for the RAG system
"""

import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import psutil
import os

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Individual performance metric tracking"""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass 
class QueryPerformance:
    """Query performance tracking"""
    query: str
    duration_ms: float
    timestamp: datetime
    cache_hit: bool
    tool_calls: int
    error: Optional[str] = None

class PerformanceMonitor:
    """Monitor and track system performance metrics"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.query_history: deque[QueryPerformance] = deque(maxlen=max_history)
        self.system_start_time = time.time()
        
    def record_metric(self, name: str, value: float, metadata: Optional[Dict[str, Any]] = None):
        """Record a performance metric"""
        try:
            metric = PerformanceMetric(
                name=name,
                value=value,
                metadata=metadata or {}
            )
            self.metrics[name].append(metric)
            logger.debug(f"Recorded metric {name}: {value}")
        except Exception as e:
            logger.error(f"Failed to record metric {name}: {e}")
    
    def record_query_performance(self, query: str, duration_ms: float, 
                                cache_hit: bool, tool_calls: int, 
                                error: Optional[str] = None):
        """Record query performance data"""
        try:
            perf = QueryPerformance(
                query=query[:100],  # Truncate for privacy
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                cache_hit=cache_hit,
                tool_calls=tool_calls,
                error=error
            )
            self.query_history.append(perf)
            
            # Record derived metrics
            self.record_metric("query_duration_ms", duration_ms)
            self.record_metric("cache_hit_rate", 1.0 if cache_hit else 0.0)
            self.record_metric("tool_calls_per_query", tool_calls)
            
        except Exception as e:
            logger.error(f"Failed to record query performance: {e}")
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system resource metrics"""
        try:
            process = psutil.Process(os.getpid())
            
            return {
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "memory_percent": process.memory_percent(),
                "open_files": len(process.open_files()),
                "threads": process.num_threads(),
                "uptime_seconds": int(time.time() - self.system_start_time)
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}
    
    def get_metric_stats(self, metric_name: str, 
                        time_window_minutes: Optional[int] = None) -> Dict[str, float]:
        """Get statistics for a specific metric"""
        try:
            if metric_name not in self.metrics:
                return {}
            
            metrics = list(self.metrics[metric_name])
            
            # Filter by time window if specified
            if time_window_minutes:
                cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
                metrics = [m for m in metrics if m.timestamp >= cutoff_time]
            
            if not metrics:
                return {}
            
            values = [m.value for m in metrics]
            
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1] if values else 0.0
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for metric {metric_name}: {e}")
            return {}
    
    def get_query_stats(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get query performance statistics"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
            recent_queries = [q for q in self.query_history if q.timestamp >= cutoff_time]
            
            if not recent_queries:
                return {}
            
            durations = [q.duration_ms for q in recent_queries]
            cache_hits = sum(1 for q in recent_queries if q.cache_hit)
            tool_calls = [q.tool_calls for q in recent_queries]
            errors = sum(1 for q in recent_queries if q.error)
            
            return {
                "total_queries": len(recent_queries),
                "avg_duration_ms": sum(durations) / len(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "cache_hit_rate": cache_hits / len(recent_queries),
                "avg_tool_calls": sum(tool_calls) / len(tool_calls),
                "error_rate": errors / len(recent_queries),
                "queries_per_minute": len(recent_queries) / time_window_minutes
            }
            
        except Exception as e:
            logger.error(f"Failed to get query stats: {e}")
            return {}
    
    def get_performance_report(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "time_window_minutes": time_window_minutes,
                "system_metrics": self.get_system_metrics(),
                "query_performance": self.get_query_stats(time_window_minutes),
                "metric_stats": {
                    name: self.get_metric_stats(name, time_window_minutes)
                    for name in self.metrics.keys()
                },
                "uptime_seconds": int(time.time() - self.system_start_time)
            }
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {"error": str(e)}
    
    def log_performance_summary(self, time_window_minutes: int = 60):
        """Log a summary of recent performance"""
        try:
            report = self.get_performance_report(time_window_minutes)
            query_stats = report.get("query_performance", {})
            system_stats = report.get("system_metrics", {})
            
            if query_stats:
                logger.info(
                    f"Performance Summary ({time_window_minutes}m): "
                    f"{query_stats.get('total_queries', 0)} queries, "
                    f"{query_stats.get('avg_duration_ms', 0):.1f}ms avg, "
                    f"{query_stats.get('cache_hit_rate', 0):.1%} cache hits, "
                    f"{system_stats.get('memory_mb', 0):.1f}MB memory"
                )
            
        except Exception as e:
            logger.error(f"Failed to log performance summary: {e}")

class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, monitor: PerformanceMonitor, metric_name: str, 
                 metadata: Optional[Dict[str, Any]] = None):
        self.monitor = monitor
        self.metric_name = metric_name
        self.metadata = metadata or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration_ms = (time.time() - self.start_time) * 1000
            self.metadata["duration_ms"] = duration_ms
            if exc_type is not None:
                self.metadata["error"] = str(exc_val)
            self.monitor.record_metric(self.metric_name, duration_ms, self.metadata)

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    return performance_monitor

def time_operation(metric_name: str, metadata: Optional[Dict[str, Any]] = None):
    """Decorator for timing function calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with PerformanceTimer(performance_monitor, metric_name, metadata):
                return func(*args, **kwargs)
        return wrapper
    return decorator