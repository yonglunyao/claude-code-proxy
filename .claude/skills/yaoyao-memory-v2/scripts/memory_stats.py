#!/usr/bin/env python3
"""
记忆统计分析模块 - v1.1.0
多维度统计分析记忆数据

优化：优先使用 memory.py 的 stats() 获取真实记忆数量
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent))

# 优先从 memory.py 获取真实数据
try:
    from memory import Memory
    _memory = Memory()
    _real_stats = _memory.stats()
except:
    _memory = None
    _real_stats = {}

MEMORY_DIR = Path.home() / ".openclaw" / "workspace" / "memory"

class MemoryStats:
    """记忆统计分析器"""
    
    def __init__(self):
        self.memory = _memory
        self.stats_data = _real_stats
        self.memory_dir = MEMORY_DIR
    
    def _scan_files(self) -> List[Dict]:
        """扫描记忆文件"""
        memories = []
        
        for f in self.memory_dir.glob("*.md"):
            if f.name.startswith(".") or "合并版" in f.name:
                continue
            
            try:
                content = f.read_text(encoding="utf-8")
                stat = f.stat()
                
                memories.append({
                    "filename": f.name,
                    "size": stat.st_size,
                    "mtime": datetime.fromtimestamp(stat.st_mtime),
                    "ctime": datetime.fromtimestamp(stat.st_ctime),
                    "content": content
                })
            except:
                pass
        
        return memories
    
    def time_analysis(self) -> Dict:
        """时间维度分析 - 基于真实记忆"""
        # 使用真实的记忆统计
        total = self.stats_data.get("total", len(self._scan_files()))
        
        # 扫描文件获取时间分布
        memories = self._scan_files()
        by_day = Counter()
        
        for mem in memories:
            by_day[mem["mtime"].strftime("%Y-%m-%d")] += 1
        
        # 最近7天趋势
        today = datetime.now()
        recent_days = []
        for i in range(7):
            day = today - timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            recent_days.append({
                "date": day_str,
                "count": by_day.get(day_str, 0)
            })
        
        # 计算平均
        if memories:
            oldest = min(m["mtime"] for m in memories)
            days_span = max((today - oldest).days, 1)
            avg_per_day = len(memories) / days_span
        else:
            avg_per_day = 0
        
        return {
            "total": total,  # 使用真实记忆数量
            "by_day": dict(sorted(by_day.items(), reverse=True)[:30]),
            "recent_7days": list(reversed(recent_days)),
            "avg_per_day": round(avg_per_day, 2)
        }
    
    def type_analysis(self) -> Dict:
        """类型分布分析 - 使用真实数据"""
        # 优先使用 memory.py 的真实统计
        by_type = self.stats_data.get("by_type", {})
        
        total = self.stats_data.get("total", sum(by_type.values()) if by_type else len(self._scan_files()))
        
        if by_type:
            percentages = {k: round(v / total * 100, 1) for k, v in by_type.items()}
        else:
            percentages = {}
        
        return {
            "distribution": dict(by_type) if by_type else {},
            "percentages": percentages,
            "source": "memory.stats()"
        }
    
    def importance_analysis(self) -> Dict:
        """重要性分布分析"""
        by_importance = self.stats_data.get("by_importance", {})
        
        return {
            "distribution": dict(by_importance),
            "source": "memory.stats()"
        }
    
    def comprehensive_report(self) -> str:
        """综合统计报告"""
        time_stats = self.time_analysis()
        type_stats = self.type_analysis()
        imp_stats = self.importance_analysis()
        
        lines = [
            "📊 记忆统计分析",
            "=" * 50,
            f"数据来源: {type_stats.get('source', 'file_scan')}",
            "",
            "📈 时间维度",
            f"  总记忆（向量库）: {time_stats.get('total', 0)}",
            f"  文件数: {len(self._scan_files())}",
            f"  日均新增: {time_stats.get('avg_per_day', 0)}",
            "",
            "📁 类型分布（向量库）",
        ]
        
        for mem_type, count in sorted(
            type_stats.get("distribution", {}).items(),
            key=lambda x: x[1],
            reverse=True
        ):
            pct = type_stats.get("percentages", {}).get(mem_type, 0)
            lines.append(f"  {mem_type}: {count} ({pct}%)")
        
        lines.extend([
            "",
            "⭐ 重要性分布",
        ])
        
        for level, count in sorted(imp_stats.get("distribution", {}).items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {level}: {count}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    stats = MemoryStats()
    print(stats.comprehensive_report())
