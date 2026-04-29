#!/usr/bin/env python3
"""yaoyao-memory 初始化配置脚本 - 精美交互式"""
import json
import sys
from pathlib import Path

try:
    import readline
except:
    pass

# ═══════════════════════════════════════════════════════════
# 精美样式定义
# ═══════════════════════════════════════════════════════════
class Style:
    # 颜色
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # 前景色
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 背景色
    BG_BLACK = '\033[40m'
    BG_BLUE = '\033[44m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

def colored(text, *styles):
    """给文本添加样式"""
    if not sys.stdout.isatty():
        return text.strip() if '\n' in text else text
    return ''.join(styles) + text + Style.RESET

def print_banner():
    """打印横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ███████╗██╗   ██╗███████╗███████╗███████╗               ║
║   ██╔════╝╚██╗ ██╔╝██╔════╝██╔════╝██╔════╝               ║
║   █████╗   ╚████╔╝ █████╗  ███████╗███████╗               ║
║   ██╔══╝    ╚██╔╝  ██╔══╝  ╚════██║╚════██║               ║
║   ███████╗   ██║   ███████╗███████║███████║               ║
║   ╚══════╝   ╚═╝   ╚══════╝╚══════╝╚══════╝               ║
║                                                              ║
║   ═══════════════════════════════════════════════════       ║
║              你的智能记忆助手 v2.0.6                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝"""
    print(colored(banner, Style.CYAN, Style.BOLD))
    print()

def print_step(step, total, title):
    """打印步骤"""
    bar = "━" * 50
    filled = int(50 * step / total) if total > 0 else 0
    progress = "█" * filled + "░" * (50 - filled)
    print(colored(f"  [{progress}]", Style.CYAN))
    print(colored(f"  步骤 {step}/{total}: {title}", Style.YELLOW, Style.BOLD))
    print()

def print_category(title):
    """打印分类标题"""
    print(colored(f"\n  ┌{'─' * 46}┐", Style.BLUE))
    print(colored(f"  │ {title:<44} │", Style.BLUE, Style.BOLD))
    print(colored(f"  └{'─' * 46}┘", Style.BLUE))

def print_option(key, desc, enabled):
    """打印选项"""
    status = colored("●", Style.GREEN) if enabled else colored("○", Style.DIM)
    desc_text = colored(desc, Style.WHITE) if enabled else colored(desc, Style.DIM)
    print(f"    {status} {desc_text}")

def print_decision():
    """打印决策"""
    print()
    print(colored("  ┌─────────────────────────────────────────────┐", Style.YELLOW))
    print(colored("  │  快速选择: 按 Enter 使用默认设置             │", Style.YELLOW))
    print(colored("  │  自定义: 输入 n 关闭该功能                  │", Style.YELLOW))
    print(colored("  └─────────────────────────────────────────────┘", Style.YELLOW))

def ask_feature(category, features):
    """询问功能"""
    print_category(category)
    for key, info in features.items():
        print_option(key, info["desc"], info["enabled"])
    print_decision()
    
    for key, info in features.items():
        prompt = f"\n  {colored('►', Style.CYAN)} {info['desc']} {colored('[Y/n]', Style.DIM)}: "
        try:
            choice = input(prompt).strip().lower()
            if choice == 'n':
                info["enabled"] = False
        except:
            pass
    print()

def print_success(msg):
    """打印成功信息"""
    print(colored(f"\n  ✓ {msg}", Style.GREEN, Style.BOLD))

def print_config(config):
    """打印配置"""
    print()
    print(colored("  ╔═══════════════════════════════════════════════╗", Style.CYAN))
    print(colored("  ║             当前配置预览                    ║", Style.CYAN, Style.BOLD))
    print(colored("  ╚═══════════════════════════════════════════════╝", Style.CYAN))
    print()
    print(colored(f"  功能总数: {len(config['features']) * 4}", Style.WHITE))
    enabled = sum(1 for cat in config['features'].values() for f in cat.values() if f['enabled'])
    print(colored(f"  开启功能: {enabled}", Style.GREEN))
    print(colored(f"  关闭功能: {len(config['features']) * 4 - enabled}", Style.RED))
    print()
    print(colored(f"  每日Token限额: {config['limits']['daily_token_limit']}", Style.WHITE))
    print(colored(f"  最大上下文: {config['limits']['max_context']} 字符", Style.WHITE))
    print(colored(f"  缓存TTL: {config['limits']['cache_ttl']} 秒", Style.WHITE))

DEFAULT_FEATURES = {
    "🔍 搜索核心": {
        "vector_search": {"enabled": True, "desc": "向量搜索"},
        "fts_search": {"enabled": True, "desc": "全文搜索"},
        "parallel_search": {"enabled": True, "desc": "并行搜索"},
        "rrf_rank": {"enabled": True, "desc": "RRF排名"}
    },
    "⚡ 缓存优化": {
        "memory_cache": {"enabled": True, "desc": "内存缓存"},
        "precompute": {"enabled": True, "desc": "预计算"},
        "incremental": {"enabled": True, "desc": "增量更新"},
        "compress": {"enabled": True, "desc": "结果压缩"}
    },
    "🧠 LLM增强": {
        "rerank": {"enabled": True, "desc": "结果重排序"},
        "summary": {"enabled": True, "desc": "结果摘要"},
        "expand": {"enabled": True, "desc": "上下文扩展"},
        "explain": {"enabled": True, "desc": "查询解释"}
    },
    "🛤️ 智能路由": {
        "auto_route": {"enabled": True, "desc": "自动路由"},
        "query_rewrite": {"enabled": True, "desc": "查询改写"},
        "weight_based": {"enabled": True, "desc": "权重排序"}
    },
    "📚 学习优化": {
        "history_learn": {"enabled": True, "desc": "历史学习"},
        "feedback": {"enabled": True, "desc": "用户反馈"},
        "deduplicate": {"enabled": True, "desc": "智能去重"}
    }
}

def main():
    print_banner()
    
    features = {k: v.copy() for k, v in DEFAULT_FEATURES.items()}
    
    print_step(1, 2, "选择功能")
    for category, cat_features in features.items():
        ask_feature(category, cat_features)
    
    print_step(2, 2, "保存配置")
    
    config = {
        "name": "yaoyao-memory",
        "version": "2.0.6",
        "features": features,
        "limits": {
            "max_results": 10,
            "max_context": 500,
            "cache_ttl": 300,
            "daily_token_limit": 10000
        }
    }
    
    ws = Path.home() / ".openclaw" / "workspace" / "skills" / "yaoyao-memory" / "config"
    ws.mkdir(parents=True, exist_ok=True)
    config_file = ws / "user_config.json"
    config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    
    print_config(config)
    
    print()
    print(colored("╔══════════════════════════════════════════════════════════════╗", Style.GREEN))
    print(colored("║                      ✨ 配置完成！                          ║", Style.GREEN, Style.BOLD))
    print(colored("╚══════════════════════════════════════════════════════════════╝", Style.GREEN))
    print()
    print(colored(f"  配置文件: {config_file}", Style.DIM))
    print()

if __name__ == "__main__":
    main()
