#!/usr/bin/env python3
"""
记忆对比模块 - v1.0.0
对比两条记忆的差异

功能：
1. 对比两个文件的差异
2. 高亮显示新增/删除/修改的行
3. 生成可读性强的对比报告
"""

import difflib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MEMORY_DIR = Path.home() / ".openclaw" / "workspace" / "memory"

class MemoryDiff:
    """记忆对比器"""
    
    def __init__(self):
        self.memory_dir = MEMORY_DIR
    
    def diff_files(self, file1: str, file2: str) -> Dict:
        """
        对比两个文件
        """
        path1 = self.memory_dir / file1
        path2 = self.memory_dir / file2
        
        if not path1.exists():
            return {"error": f"文件不存在: {file1}"}
        if not path2.exists():
            return {"error": f"文件不存在: {file2}"}
        
        try:
            content1 = path1.read_text(encoding="utf-8")
            content2 = path2.read_text(encoding="utf-8")
            
            return self.diff_content(content1, content2, file1, file2)
        except Exception as e:
            return {"error": str(e)}
    
    def diff_content(self, content1: str, content2: str, name1: str = "A", name2: str = "B") -> Dict:
        """
        对比两段内容
        """
        lines1 = content1.splitlines()
        lines2 = content2.splitlines()
        
        # 使用 difflib 生成 unified diff
        diff = list(difflib.unified_diff(
            lines1, lines2,
            fromfile=name1,
            tofile=name2,
            lineterm=''
        ))
        
        # 统计
        added = len([l for l in diff if l.startswith('+') and not l.startswith('+++')])
        removed = len([l for l in diff if l.startswith('-') and not l.startswith('---')])
        unchanged = len(lines1) - removed if lines1 else 0
        
        return {
            "added": added,
            "removed": removed,
            "unchanged": unchanged,
            "diff_lines": diff[:50],  # 限制输出行数
            "total_changes": added + removed
        }
    
    def diff_memories(self, query1: str, query2: str, limit: int = 3) -> Dict:
        """
        对比两条最匹配的记忆（通过搜索）
        """
        # 简单的文本搜索
        memories = list(self.memory_dir.glob("*.md"))
        memories = [m for m in memories if not m.name.startswith('.') and '合并版' not in m.name]
        
        def search_memory(query: str) -> List[Tuple[Path, int]]:
            results = []
            query_lower = query.lower()
            for m in memories:
                try:
                    content = m.read_text(encoding="utf-8").lower()
                    count = content.count(query_lower)
                    if count > 0:
                        results.append((m, count))
                except:
                    pass
            return sorted(results, key=lambda x: x[1], reverse=True)
        
        results1 = search_memory(query1)
        results2 = search_memory(query2)
        
        if not results1 or not results2:
            return {"error": "未找到匹配的记忆"}
        
        file1 = results1[0][0].name
        file2 = results2[0][0].name
        
        return {
            "matched_files": [file1, file2],
            "diff": self.diff_files(file1, file2)
        }
    
    def format_diff(self, diff_result: Dict) -> str:
        """格式化 diff 输出"""
        if "error" in diff_result:
            return f"错误: {diff_result['error']}"
        
        lines = [
            "📝 记忆对比报告",
            "=" * 40,
            f"新增行: +{diff_result['added']}",
            f"删除行: -{diff_result['removed']}",
            f"未变化: {diff_result['unchanged']}",
            "",
            "差异内容:",
            "-" * 40,
        ]
        
        for line in diff_result.get("diff_lines", [])[:30]:
            lines.append(line)
        
        return "\n".join(lines)
    
    def report(self) -> str:
        """生成对比报告"""
        memories = list(self.memory_dir.glob("*.md"))
        memories = [m for m in memories if not m.name.startswith('.') and '合并版' not in m.name]
        
        lines = [
            "📝 记忆对比工具",
            "=" * 40,
            f"可用记忆: {len(memories)}",
            "",
            "使用方法:",
            "  diff_files(file1, file2) - 对比两个文件",
            "  diff_content(c1, c2) - 对比两段内容",
            "  diff_memories(query1, query2) - 对比最匹配的记忆",
        ]
        
        return "\n".join(lines)


if __name__ == "__main__":
    diff_tool = MemoryDiff()
    
    print(diff_tool.report())
    
    # 测试对比最近两个日记文件
    print("\n=== 对比测试 ===")
    diaries = sorted([m.name for m in diff_tool.memory_dir.glob("*.md") 
                     if m.name.startswith("2026-") and '合并版' not in m.name])
    
    if len(diaries) >= 2:
        result = diff_tool.diff_files(diaries[0], diaries[-1])
        print(diff_tool.format_diff(result))
