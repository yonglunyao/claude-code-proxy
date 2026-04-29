#!/usr/bin/env python3
"""yaoyao-memory 核心记忆脚本 v2.0 - 全优化版"""
import argparse
import json
import os
import re
import sys
import uuid
import hashlib
from datetime import datetime, timedelta
import sys
sys.path.insert(0, str(__file__).rsplit("/", 1)[0])
try:
    from audit import log
except:
    def log(*args, **kwargs): pass  # fallback if audit not available
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

IMPORTANCE = {"c": "Critical", "h": "High", "n": "Normal", "l": "Low"}

class MemoryCache:
    """多级缓存系统"""
    _cache = {}
    _lock = threading.Lock()
    
    @classmethod
    def get(cls, key, ttl=60):
        with cls._lock:
            if key in cls._cache:
                entry = cls._cache[key]
                if (datetime.now() - entry["time"]).total_seconds() < ttl:
                    return entry["data"]
                del cls._cache[key]
        return None
    
    @classmethod
    def set(cls, key, data):
        with cls._lock:
            cls._cache[key] = {"data": data, "time": datetime.now()}
    
    @classmethod
    def clear(cls):
        with cls._lock:
            cls._cache.clear()

class Memory:
    """记忆系统 - 全优化版"""
    
    def __init__(self):
        self.ws = Path.home() / ".openclaw" / "workspace"
        self.mem_dir = self.ws / "memory"
        self.meta_file = self.mem_dir / ".meta.json"
        self._meta = self._load_meta()
        self.load()
    
    def _load_meta(self):
        if self.meta_file.exists():
            try:
                return json.loads(self.meta_file.read_text(encoding="utf-8"))
            except:
                pass
        return {"index": [], "last_load": None, "cache": {}}
    
    def _save_meta(self):
        try:
            self.meta_file.parent.mkdir(parents=True, exist_ok=True)
            self.meta_file.write_text(json.dumps(self._meta, ensure_ascii=False), encoding="utf-8")
        except:
            pass
    
    def load(self, force=False):
        now = datetime.now()
        if not force and self._meta.get("last_load"):
            last = datetime.fromisoformat(self._meta["last_load"])
            if (now - last).total_seconds() < 60:
                return
        self._meta["last_load"] = now.isoformat()
        self._meta["index"] = []
        for f in self.mem_dir.glob("*.md"):
            if f.name == "archive" or f.name.startswith("."):
                continue
            try:
                content = f.read_text(encoding="utf-8")
                for block in re.split(r"\n## ", content):
                    lines = block.split("\n", 1)
                    if len(lines) > 1 and lines[0].strip():
                        self._meta["index"].append({
                            "id": str(uuid.uuid4())[:8],
                            "title": lines[0].strip()[:50],
                            "type": "info",
                            "importance": "Normal",
                            "file": f.name
                        })
            except:
                pass
        self._save_meta()
    
    # ========== 搜索核心优化 ==========
    def _vector_search(self, query, limit=3):
        """向量搜索（模拟）"""
        q_lower = query.lower()
        results = []
        for item in self._meta.get("index", []):
            if q_lower in item.get("title", "").lower():
                results.append({"s": item.get("title", ""), "score": 0.9, "type": item.get("type", "info")})
        return results[:limit]
    
    def _fts_search(self, query, limit=3):
        """全文搜索"""
        q_lower = query.lower()
        results = []
        for item in self._meta.get("index", []):
            if q_lower in item.get("title", "").lower():
                results.append({"s": item.get("title", ""), "score": 0.8, "type": item.get("type", "info")})
        return results[:limit]
    
    def _parallel_search(self, query, limit=3):
        """并行搜索 - 多策略并发"""
        with ThreadPoolExecutor(max_workers=3) as executor:
            v_future = executor.submit(self._vector_search, query, limit)
            f_future = executor.submit(self._fts_search, query, limit)
            v_results = v_future.result()
            f_results = f_future.result()
        return v_results, f_results
    
    def _rrf_rank(self, results_list, k=60):
        """RRF排名算法"""
        scores = {}
        for results in results_list:
            for i, r in enumerate(results):
                key = r["s"]
                score = scores.get(key, 0) + 1 / (k + i + 1)
                scores[key] = score
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    def hybrid_search(self, query, limit=3):
        """混合搜索 - 向量+FTS+RRF"""
        cache_key = f"hybrid_{query}_{limit}"
        cached = MemoryCache.get(cache_key, 60)
        if cached:
            return cached
        v_results, f_results = self._parallel_search(query, limit)
        rrf_results = self._rrf_rank([v_results, f_results])
        output = [{"title": title, "score": score} for title, score in rrf_results[:limit]]
        MemoryCache.set(cache_key, output)
        return output
    
    # ========== 缓存优化 ==========
    def get_cached(self, key):
        """预计算缓存获取"""
        return MemoryCache.get(f"cached_{key}", 300)
    
    def set_cached(self, key, data):
        """预计算缓存设置"""
        MemoryCache.set(f"cached_{key}", data)
    
    def clear_cache(self):
        """清理缓存"""
        MemoryCache.clear()
    
    # ========== LLM增强 ==========
    def rerank_results(self, results, query):
        """重排序 - 基于query权重"""
        if not results:
            return results
        query_words = set(query.lower().split())
        for r in results:
            title_words = set(r.get("title", "").lower().split())
            overlap = len(query_words & title_words)
            r["rerank_score"] = r.get("score", 0.5) * (1 + overlap * 0.1)
        return sorted(results, key=lambda x: x.get("rerank_score", 0), reverse=True)
    
    def summarize_results(self, results, max_chars=100):
        """结果摘要"""
        if not results:
            return []
        for r in results:
            title = r.get("title", "")
            if len(title) > max_chars:
                r["summary"] = title[:max_chars] + "..."
            else:
                r["summary"] = title
        return results
    
    # ========== 智能路由 ==========
    def route_query(self, query):
        """智能路由 - 判断使用什么搜索策略"""
        query_lower = query.lower()
        if any(k in query_lower for k in ["怎么", "如何", "what", "how"]):
            return "hybrid"  # 复杂查询用混合搜索
        if any(k in query_lower for k in ["找出", "查找", "find", "search"]):
            return "fts"  # 精确查找用FTS
        if len(query.split()) <= 2:
            return "vector"  # 短查询用向量
        return "hybrid"
    
    def smart_search(self, query, limit=3):
        """智能搜索 - 自动路由"""
        route = self.route_query(query)
        if route == "fts":
            results = self._fts_search(query, limit)
        elif route == "vector":
            results = self._vector_search(query, limit)
        else:
            v_results, f_results = self._parallel_search(query, limit)
            results = v_results + f_results
        results = self.rerank_results(results, query)
        return self.summarize_results(results[:limit])
    
    # ========== 学习优化 ==========
    def learn_from_history(self, query, selected_result):
        """从历史中学习 - 记录用户偏好"""
        history_key = "query_history"
        history = self._meta.get("cache", {}).get(history_key, [])
        history.append({
            "query": query,
            "selected": selected_result,
            "timestamp": datetime.now().isoformat()
        })
        # 只保留最近20条
        history = history[-20:]
        self._meta["cache"][history_key] = history
        self._save_meta()
    
    def deduplicate(self, data):
        """去重 - 基于内容hash"""
        data_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
        existing_hashes = self._meta.get("cache", {}).get("data_hashes", [])
        if data_hash in existing_hashes:
            return False
        existing_hashes.append(data_hash)
        self._meta["cache"]["data_hashes"] = existing_hashes[-100:]
        self._save_meta()
        return True
    
    # ========== 核心接口 ==========
    def sync_start(self):
        """超轻量会话开始"""
        return {
            "b": "main",
            "t": self._get_type_stats(),
            "n": len(self._meta.get("index", [])),
            "h": self._get_high_count()
        }
    
    def _get_type_stats(self):
        stats = {}
        for item in self._meta.get("index", []):
            t = item.get("type", "info")
            stats[t] = stats.get(t, 0) + 1
        return stats
    
    def _get_high_count(self):
        return sum(1 for item in self._meta.get("index", []) if item.get("importance") in ["Critical", "High"])
    
    def get(self, topic, limit=3):
        """获取记忆"""
        topic_lower = topic.lower()
        results = []
        for item in self._meta.get("index", []):
            if topic_lower in item.get("title", "").lower():
                results.append({
                    "id": item.get("id", ""),
                    "t": item.get("title", ""),
                    "tp": item.get("type", "info")[0].upper(),
                    "i": item.get("importance", "Normal")[0].upper()
                })
                if len(results) >= limit:
                    break
        return {"topic": topic, "mem": results, "total": len(results)}
    
    def search(self, query, limit=3, method="auto"):
        """搜索 - 支持多种方法"""
        if method == "auto":
            results = self.smart_search(query, limit)
        elif method == "hybrid":
            results = self.hybrid_search(query, limit)
        elif method == "parallel":
            v, f = self._parallel_search(query, limit)
            results = v + f
        else:
            results = self._fts_search(query, limit)
        return {"query": query, "results": results, "method": method, "total": len(results)}
    
    def stats(self):
        index = self._meta.get("index", [])
        by_type = {}
        by_imp = {"Critical": 0, "High": 0, "Normal": 0, "Low": 0}
        for item in index:
            by_type[item.get("type", "info")] = by_type.get(item.get("type", "info"), 0) + 1
            by_imp[item.get("importance", "Normal")] = by_imp.get(item.get("importance", "Normal"), 0) + 1
        return {"total": len(index), "by_type": by_type, "by_importance": by_imp}

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    
    sub.add_parser("sync-start")
    
    g = sub.add_parser("get")
    g.add_argument("topic")
    g.add_argument("-l", "--limit", type=int, default=3)
    
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("-l", "--limit", type=int, default=3)
    s.add_argument("-m", "--method", default="auto", choices=["auto", "hybrid", "parallel", "fts"])
    
    sub.add_parser("stats")
    sub.add_parser("clear-cache")

    args = parser.parse_args()
    if not args.cmd:
        return
    
    m = Memory()
    
    if args.cmd == "sync-start":
        print(json.dumps(m.sync_start(), indent=2, ensure_ascii=False))
    elif args.cmd == "get":
        print(json.dumps(m.get(args.topic, args.limit), indent=2, ensure_ascii=False))
    elif args.cmd == "search":
        print(json.dumps(m.search(args.query, args.limit, args.method), indent=2, ensure_ascii=False))
    elif args.cmd == "stats":
        print(json.dumps(m.stats(), indent=2, ensure_ascii=False))
    elif args.cmd == "clear-cache":
        m.clear_cache()
        print(json.dumps({"status": "cache_cleared"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
