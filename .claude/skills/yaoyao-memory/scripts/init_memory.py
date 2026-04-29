#!/usr/bin/env python3
"""
龙虾记忆系统 - 初始化脚本
首次使用时创建必要的文件结构
"""

import argparse
import sys
sys.path.insert(0, str(__file__).rsplit("/", 1)[0])
try:
    from audit import log
except:
    def log(*args, **kwargs): pass
import json
import os
from datetime import datetime
from pathlib import Path


MEMORY_MD_TEMPLATE = '''# MEMORY.md - 长期核心记忆

> 此文件存储30天+的核心知识、身份认同、重要决策。是AI的"长期记忆中枢"。

---

## 📌 记忆索引

| 标签 | 说明 |
|------|------|
| #用户 | 用户信息、偏好、习惯 |
| #技术 | 技术决策、实现、经验 |
| #产品 | 产品设计、功能、规划 |
| #项目 | 项目记录、里程碑 |
| #决策 | 重要决策及理由 |
| #错误 | 错误教训、踩坑记录 |
| #学习 | 新知识、新技能 |
| #重要 | 核心记忆，不可遗忘 |
| #待处理 | 等待执行的任务 |

---

## 👤 用户档案

> 从 USER.md 同步的核心信息

- **身份认同：** 待确认
- **语言偏好：** 待确认
- **时区：** 待确认

---

## 🤖 AI身份认同

- **名称：** 待确认
- **定位：** AI 助理
- **特质：** 贴心陪伴、持续成长

---

## 🎯 重要决策记录

> 记录影响深远的技术选型、产品方向等决策

_暂无记录_

---

## 📚 核心知识沉淀

> 从对话中提炼的可复用知识

_暂无记录_

---

## ⚠️ 错误与教训

> 记录犯过的错误，避免重犯

_暂无记录_

---

## 🔄 待处理事项

> 需要跟进的任务或问题

_暂无记录_

---

## 📝 更新日志

| 日期 | 更新内容 |
|------|----------|
| {date} | 初始化记忆系统 |

---

_此文件由AI主动维护，记录核心记忆。日常事件记录在 memory/YYYY-MM-DD.md_
'''

HEARTBEAT_STATE_TEMPLATE = {
    "lastChecks": {
        "midTermReview": None,
        "longTermUpdate": None,
        "expiredCleanup": None,
        "imaSync": None
    },
    "stats": {
        "totalMemories": 0,
        "promotedThisMonth": 0,
        "cleanedThisMonth": 0
    },
    "imaEnabled": False,
    "version": "1.0.0",
    "createdAt": "{date}"
}

DAILY_MEMORY_TEMPLATE = '''# {date} 记忆

> 每日对话记录，7-30天后自动清理或升级

---

## 📋 今日事项

_暂无记录_

---

## 💬 对话摘要

_暂无记录_

---

## 🏷️ 标签内容

### #决策
_暂无_

### #错误
_暂无_

### #重要
_暂无_

---

_此文件由AI自动维护_
'''


def init_workspace(workspace_path: Path, force: bool = False):
    """初始化工作空间"""
    
    VERSION = "1.0.0"
    
    print("🦞 龙虾记忆系统 - 初始化")
    print(f"   版本: {VERSION}")
    print("=" * 40)
    
    # 1. 创建 memory 目录
    memory_dir = workspace_path / "memory"
    if not memory_dir.exists():
        memory_dir.mkdir(parents=True)
        print("✅ 创建 memory/ 目录")
    else:
        print("ℹ️  memory/ 目录已存在")
    
    # 2. 创建 archive 子目录
    archive_dir = memory_dir / "archive"
    if not archive_dir.exists():
        archive_dir.mkdir()
        print("✅ 创建 memory/archive/ 目录")
    else:
        print("ℹ️  memory/archive/ 目录已存在")
    
    # 3. 创建 MEMORY.md
    memory_md = workspace_path / "MEMORY.md"
    if not memory_md.exists() or force:
        today = datetime.now().strftime("%Y-%m-%d")
        content = MEMORY_MD_TEMPLATE.format(date=today)
        memory_md.write_text(content, encoding="utf-8")
        print("✅ 创建 MEMORY.md（长期记忆）")
    else:
        print("ℹ️  MEMORY.md 已存在，跳过（使用 --force 覆盖）")
    
    # 4. 创建今日记忆文件
    today = datetime.now().strftime("%Y-%m-%d")
    today_file = memory_dir / f"{today}.md"
    if not today_file.exists():
        content = DAILY_MEMORY_TEMPLATE.format(date=today)
        today_file.write_text(content, encoding="utf-8")
        print(f"✅ 创建 memory/{today}.md（今日记忆）")
    else:
        print(f"ℹ️  memory/{today}.md 已存在")
    
    # 5. 创建心跳状态文件
    state_file = memory_dir / "heartbeat-state.json"
    if not state_file.exists() or force:
        state_data = HEARTBEAT_STATE_TEMPLATE.copy()
        state_data["createdAt"] = datetime.now().isoformat()
        content = json.dumps(state_data, indent=2, ensure_ascii=False)
        state_file.write_text(content, encoding="utf-8")
        print("✅ 创建 heartbeat-state.json")
    else:
        print("ℹ️  heartbeat-state.json 已存在")
    
    # 6. 检查 USER.md
    user_md = workspace_path / "USER.md"
    if user_md.exists():
        print("ℹ️  USER.md 已存在")
    else:
        print("⚠️  USER.md 不存在，建议手动创建")
    
    # 7. 检查 SOUL.md
    soul_md = workspace_path / "SOUL.md"
    if soul_md.exists():
        print("ℹ️  SOUL.md 已存在")
    else:
        print("⚠️  SOUL.md 不存在，建议手动创建")
    
    # 8. 检查 IMA 配置
    print("\n" + "-" * 40)
    ima_status = check_ima_config()
    
    print("\n" + "=" * 40)
    print("✅ 初始化完成！")
    print("\n📁 文件结构：")
    print(f"   {workspace_path}/")
    print("   ├── MEMORY.md          # 长期记忆")
    print("   ├── memory/")
    print(f"   │   ├── {today}.md     # 今日记忆")
    print("   │   ├── archive/       # 归档目录")
    print("   │   └── heartbeat-state.json")
    print("   ├── USER.md            # 用户档案")
    print("   └── SOUL.md            # AI人设")
    
    print("\n🚀 下一步：")
    print("   1. 编辑 USER.md 填写用户信息")
    print("   2. 编辑 SOUL.md 定义AI人设")
    print("   3. 开始对话，AI会自动记录重要内容")
    
    if not ima_status:
        print("\n💡 可选：配置 IMA 知识库实现云端备份")
        print("   运行: python3 scripts/init_memory.py --ima-setup")


def check_ima_config() -> bool:
    """检查 IMA 配置状态"""
    # 检查环境变量
    client_id = os.environ.get("IMA_OPENAPI_CLIENTID")
    api_key = os.environ.get("IMA_OPENAPI_APIKEY")
    
    # 检查配置文件
    if not client_id or not api_key:
        config_dir = Path.home() / ".config" / "ima"
        if config_dir.exists():
            client_id_file = config_dir / "client_id"
            api_key_file = config_dir / "api_key"
            if client_id_file.exists():
                client_id = client_id_file.read_text().strip()
            if api_key_file.exists():
                api_key = api_key_file.read_text().strip()
    
    print("🔗 IMA 知识库配置检测")
    
    if client_id and api_key:
        print("   ✅ IMA 凭证已配置")
        print("   📝 可使用 sync_ima.py 同步记忆到云端")
        return True
    else:
        print("   ⚠️  IMA 凭证未配置（可选功能）")
        print("   📖 IMA 是腾讯云端知识库，可永久存储重要记忆")
        print("   🔧 配置方式：")
        print("      1. 访问 https://ima.qq.com/agent-interface 获取凭证")
        print("      2. 运行: python3 scripts/init_memory.py --ima-setup")
        return False


def setup_ima():
    """引导用户配置 IMA"""
    print("\n🔗 IMA 知识库配置向导")
    print("=" * 40)
    print("\n📖 IMA 是腾讯提供的云端知识库服务")
    print("   可将重要记忆永久存储到云端，跨设备访问")
    print("\n📋 前置条件：")
    print("   1. 访问 https://ima.qq.com/agent-interface")
    print("   2. 获取 Client ID 和 API Key")
    print("")
    
    try:
        print("请输入 IMA 凭证（留空跳过）：")
        client_id = input("Client ID: ").strip()
        if not client_id:
            print("❌ 已跳过 IMA 配置")
            return
        
        api_key = input("API Key: ").strip()
        if not api_key:
            print("❌ 已跳过 IMA 配置")
            return
        
        # 保存到配置文件
        config_dir = Path.home() / ".config" / "ima"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        (config_dir / "client_id").write_text(client_id)
        (config_dir / "api_key").write_text(api_key)
        
        print("\n✅ IMA 凭证已保存到 ~/.config/ima/")
        
        # 询问是否启用自动同步
        print("\n📡 是否启用自动同步到 IMA？(y/n): ", end="")
        enable_auto = input().strip().lower()
        
        if enable_auto in ['y', 'yes', '是']:
            # 更新 heartbeat-state.json
            workspace = Path("~/.openclaw/workspace").expanduser()
            state_file = workspace / "memory" / "heartbeat-state.json"
            
            if state_file.exists():
                state = json.loads(state_file.read_text(encoding="utf-8"))
                state["imaEnabled"] = True
                state["lastChecks"]["imaSync"] = datetime.now().isoformat()
                state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
                print("✅ 已启用 IMA 自动同步")
                print("   心跳维护时会自动同步重要记忆到云端")
            else:
                print("⚠️  heartbeat-state.json 不存在，请先运行初始化")
                print("   运行: python3 ~/.openclaw/workspace/skills/yaoyao-memory/scripts/init_memory.py")
        else:
            print("ℹ️  未启用自动同步，可手动同步：")
            print("   python3 ~/.openclaw/workspace/skills/yaoyao-memory/scripts/sync_ima.py")
        
        print("\n🚀 IMA 配置完成！")
        
    except EOFError:
        print("\n💡 非交互模式，请手动配置：")
        print("   mkdir -p ~/.config/ima")
        print('   echo "your_client_id" > ~/.config/ima/client_id')
        print('   echo "your_api_key" > ~/.config/ima/api_key')
        print("")
        print("   启用自动同步：编辑 memory/heartbeat-state.json")
        print('   设置 "imaEnabled": true')


def main():
    parser = argparse.ArgumentParser(description="初始化龙虾记忆系统")
    parser.add_argument("--workspace", default="~/.openclaw/workspace", help="工作空间路径（默认：~/.openclaw/workspace）")
    parser.add_argument("--force", action="store_true", help="强制覆盖已存在的文件")
    parser.add_argument("--ima-setup", action="store_true", help="配置 IMA 知识库凭证")
    args = parser.parse_args()
    
    # IMA 配置模式
    if args.ima_setup:
        setup_ima()
        return
    
    workspace = Path(args.workspace).expanduser()
    
    # 如果工作空间不存在，询问是否创建
    if not workspace.exists():
        print(f"⚠️  工作空间不存在: {workspace}")
        print(f"   是否创建？(y/n): ", end="")
        try:
            response = input().strip().lower()
            if response in ['y', 'yes', '是']:
                workspace.mkdir(parents=True)
                print(f"✅ 已创建工作空间: {workspace}")
            else:
                print("❌ 已取消")
                return
        except EOFError:
            # 非交互模式，自动创建
            workspace.mkdir(parents=True)
            print(f"✅ 已创建工作空间: {workspace}")
    
    init_workspace(workspace, args.force)


if __name__ == "__main__":
    main()
