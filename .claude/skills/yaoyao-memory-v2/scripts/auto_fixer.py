#!/usr/bin/env python3
"""
自动修复系统 - 自修复常见问题
当检测到问题时，尝试自动修复
"""
import sys
import os
import json
import shutil
from pathlib import Path
sys.path.insert(0, str(__file__).rsplit("/", 1)[0])

try:
    from audit import log
except:
    def log(*args, **kwargs): pass


class AutoFixer:
    """自动修复器"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.skill_dir = self.script_dir.parent
        self.config_dir = self.skill_dir / "config"
        self.memory_dir = Path.home() / ".openclaw" / "workspace" / "memory"
        
    def diagnose(self) -> list:
        """诊断所有可修复问题"""
        issues = []
        
        # 1. 检查 embedding 缓存
        cache_file = self.config_dir / "embeddings_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    json.load(f)
            except:
                issues.append({
                    "type": "cache_corrupted",
                    "file": str(cache_file),
                    "problem": "Embedding 缓存文件损坏",
                    "fix": "删除缓存文件",
                    "action": lambda: cache_file.unlink() if cache_file.exists() else None
                })
        
        # 2. 检查记忆目录
        if not self.memory_dir.exists():
            issues.append({
                "type": "memory_dir_missing",
                "problem": "记忆目录不存在",
                "fix": "创建记忆目录",
                "action": lambda: self.memory_dir.mkdir(parents=True, exist_ok=True)
            })
        
        # 3. 检查配置文件
        llm_config = self.config_dir / "llm_config.json"
        if llm_config.exists():
            try:
                with open(llm_config) as f:
                    json.load(f)
            except:
                issues.append({
                    "type": "config_corrupted",
                    "file": str(llm_config),
                    "problem": "配置文件格式错误",
                    "fix": "备份并重建配置",
                    "action": lambda: self._backup_and_reset_config(llm_config)
                })
        
        # 4. 检查 feature_flag 文件
        ff_file = self.config_dir / "feature_flags.json"
        if ff_file.exists():
            try:
                with open(ff_file) as f:
                    json.load(f)
            except:
                issues.append({
                    "type": "feature_flag_corrupted",
                    "file": str(ff_file),
                    "problem": "Feature Flag 文件损坏",
                    "fix": "重置 Feature Flags",
                    "action": lambda: ff_file.unlink() if ff_file.exists() else None
                })
        
        # 5. 检查磁盘空间
        try:
            stat = shutil.disk_usage(self.memory_dir)
            if stat.free < 100 * 1024 * 1024:  # < 100MB
                issues.append({
                    "type": "low_disk_space",
                    "problem": "磁盘空间不足",
                    "fix": "建议清理过期记忆",
                    "action": None
                })
        except:
            pass
        
        return issues
    
    def _backup_and_reset_config(self, config_file: Path):
        """备份损坏的配置并重置"""
        backup = config_file.with_suffix('.json.bak')
        shutil.copy2(config_file, backup)
        default_config = {
            "embedding": {
                "api_key": "",
                "base_url": "https://ai.gitee.com/v1/embeddings",
                "model": "Qwen3-Embedding-8B",
                "dimensions": 1024
            },
            "llm": {
                "api_key": "",
                "base_url": ""
            }
        }
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        return True
    
    def auto_fix(self) -> dict:
        """执行自动修复"""
        issues = self.diagnose()
        fixed = []
        failed = []
        
        for issue in issues:
            try:
                if issue.get("action"):
                    issue["action"]()
                fixed.append({
                    "type": issue["type"],
                    "fix": issue["fix"]
                })
                log(f"[AutoFixer] 已修复: {issue['problem']}")
            except Exception as e:
                failed.append({
                    "type": issue["type"],
                    "problem": issue["problem"],
                    "error": str(e)
                })
                log(f"[AutoFixer] 修复失败: {issue['problem']} - {e}")
        
        return {
            "fixed": fixed,
            "failed": failed,
            "total": len(issues)
        }
    
    def report(self) -> str:
        """生成诊断报告"""
        issues = self.diagnose()
        
        if not issues:
            return "✅ 未检测到可自修复问题"
        
        lines = ["⚠️ 检测到以下可修复问题：", ""]
        
        for i, issue in enumerate(issues, 1):
            lines.append(f"{i}. {issue['problem']}")
            lines.append(f"   修复方案: {issue['fix']}")
        
        lines.append("")
        lines.append("执行 `auto_fixer.py fix` 进行自动修复")
        
        return "\n".join(lines)


def main():
    fixer = AutoFixer()
    
    if len(sys.argv) < 2:
        print(fixer.report())
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == 'diagnose':
        print(fixer.report())
    
    elif cmd == 'fix':
        print("🔧 执行自动修复...")
        result = fixer.auto_fix()
        
        if result['fixed']:
            print(f"\n✅ 已修复 {len(result['fixed'])} 项:")
            for f in result['fixed']:
                print(f"  - {f['fix']}")
        
        if result['failed']:
            print(f"\n❌ 修复失败 {len(result['failed'])} 项:")
            for f in result['failed']:
                print(f"  - {f['problem']}: {f['error']}")
        
        if not result['fixed'] and not result['failed']:
            print("✅ 没有需要修复的问题")
    
    elif cmd == 'auto':
        """静默修复 - 用于脚本自动调用"""
        result = fixer.auto_fix()
        return result


if __name__ == '__main__':
    main()
