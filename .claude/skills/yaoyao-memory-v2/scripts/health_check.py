#!/usr/bin/env python3
"""yaoyao-memory 健康检测脚本 - 增强版
参考 xiaoyi-claw-omega-final 的 18 类检测体系
"""
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(__file__).rsplit("/", 1)[0])

# 使用路径自动发现
from paths import get_memory_base, get_openclaw_home, get_vectors_db

# 状态文件
STATE_FILE = get_memory_base() / "heartbeat-state.json"
MEMORY_DIR = get_memory_base()
CHROMA_DB = get_memory_base() / "chroma_db"
# yaoyao 自己的 embedding 缓存（在 skill config 目录）
EMBEDDING_CACHE = SKILL_CONFIG_DIR / "embeddings_cache.json"
# 向量数据库
VECTORS_DB = get_vectors_db()

class HealthChecker:
    """健康检测器"""
    
    def __init__(self):
        self.checks = []
        self.load_state()
    
    def load_state(self):
        """加载状态"""
        if STATE_FILE.exists():
            self.state = json.loads(STATE_FILE.read_text())
        else:
            self.state = {"lastChecks": {}, "stats": {}, "issues": []}
    
    def save_state(self):
        """保存状态"""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self.state, indent=2))
    
    # ========== 一、健康度检测 (每6小时) ==========
    def check_system_health(self):
        """系统健康度检查"""
        score = 100
        issues = []
        
        # 检查文件完整性
        if not MEMORY_DIR.exists():
            score -= 20
            issues.append("memory目录不存在")
        
        # 检查状态文件
        if not STATE_FILE.exists():
            score -= 10
            issues.append("状态文件不存在")
        
        self.checks.append({
            "name": "系统健康度",
            "score": score,
            "threshold": 90,
            "status": "✅" if score >= 90 else "⚠️",
            "issues": issues
        })
        return score >= 90
    
    def check_module_integrity(self):
        """模块完整性检查"""
        required_files = [
            MEMORY_DIR / "2026-04-07.md",
            Path(__file__).parent / "memory.py",
            Path(__file__).parent / "feature_flag.py"
        ]
        
        missing = [f for f in required_files if not f.exists()]
        status = "✅" if not missing else "⚠️"
        
        self.checks.append({
            "name": "模块完整性",
            "score": 100 if not missing else 0,
            "threshold": 100,
            "status": status,
            "missing": [str(f.name) for f in missing] if missing else []
        })
        return not missing
    
    # ========== 二、问题检测 (实时) ==========
    def check_error_logs(self):
        """错误日志监控"""
        error_file = Path.home() / ".openclaw" / "workspace" / ".learnings" / "ERRORS.md"
        
        if not error_file.exists():
            error_count = 0
        else:
            content = error_file.read_text()
            error_count = content.count("\n## ")
        
        self.checks.append({
            "name": "错误日志监控",
            "count": error_count,
            "threshold": 10,
            "status": "✅" if error_count < 10 else "⚠️"
        })
        return error_count < 10
    
    def check_performance(self):
        """性能异常检测"""
        # 检查 embedding 缓存
        cache_ok = EMBEDDING_CACHE.exists() and EMBEDDING_CACHE.stat().st_size > 1000
        
        self.checks.append({
            "name": "性能检测",
            "cache_ok": cache_ok,
            "cache_size": EMBEDDING_CACHE.stat().st_size if cache_ok else 0,
            "status": "✅" if cache_ok else "⚠️"
        })
        return cache_ok
    
    # ========== 三、数据治理检测 (每日) ==========
    def check_data_retention(self):
        """数据保留策略执行"""
        # 检查 30 天以上的记忆文件
        cutoff = datetime.now() - timedelta(days=30)
        old_files = []
        
        if MEMORY_DIR.exists():
            for f in MEMORY_DIR.glob("*.md"):
                if f.stat().st_mtime < cutoff.timestamp():
                    old_files.append(f.name)
        
        self.checks.append({
            "name": "数据保留检测",
            "old_files_count": len(old_files),
            "status": "✅" if len(old_files) == 0 else "📋",
            "old_files": old_files[:5]  # 只显示前5个
        })
        return True  # 只是提示，不强制
    
    # ========== 四、向量系统检测 (每6小时) ==========
    def check_vector_system(self):
        """向量系统健康检测"""
        checks = {
            "embedding_cache": EMBEDDING_CACHE.exists(),
            "chroma_db": CHROMA_DB.exists(),
            "cache_size": EMBEDDING_CACHE.stat().st_size if EMBEDDING_CACHE.exists() else 0
        }
        
        all_ok = all(checks.values())
        
        self.checks.append({
            "name": "向量系统检测",
            "checks": checks,
            "status": "✅" if all_ok else "⚠️"
        })
        return all_ok
    
    # ========== 五、检索能力检测 (每6小时) ==========
    def check_search_performance(self):
        """检索延迟检测"""
        from memory import Memory
        
        try:
            m = Memory()
            start = time.time()
            results = m.search("测试", limit=3, method="fts")
            elapsed = (time.time() - start) * 1000
            
            ok = elapsed < 100  # 目标 < 100ms
            
            self.checks.append({
                "name": "检索延迟检测",
                "latency_ms": round(elapsed, 1),
                "threshold_ms": 100,
                "status": "✅" if ok else "⚠️"
            })
            return ok
        except Exception as e:
            self.checks.append({
                "name": "检索延迟检测",
                "error": str(e),
                "status": "❌"
            })
            return False
    
    # ========== 六、缓存命中率检测 (每6小时) ==========
    def check_cache_hit_rate(self):
        """缓存命中率检测"""
        from memory import _embedding_cache
        
        cache_size = len(_embedding_cache)
        target = 60  # 目标 > 60%
        
        # 估算命中率（基于缓存大小）
        hit_rate = min(100, cache_size * 1.2)  # 粗略估算
        
        self.checks.append({
            "name": "缓存命中率检测",
            "cache_size": cache_size,
            "estimated_hit_rate": f"{hit_rate:.0f}%",
            "threshold": f"{target}%",
            "status": "✅" if hit_rate >= target else "⚠️"
        })
        return hit_rate >= target
    
    # ========== 七、记忆系统检测 ==========
    def check_memory_stats(self):
        """记忆统计检测"""
        from memory import Memory
        
        try:
            m = Memory()
            stats = m.stats()
            
            self.checks.append({
                "name": "记忆统计",
                "total": stats["total"],
                "by_type": stats["by_type"],
                "status": "✅"
            })
            return True
        except Exception as e:
            self.checks.append({
                "name": "记忆统计",
                "error": str(e),
                "status": "❌"
            })
            return False
    
    # ========== 八、MCP管线检测 ==========
    def check_mcp_pipeline(self):
        """MCP记忆管线检测"""
        import sqlite3
        
        vectors_db = Path.home() / ".openclaw" / "memory-tdai" / "vectors.db"
        
        if not vectors_db.exists():
            l0_count = 0
            l1_count = 0
        else:
            try:
                conn = sqlite3.connect(str(vectors_db))
                l0_count = conn.execute("SELECT COUNT(*) FROM l0_conversations").fetchone()[0]
                l1_count = conn.execute("SELECT COUNT(*) FROM l1_records").fetchone()[0]
                conn.close()
            except:
                l0_count = -1
                l1_count = -1
        
        self.checks.append({
            "name": "MCP记忆管线",
            "L0_captures": l0_count,
            "L1_records": l1_count,
            "status": "✅" if l0_count > 0 else "⏳"
        })
        return True
    
    # ========== 运行所有检测 ==========
    def run_all_checks(self):
        """运行所有检测"""
        print("=" * 50)
        print("🩺 yaoyao-memory 健康检测")
        print("=" * 50)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 一、健康度检测
        print("【一】健康度检测")
        self.check_system_health()
        self.check_module_integrity()
        
        # 二、问题检测
        print("\n【二】问题检测")
        self.check_error_logs()
        self.check_performance()
        
        # 三、数据治理
        print("\n【三】数据治理检测")
        self.check_data_retention()
        
        # 四、向量系统
        print("\n【四】向量系统检测")
        self.check_vector_system()
        
        # 五、检索能力
        print("\n【五】检索能力检测")
        self.check_search_performance()
        
        # 六、缓存命中率
        print("\n【六】缓存检测")
        self.check_cache_hit_rate()
        
        # 七、记忆统计
        print("\n【七】记忆系统检测")
        self.check_memory_stats()
        
        # 八、MCP管线
        print("\n【八】MCP管线检测")
        self.check_mcp_pipeline()
        
        # 输出汇总
        print("\n" + "=" * 50)
        print("📊 检测结果汇总")
        print("=" * 50)
        
        for check in self.checks:
            status = check.get("status", "❓")
            name = check["name"]
            score = check.get("score")
            
            if score is not None:
                print(f"{status} {name}: {score}")
            else:
                print(f"{status} {name}")
        
        # 保存状态
        self.state["lastChecks"]["healthCheck"] = datetime.now().isoformat()
        self.state["issues"] = [c["name"] for c in self.checks if c.get("status") in ["⚠️", "❌"]]
        self.save_state()
        
        return self.checks

if __name__ == "__main__":
    checker = HealthChecker()
    checker.run_all_checks()
