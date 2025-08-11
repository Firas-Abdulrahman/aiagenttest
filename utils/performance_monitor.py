# utils/performance_monitor.py
"""
Performance monitoring and optimization utilities
"""
import time
import logging
import threading
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    operation: str
    duration: float
    timestamp: datetime
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """Performance monitoring and analysis system"""
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics: deque = deque(maxlen=max_metrics)
        self.lock = threading.RLock()
        
        # Performance thresholds
        self.slow_operation_threshold = 1.0  # 1 second
        self.critical_threshold = 5.0  # 5 seconds
        
        # Statistics
        self.operation_stats = defaultdict(lambda: {
            'count': 0,
            'total_duration': 0.0,
            'success_count': 0,
            'error_count': 0,
            'min_duration': float('inf'),
            'max_duration': 0.0,
            'slow_operations': 0
        })
        
        logger.info("✅ Performance monitor initialized")

    def record_operation(self, operation: str, duration: float, success: bool = True, 
                        error: Optional[str] = None, metadata: Optional[Dict] = None):
        """Record a performance metric"""
        try:
            metric = PerformanceMetric(
                operation=operation,
                duration=duration,
                timestamp=datetime.now(),
                success=success,
                error=error,
                metadata=metadata or {}
            )
            
            with self.lock:
                self.metrics.append(metric)
                
                # Update statistics
                stats = self.operation_stats[operation]
                stats['count'] += 1
                stats['total_duration'] += duration
                stats['min_duration'] = min(stats['min_duration'], duration)
                stats['max_duration'] = max(stats['max_duration'], duration)
                
                if success:
                    stats['success_count'] += 1
                else:
                    stats['error_count'] += 1
                
                if duration > self.slow_operation_threshold:
                    stats['slow_operations'] += 1
                    
                    if duration > self.critical_threshold:
                        logger.warning(f"🐌 CRITICAL: {operation} took {duration:.2f}s")
                    else:
                        logger.warning(f"🐌 SLOW: {operation} took {duration:.2f}s")
                        
        except Exception as e:
            logger.error(f"❌ Error recording performance metric: {e}")

    def time_operation(self, operation: str, metadata: Optional[Dict] = None):
        """Context manager for timing operations"""
        return OperationTimer(self, operation, metadata)

    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with self.lock:
                recent_metrics = [
                    m for m in self.metrics 
                    if m.timestamp > cutoff_time
                ]
                
                if not recent_metrics:
                    return {"message": f"No metrics found for last {hours} hours"}
                
                # Overall statistics
                total_operations = len(recent_metrics)
                total_duration = sum(m.duration for m in recent_metrics)
                avg_duration = total_duration / total_operations
                success_rate = sum(1 for m in recent_metrics if m.success) / total_operations
                
                # Slow operations
                slow_ops = [m for m in recent_metrics if m.duration > self.slow_operation_threshold]
                critical_ops = [m for m in recent_metrics if m.duration > self.critical_threshold]
                
                # Top slow operations
                operation_durations = defaultdict(list)
                for m in recent_metrics:
                    operation_durations[m.operation].append(m.duration)
                
                top_slow_ops = sorted(
                    [(op, sum(durations)/len(durations)) for op, durations in operation_durations.items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                
                return {
                    "period_hours": hours,
                    "total_operations": total_operations,
                    "total_duration": total_duration,
                    "average_duration": avg_duration,
                    "success_rate": success_rate,
                    "slow_operations": len(slow_ops),
                    "critical_operations": len(critical_ops),
                    "top_slow_operations": top_slow_ops,
                    "operation_breakdown": dict(self.operation_stats)
                }
                
        except Exception as e:
            logger.error(f"❌ Error generating performance summary: {e}")
            return {"error": str(e)}

    def get_operation_details(self, operation: str, hours: int = 24) -> Dict[str, Any]:
        """Get detailed statistics for a specific operation"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with self.lock:
                operation_metrics = [
                    m for m in self.metrics 
                    if m.operation == operation and m.timestamp > cutoff_time
                ]
                
                if not operation_metrics:
                    return {"message": f"No metrics found for {operation} in last {hours} hours"}
                
                durations = [m.duration for m in operation_metrics]
                errors = [m for m in operation_metrics if not m.success]
                
                return {
                    "operation": operation,
                    "period_hours": hours,
                    "total_count": len(operation_metrics),
                    "success_count": len([m for m in operation_metrics if m.success]),
                    "error_count": len(errors),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "average_duration": sum(durations) / len(durations),
                    "recent_errors": [
                        {
                            "timestamp": e.timestamp.isoformat(),
                            "duration": e.duration,
                            "error": e.error,
                            "metadata": e.metadata
                        } for e in errors[-10:]  # Last 10 errors
                    ]
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting operation details: {e}")
            return {"error": str(e)}

    def clear_old_metrics(self, hours: int = 168):  # Default: 1 week
        """Clear metrics older than specified hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with self.lock:
                original_count = len(self.metrics)
                self.metrics = deque(
                    [m for m in self.metrics if m.timestamp > cutoff_time],
                    maxlen=self.max_metrics
                )
                cleared_count = original_count - len(self.metrics)
                
                logger.info(f"🧹 Cleared {cleared_count} old metrics (older than {hours} hours)")
                return cleared_count
                
        except Exception as e:
            logger.error(f"❌ Error clearing old metrics: {e}")
            return 0


class OperationTimer:
    """Context manager for timing operations"""
    
    def __init__(self, monitor: PerformanceMonitor, operation: str, metadata: Optional[Dict] = None):
        self.monitor = monitor
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None
        error = str(exc_val) if exc_val else None
        
        self.monitor.record_operation(
            operation=self.operation,
            duration=duration,
            success=success,
            error=error,
            metadata=self.metadata
        )


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def monitor_operation(operation: str, metadata: Optional[Dict] = None):
    """Decorator for monitoring function performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with performance_monitor.time_operation(operation, metadata):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def get_performance_stats(hours: int = 24) -> Dict[str, Any]:
    """Get current performance statistics"""
    return performance_monitor.get_performance_summary(hours)


def clear_performance_data(hours: int = 168) -> int:
    """Clear old performance data"""
    return performance_monitor.clear_old_metrics(hours)
