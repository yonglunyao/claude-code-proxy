#!/usr/bin/env python3
"""
performance_monitor.py - 性能监控模块

功能：
- 检索延迟监控
- Token消耗追踪
- 缓存命中率分析
- 历史趋势记录
"""

import json
import time
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

MEMORY_DIR = Path.home() / ".openclaw" / "workspace" / "memory"
PERF_FILE = MEMORY_DIR / ".performance.json"

# 性能数据保留条数
MAX_HISTORY = 1000


@dataclass
class PerformanceRecord:
    """性能记录"""
    timestamp: str
    operation: str  # search, embed, classify, etc.
    latency_ms: float
    tokens: int = 0
    cache_hit: bool = False
    success: bool = True
    error: str = ""


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.records: List[PerformanceRecord] = []
        self.load()
    
    def load(self):
        """加载历史数据"""
        if PERF_FILE.exists():
            try:
                with open(PERF_FILE) as f:
                    data = json.load(f)
                    self.records = [PerformanceRecord(**r) for r in data.get("records", [])]
            except:
                self.records = []
    
    def save(self):
        """保存数据"""
        PERF_FILE.parent.mkdir(parents=True, exist_ok=True)
        # 只保留最近 MAX_HISTORY 条
        records = self.records[-MAX_HISTORY:]
        with open(PERF_FILE, "w") as f:
            json.dump({
                "records": [asdict(r) for r in records],
                "last_updated": datetime.now().isoformat(),
            }, f, indent=2)
    
    def record(self, operation: str, latency_ms: float, tokens: int = 0, 
               cache_hit: bool = False, success: bool = True, error: str = ""):
        """记录一次操作"""
        record = PerformanceRecord(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            latency_ms=latency_ms,
            tokens=tokens,
            cache_hit=cache_hit,
            success=success,
            error=error,
        )
        self.records.append(record)
        self.save()
    
    def get_stats(self, hours: int = 24) -> Dict:
        """获取统计信息"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [r for r in self.records 
                   if datetime.fromisoformat(r.timestamp) >= cutoff]
        
        if not recent:
            return {
                "operation_count": 0,
                "avg_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0,
                "total_tokens": 0,
                "cache_hit_rate": 0,
                "success_rate": 0,
            }
        
        total = len(recent)
        successes = sum(1 for r in recent if r.success)
        cache_hits = sum(1 for r in recent if r.cache_hit)
        
        return {
            "operation_count": total,
            "avg_latency_ms": sum(r.latency_ms for r in recent) / total,
            "p95_latency_ms": sorted(r.latency_ms for r in recent)[int(total * 0.95)] if total > 0 else 0,
            "p99_latency_ms": sorted(r.latency_ms for r in recent)[int(total * 0.99)] if total > 0 else 0,
            "total_tokens": sum(r.tokens for r in recent),
            "cache_hit_rate": cache_hits / total if total > 0 else 0,
            "success_rate": successes / total if total > 0 else 0,
            "hours": hours,
        }
    
    def get_operation_stats(self, operation: str, hours: int = 24) -> Dict:
        """获取特定操作的统计"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [r for r in self.records 
                   if r.operation == operation 
                   and datetime.fromisoformat(r.timestamp) >= cutoff]
        
        if not recent:
            return {"count": 0, "avg_latency": 0}
        
        return {
            "count": len(recent),
            "avg_latency": sum(r.latency_ms for r in recent) / len(recent),
            "min_latency": min(r.latency_ms for r in recent),
            "max_latency": max(r.latency_ms for r in recent),
            "total_tokens": sum(r.tokens for r in recent),
        }
    
    def check_thresholds(self) -> List[str]:
        """检查阈值，返回告警列表"""
        alerts = []
        stats = self.get_stats(hours=1)  # 最近1小时
        
        if stats["avg_latency_ms"] > 100:
            alerts.append(f"平均延迟过高: {stats['avg_latency_ms']:.1f}ms")
        
        if stats["p95_latency_ms"] > 200:
            alerts.append(f"P95延迟过高: {stats['p95_latency_ms']:.1f}ms")
        
        if stats["cache_hit_rate"] < 0.6:
            alerts.append(f"缓存命中率低: {stats['cache_hit_rate']:.1%}")
        
        if stats["success_rate"] < 0.95:
            alerts.append(f"成功率低: {stats['success_rate']:.1%}")
        
        return alerts


# 装饰器：自动监控函数性能
def monitor(operation: str = None):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = PerformanceMonitor()
            start = time.time()
            success = True
            error = ""
            result = None
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                latency_ms = (time.time() - start) * 1000
                tokens = len(str(result)) // 4 if result else 0
                op = operation or func.__name__
                monitor.record(op, latency_ms, tokens, False, success, error)
        return wrapper
    return decorator


def main():
    import argparse
    parser = argparse.ArgumentParser(description="性能监控")
    parser.add_argument("--stats", "-s", action="store_true", help="显示统计")
    parser.add_argument("--op", help="特定操作统计")
    parser.add_argument("--hours", type=int, default=24, help="时间范围(小时)")
    parser.add_argument("--alert", action="store_true", help="检查告警")
    args = parser.parse_args()
    
    monitor = PerformanceMonitor()
    
    if args.alert:
        alerts = monitor.check_thresholds()
        if alerts:
            print("⚠️ 告警:")
            for a in alerts:
                print(f"  - {a}")
        else:
            print("✅ 无告警")
    
    elif args.op:
        stats = monitor.get_operation_stats(args.op, args.hours)
        print(f"📊 {args.op} 统计 (最近{args.hours}小时):")
        for k, v in stats.items():
            print(f"  {k}: {v}")
    
    else:
        stats = monitor.get_stats(args.hours)
        print(f"📊 性能统计 (最近{args.hours}小时):")
        print(f"  操作次数: {stats['operation_count']}")
        print(f"  平均延迟: {stats['avg_latency_ms']:.1f}ms")
        print(f"  P95延迟: {stats['p95_latency_ms']:.1f}ms")
        print(f"  P99延迟: {stats['p99_latency_ms']:.1f}ms")
        print(f"  Token消耗: {stats['total_tokens']}")
        print(f"  缓存命中率: {stats['cache_hit_rate']:.1%}")
        print(f"  成功率: {stats['success_rate']:.1%}")


if __name__ == "__main__":
    main()
