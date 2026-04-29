#!/usr/bin/env python3
"""
记忆关联图谱模块 - v1.0.0
分析记忆之间的关联，生成可视化图谱数据

功能：
1. 提取记忆中的关键词和实体
2. 计算记忆之间的关联强度
3. 生成图谱数据（节点+边）
4. 支持导出为 JSON 供可视化使用
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

# 配置
MEMORY_DIR = Path.home() / ".openclaw" / "workspace" / "memory"
GRAPH_FILE = MEMORY_DIR / ".memory_graph.json"

# 关联阈值
MIN_COMMON_WORDS = 2  # 最少共同关键词数
ENTITY_PATTERNS = [
    r"[A-Z][a-z]+(?:[A-Z][a-z]+)+",  # CamelCase
    r"[\w]+(?:[-_][\w]+)+",            # snake_case / kebab-case
    r"「[^」]+」",                       # 中文引号
    r"《[^》]+》",                       # 书名号
]

class MemoryGraph:
    """记忆关联图谱"""
    
    def __init__(self):
        self.memory_dir = MEMORY_DIR
        self.graph_file = GRAPH_FILE
        self._load_graph()
    
    def _load_graph(self):
        """加载图谱数据"""
        if self.graph_file.exists():
            try:
                self.graph = json.loads(self.graph_file.read_text(encoding="utf-8"))
            except:
                self.graph = {"nodes": [], "edges": []}
        else:
            self.graph = {"nodes": [], "edges": []}
    
    def _save_graph(self):
        """保存图谱数据"""
        try:
            self.graph_file.parent.mkdir(parents=True, exist_ok=True)
            self.graph_file.write_text(
                json.dumps(self.graph, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except:
            pass
    
    def _extract_entities(self, text: str) -> Set[str]:
        """提取实体（关键词）"""
        entities = set()
        
        # 提取中文词组（2-4字）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        entities.update(chinese_words)
        
        # 提取英文词组
        english_words = re.findall(r'[A-Za-z]{3,}', text)
        entities.update(w.lower() for w in english_words)
        
        # 提取特殊模式
        for pattern in ENTITY_PATTERNS:
            matches = re.findall(pattern, text)
            entities.update(matches)
        
        return entities
    
    def _extract_tags(self, content: str) -> List[str]:
        """提取记忆标签"""
        tags = []
        
        # 提取 #标签
        tag_matches = re.findall(r'#(\w+)', content)
        tags.extend(tag_matches)
        
        # 提取 ## 标题
        heading_matches = re.findall(r'^##?\s*(.+?)$', content, re.MULTILINE)
        tags.extend(heading_matches[:3])  # 最多3个标题
        
        return list(set(tags))
    
    def _calculate_similarity(self, entities1: Set[str], entities2: Set[str]) -> float:
        """计算两个记忆的相似度"""
        if not entities1 or not entities2:
            return 0.0
        
        intersection = len(entities1 & entities2)
        union = len(entities1 | entities2)
        
        if union == 0:
            return 0.0
        
        return intersection / union  # Jaccard 相似度
    
    def build_graph(self, force_rebuild: bool = False) -> Dict:
        """
        构建记忆图谱
        - force_rebuild: 是否强制重建
        """
        # 如果不是强制重建，尝试使用缓存
        if not force_rebuild and self.graph.get("nodes"):
            return self.graph
        
        memories = []
        
        # 扫描所有记忆文件
        for f in self.memory_dir.glob("*.md"):
            if f.name.startswith(".") or "合并版" in f.name:
                continue
            
            try:
                content = f.read_text(encoding="utf-8")
                entities = self._extract_entities(content)
                tags = self._extract_tags(content)
                
                memories.append({
                    "id": f.stem,
                    "filename": f.name,
                    "entities": list(entities),
                    "tags": tags,
                    "content_preview": content[:200]
                })
            except:
                pass
        
        # 构建节点
        nodes = []
        for mem in memories:
            nodes.append({
                "id": mem["id"],
                "filename": mem["filename"],
                "tags": mem["tags"],
                "entity_count": len(mem["entities"]),
                "preview": mem["content_preview"][:50]
            })
        
        # 构建边（关联）
        edges = []
        for i, mem1 in enumerate(memories):
            for j, mem2 in enumerate(memories[i+1:], start=i+1):
                similarity = self._calculate_similarity(
                    set(mem1["entities"]),
                    set(mem2["entities"])
                )
                
                if similarity >= 0.1:  # 阈值
                    edges.append({
                        "source": mem1["id"],
                        "target": mem2["id"],
                        "weight": round(similarity, 3)
                    })
        
        self.graph = {"nodes": nodes, "edges": edges}
        self._save_graph()
        
        return self.graph
    
    def get_related(self, memory_id: str, limit: int = 5) -> List[Dict]:
        """获取与指定记忆关联的其他记忆"""
        related = []
        
        for edge in self.graph.get("edges", []):
            if edge["source"] == memory_id:
                related.append({
                    "id": edge["target"],
                    "weight": edge["weight"]
                })
            elif edge["target"] == memory_id:
                related.append({
                    "id": edge["source"],
                    "weight": edge["weight"]
                })
        
        related.sort(key=lambda x: x["weight"], reverse=True)
        return related[:limit]
    
    def get_hub_memories(self, limit: int = 5) -> List[Dict]:
        """获取中心度最高的记忆（关联最多）"""
        degrees = defaultdict(int)
        
        for edge in self.graph.get("edges", []):
            degrees[edge["source"]] += 1
            degrees[edge["target"]] += 1
        
        hub_ids = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        nodes_map = {n["id"]: n for n in self.graph.get("nodes", [])}
        
        return [
            {"id": hid, "degree": deg, "node": nodes_map.get(hid, {})}
            for hid, deg in hub_ids
        ]
    
    def report(self) -> str:
        """生成图谱报告"""
        self.build_graph()
        
        nodes_count = len(self.graph.get("nodes", []))
        edges_count = len(self.graph.get("edges", []))
        hubs = self.get_hub_memories(5)
        
        lines = [
            "🔗 记忆关联图谱",
            "=" * 40,
            f"节点（记忆）: {nodes_count}",
            f"边（关联）: {edges_count}",
            "",
        ]
        
        if hubs:
            lines.append("🔥 中心记忆（关联最多）:")
            for h in hubs:
                tags = h["node"].get("tags", [])[:3]
                lines.append(f"  • {h['id']} ({h['degree']}个关联) {tags}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    graph = MemoryGraph()
    print(graph.report())
