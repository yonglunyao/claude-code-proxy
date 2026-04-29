#!/usr/bin/env python3
"""
遗忘检测模块 - v1.1.0
识别长期未访问的记忆，提示用户清理或强化

优化：可选择从 memory.py 获取真实记忆列表
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
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

class ForgetDetector:
    """遗忘检测器"""
    
    def __init__(self):
        self.memory_dir = MEMORY_DIR
        self.memory = _memory
        self.stats = _real_stats
    
    def analyze(self) -> Dict:
        """
        分析所有记忆的遗忘风险
        返回结构化数据
        """
        memories = []
        
        # 优先使用真实记忆数量
        total = self.stats.get("total", 0)
        
        # 扫描文件获取详情
        for f in self.memory_dir.glob("*.md"):
            if f.name.startswith(".") or "合并版" in f.name:
                continue
            
            try:
                stat = f.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                now = datetime.now()
                days_since = (now - mtime).days
                
                # 计算遗忘分数
                forget_score = min(100, days_since * 3)
                
                memories.append({
                    "file": f.name,
                    "title": f.stem,
                    "size": stat.st_size,
                    "modified": mtime.isoformat(),
                    "days_since_modified": days_since,
                    "forget_score": forget_score
                })
            except:
                pass
        
        # 分类
        hot = [m for m in memories if m["days_since_modified"] <= 7]
        warm = [m for m in memories if 7 < m["days_since_modified"] <= 30]
        cold = [m for m in memories if m["days_since_modified"] > 30]
        
        return {
            "total": total,  # 真实记忆数量
            "file_count": len(memories),  # 文件数量
            "hot": hot,
            "warm": warm,
            "cold": cold,
            "hot_count": len(hot),
            "warm_count": len(warm),
            "cold_count": len(cold),
            "high_risk": [m for m in cold if m.get("forget_score", 0) > 60]
        }
    
    def report(self) -> str:
        """生成遗忘检测报告"""
        analysis = self.analyze()
        
        lines = [
            "📊 遗忘检测报告",
            "=" * 40,
            f"总记忆（向量库）: {analysis['total']}",
            f"记忆文件: {analysis['file_count']}",
            "",
            f"🔥 热记忆（<7天）: {analysis['hot_count']}",
            f"🌡️ 温记忆（7-30天）: {analysis['warm_count']}",
            f"❄️ 冷记忆（>30天）: {analysis['cold_count']}",
            "",
        ]
        
        # 高风险冷记忆
        high_risk = analysis.get("high_risk", [])
        if high_risk:
            lines.append(f"⚠️ 高风险冷记忆 ({len(high_risk)}):")
            for m in high_risk[:5]:
                lines.append(f"  • {m['file']} (遗忘分数:{m['forget_score']})")
        
        return "\n".join(lines)


if __name__ == "__main__":
    detector = ForgetDetector()
    print(detector.report())
    print()
    analysis = detector.analyze()
    print(f"分析结果: 总记忆{analysis['total']}条")
