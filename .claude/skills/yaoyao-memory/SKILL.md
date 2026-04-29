---
name: yaoyao-memory
description: |
  四层渐进式长时记忆系统，让 AI 跨会话保持上下文、沉淀知识、持续进化。
  
  【核心设计：静默自动】
  AI 自动识别、记录、整理记忆，无需用户确认。永不主动询问"是否记录"。
---

# 摇摇记忆系统 v3.0

> 整合 LLM Memory Integration v2.1.4 精华：智能路由、查询改写、LLM 增强、反馈学习

> 基于 git-notes-memory 灵感，四层渐进式记忆 + 全自动静默操作 + 安全增强。

## 核心理念

**记忆不是存储，而是进化。AI 全自动运行，不打扰用户。**

---

## 重要性等级

| 标志 | 含义 | 触发场景 |
|------|------|----------|
| `-i c` | Critical 关键 | 用户明确说"永远记住"、"绝不遗忘" |
| `-i h` | High 高 | 决策、偏好、架构选择、用户纠正 |
| `-i n` | Normal 普通 | 一般信息（默认） |
| `-i l` | Low 低 | 临时笔记，可能被清理 |

---

## 记忆类型（自动分类）

| 类型 | 触发词 | 示例 |
|------|--------|------|
| `decision` | 决定、用、选择、采用 | "决定用 PostgreSQL" |
| `preference` | 喜欢、偏好、更倾向 | "喜欢深色主题" |
| `learning` | 学会、理解、发现 | "学会了 async/await" |
| `task` | 需要做、计划、下一步 | "需要修复登录 bug" |
| `question` | 好奇、研究、调查 | "想研究微服务架构" |
| `note` | 注意、重要、记住 | "项目周一上线" |
| `progress` | 完成、达成、里程碑 | "完成了用户认证" |
| `info` | 默认 | 其他信息 |

---

## 静默操作规则

**绝对禁止：**
- ❌ "要不要记录这个？"
- ❌ "我会记住的"
- ❌ "已保存到记忆"
- ❌ 主动提及记忆操作

**正确做法：**
- ✅ 检测到重要信息 → 直接静默记录
- ✅ 用户询问记忆 → 静默检索后回答
- ✅ 只需要做：**自动记录，不问用户**

---

## 记忆写入

```bash
# 升级近期记忆到长期（需指定天数）
python3 scripts/promote.py --days 7

# 智能更新（需要配置 LLM）
python3 scripts/smart_memory_update.py

# 生成摘要
python3 scripts/summarize.py --type daily
```

**自动识别写入（推荐）：**
- 用户做出决策 → 自动记录为 decision，高重要性
- 用户表达偏好 → 自动记录为 preference，高重要性
- 用户学到知识 → 自动记录为 learning，普通重要性
- 用户设置任务 → 自动记录为 task，普通重要性

---

## 记忆检索

```bash
# 获取主题相关记忆（模糊匹配 topics）
python3 scripts/memory.py get <topic>

# 全文搜索
python3 scripts/memory.py search <query>

# 查看统计
python3 scripts/memory.py stats

# 清除缓存
python3 scripts/memory.py clear-cache

# 会话开始同步
python3 scripts/memory.py sync-start
```

---



## 增强检索（整合 LLM Memory Integration）

### 智能路由

根据查询复杂度自动选择模式：

| 模式 | 触发条件 | 特点 |
|------|----------|------|
| `fast` | 短查询、关键词 | 仅 FTS，<10ms |
| `balanced` | 普通问题 | FTS + 向量混合 |
| `full` | 复杂问题 | FTS + 向量 + LLM 分析 |

### 查询改写

自动优化查询词：

```bash
# 拼写纠正
vsearch "推送规责"  →  自动纠正为 "推送规则"

# 同义词扩展
vsearch "记忆"      →  扩展：记忆/存储/记住/沉淀

# 语义扩展
vsearch "配置"      →  扩展：配置/设置/安装/初始化
```

### LLM 增强

需要配置 `LLM_API_KEY`：

```bash
# 结果解释（为什么这条记忆相关）
vsearch "用户偏好" --explain

# 结果摘要（自动生成摘要）
vsearch "记忆系统配置" --summarize
```

### 反馈学习

记录用户选择，持续优化排序：

```bash
# 记录反馈
python3 scripts/feedback.py record --query "配置" --selected 3

# 查看高频查询
python3 scripts/history.py top
```

## 实体提取

自动提取实体便于检索：
- **显式字段**：topic、subject、name、category
- **标签**：#技术、#用户、#决策
- **引号短语**："REST API"、"用户认证"
- **大写词**：React、PostgreSQL、Monday

---

## 会话生命周期

### Session Start（每次会话开始）

```bash
python3 scripts/memory.py sync-start
```

（无额外输出，执行成功返回空）

---

## 四层记忆架构（参考小艺Claw优化）

```
┌─────────────────────────────────────────────────────┐
│  L0 对话层 (Conversations)                            │
│  存储：conversations.jsonl + vectors              │
│  记录：1002条对话 / 666条向量 (66.5%覆盖)         │
│  工具：tdai_conversation_search (FTS5对话历史)    │
│  时长：当前会话                                    │
│  自动：实时捕获对话                                │
├─────────────────────────────────────────────────────┤
│  L1 记忆层 (Records)                              │
│  存储：records + vectors.db (向量索引)               │
│  记录：13条 / 13条向量 (100%覆盖)                 │
│  工具：tdai_memory_search (FTS5+向量混合)          │
│  时长：7-30天                                    │
│  自动：每日摘要 + 向量化                          │
├─────────────────────────────────────────────────────┤
│  L2 长期层 (Long-term)                           │
│  存储：MEMORY.md + persona.md + scene_blocks      │
│  记录：159行 (长期记忆)                           │
│  工具：memory.py get / search                 │
│  时长：30天+                                     │
│  触发：被引用≥3次 或 用户明确要求                │
├─────────────────────────────────────────────────────┤
│  L3 档案层 (Archive)                             │
│  存储：IMA 知识库 (云端备份)                      │
│  组件：2nd-brain (个人知识库)                   │
│        ontology (知识图谱，1条实体)                │
│  时长：永久                                      │
│  触发：核心知识、重要决策                        │
└─────────────────────────────────────────────────────┘
```

### 数据统计

| 层级 | 记录数 | 向量数 | 覆盖率 |
|------|--------|--------|--------|
| L0 对话 | 1002条 | 666条 | 66.5% |
| L1 记忆 | 13条 | 13条 | 100% |
| L2 长期 | 159行 | - | - |
| L3 档案 | IMA云端 | - | - |

### 核心组件

| 组件 | 技术 | 用途 |
|------|------|------|
| vector-memory-hack | TF-IDF | 快速文档检索 (<10ms) |
| memory-tencentdb | FTS5+向量 | 动态记忆混合搜索 |
| tdai_memory_search | LLM+向量+FTS | 结构化记忆召回 |
| tdai_conversation_search | FTS5 | 对话历史搜索 |
| yaoyao-memory | 文件型 | 纯文件记忆系统 |
| git-notes-memory | Git Notes | 知识图谱管理 |
| 2nd-brain | IMA | 个人知识库 |
| ontology | IMA | 结构化知识图谱 |

### 向量模型

| 配置 | 值 |
|------|-----|
| Provider | Gitee AI |
| 模型 | Qwen3-Embedding-8B |
| 维度 | 4096维 |
| 数据库 | vectors.db / 36MB |

---

## 记忆流向

```
L0(会话) → L1(每日) → L2(30天+) → L3(永久)
  ↓          ↓          ↓          ↓
  自动      自动       引用≥3    手动/IMA
```

---

## 心跳维护（自动执行）

心跳时自动轮换执行（无需用户确认）：

| 检查项 | 频率 | 操作 |
|--------|------|------|
| 中期记忆审查 | 每次心跳 | 识别需升级内容 |
| 长期记忆更新 | 每日 | 更新 MEMORY.md |
| 过期清理 | 每周 | 删除>30天记忆 |
| IMA 同步 | 每日 | 同步重要决策到云端 |

---

## 文件结构

```
workspace/
├── MEMORY.md              # 长期记忆
├── memory/
│   ├── YYYY-MM-DD.md     # 中期记忆（每日）
│   ├── heartbeat-state.json
│   └── archive/           # 归档
└── scripts/
    ├── memory.py              # 核心记忆脚本
    ├── init_memory.py         # 初始化
    ├── promote.py             # 升级记忆
    ├── cleanup.py             # 清理过期
    ├── sync_ima.py           # IMA同步
    ├── summarize.py           # 生成摘要
    ├── one_click_setup.py     # 一键安装配置
    ├── check_coverage.py      # 向量覆盖率检查
    ├── optimize_vector_system.py  # 向量系统优化
    ├── hybrid_memory_search.py # 混合记忆搜索
    ├── smart_memory_update.py  # 智能记忆更新
    ├── update_persona.py       # 用户画像更新
    ├── update_l3_profile.py    # L3档案更新
    ├── fast_search.py          # 快速搜索
    ├── parallel_search.py      # 并行搜索
    ├── generate_index.py       # 生成索引
    └── migrate.py              # 数据迁移
```

---

## 标签系统

| 标签 | 含义 | 示例 |
|------|------|------|
| #决策 | 技术/产品决策 | #决策 用 PostgreSQL |
| #偏好 | 用户偏好习惯 | #偏好 喜欢简洁代码 |
| #错误 | 踩坑教训 | #错误 忘记校验输入 |
| #技术 | 技术知识 | #技术 Redis缓存 |
| #用户 | 用户信息 | #用户 喜欢深色主题 |
| #重要 | 核心记忆 | #重要 API密钥不记录 |
| #待处理 | 待办事项 | #待处理 下周演示 |

---

## 隐私规则

**永不记录：**
- ❌ 密码、密钥、Token
- ❌ 银行卡、身份证
- ❌ 用户明确要求不记录的

**自动跳过：**
- 临时对话、一次性问题
- 可从代码推导的信息
- 重复已有记忆

## 安全说明

### 声明的权限 vs 实际行为

| 功能 | 是否启用 | 说明 |
|------|----------|------|
| 静默自动记录 | ✅ 默认关闭 | 需用户明确启用 heartbeat |
| 外部 API 调用 | ✅ 可选 | 仅当配置了 API Key 时生效 |
| 写入本地文件 | ✅ 必需 | 仅在 `~/.openclaw/workspace/memory/` |
| 云端同步 | ❌ 默认禁用 | 需用户主动配置 IMA |

### 环境变量（可选）

| 变量 | 用途 | 说明 |
|------|------|------|
| `GITEE_AI_KEY` | 向量嵌入 | 需要自行申请，无默认 |
| `LLM_API_KEY` | 结果解释/摘要 | 需要自行申请，无默认 |
| `IMA_OPENAPI_CLIENTID` | IMA 云端同步 | 需要自行申请，无默认 |
| `IMA_OPENAPI_APIKEY` | IMA 云端同步 | 需要自行申请，无默认 |

**重要**：本技能不读取 `openclaw.json` 或其他技能的凭证。

### 静默行为的边界

heartbeat 时仅执行预设的检查和维护任务：
- 检查 memory/ 目录的今日记忆文件
- 更新 heartbeat-state.json 状态
- **不会**自动发送网络请求（除非配置了 API Key）
- **不会**自动同步到云端（除非用户启用 IMA）

如需完全禁用记忆系统，可删除 `~/.openclaw/workspace/memory/` 目录。

### 本地模型支持

**支持本地部署，完全不发送数据到外部：**

| 模型类型 | 推荐方案 | 配置示例 |
|----------|----------|----------|
| Embedding | Ollama + nomic-embed-text | `provider: ollama`, `base_url: http://localhost:11434` |
| LLM | Ollama + qwen2.5 | `provider: ollama`, `base_url: http://localhost:11434` |

**配置步骤：**
1. 安装 [Ollama](https://ollama.ai)
2. 下载模型：`ollama pull nomic-embed-text` / `ollama pull qwen2.5`
3. 复制 `config/llm_config.example.json` 为 `config/llm_config.json`
4. 修改配置：

```json
{
  "llm": {
    "provider": "ollama",
    "base_url": "http://localhost:11434",
    "model": "qwen2.5"
  },
  "embedding": {
    "provider": "ollama",
    "base_url": "http://localhost:11434",
    "model": "nomic-embed-text",
    "dimensions": 768
  }
}
```

**隐私保证**：使用本地模型时，记忆数据**永远不会**离开你的机器。

### 审计日志

记录所有记忆操作，方便追溯和隐私审查：

```bash
# 查看审计统计
python3 scripts/audit.py stats

# 查看最近操作
python3 scripts/audit.py recent

# 清除审计日志
python3 scripts/audit.py clear
```

**日志位置**：`memory/audit.log`

**记录的操作类型**：
| 操作 | 说明 |
|------|------|
| `init` | 初始化工作空间 |
| `sync_start` | 会话开始同步 |
| `get` | 查询记忆 |
| `search` | 搜索记忆 |
| `sync_ima` | 云端同步 |

---

## 与 memory-tencentdb 联动

**强烈推荐安装 memory-tencentdb 插件：**
```bash
openclaw plugins install @tencentdb-agent-memory/memory-tencentdb
```

| 组件 | 功能 | 触发 |
|------|------|------|
| yaoyao-memory | 手动+自动记录 | 静默自动 |
| memory-tencentdb | 自动捕获+召回 | 实时 |

---

## 脚本功能详解

| 脚本 | 功能 | 用法 |
|------|------|------|
| `memory.py` | 核心记忆CLI（优化版） | `python3 scripts/memory.py stats\|get\|search` |
| `smart_memory_update.py` | 智能记忆更新 | `python3 scripts/smart_memory_update.py` |
| `init_memory.py` | 初始化记忆系统 | `python3 scripts/init_memory.py` |
| `promote.py` | 记忆升级(L0→L1→L2→L3) | `python3 scripts/promote.py` |
| `cleanup.py` | 清理过期记忆 | `python3 scripts/cleanup.py` |
| `sync_ima.py` | IMA云端同步 | `python3 scripts/sync_ima.py` |
| `summarize.py` | 生成记忆摘要 | `python3 scripts/summarize.py` |
| `one_click_setup.py` | 一键安装配置 | `python3 scripts/one_click_setup.py` |
| `check_coverage.py` | 检查向量覆盖率 | `python3 scripts/check_coverage.py` |
| `optimize_vector_system.py` | 优化向量系统 | `python3 scripts/optimize_vector_system.py` |
| `hybrid_memory_search.py` | 混合记忆搜索 | `python3 scripts/hybrid_memory_search.py <query>` |
| `smart_memory_update.py` | 智能记忆更新 | `python3 scripts/smart_memory_update.py` |
| `update_persona.py` | 更新用户画像 | `python3 scripts/update_persona.py` |
| `update_l3_profile.py` | 更新L3档案 | `python3 scripts/update_l3_profile.py` |
| `fast_search.py` | 快速搜索 | `python3 scripts/fast_search.py <query>` |
| `parallel_search.py` | 并行搜索 | `python3 scripts/parallel_search.py <query>` |
| `generate_index.py` | 生成索引 | `python3 scripts/generate_index.py` |
| `migrate.py` | 数据迁移 | `python3 scripts/migrate.py` |

---

## 系统要求

| 依赖 | 说明 | 检查命令 |
|------|------|----------|
| `sqlite3` | SQLite CLI（用于 FTS 搜索） | `sqlite3 --version` |
| Python 3.8+ | Python 解释器 | `python3 --version` |

### 可选依赖

| 依赖 | 说明 | 用途 |
|------|------|------|
| `GITEE_AI_KEY` | Gitee AI API Key | 向量嵌入（搜索增强） |
| `LLM_API_KEY` | LLM API Key | 结果解释/摘要 |
| memory-tencentdb | OpenClaw 插件 | 向量数据库 |

### 安装 SQLite

```bash
# Ubuntu/Debian
sudo apt install sqlite3

# macOS
brew install sqlite3

# Windows (通过 conda)
conda install sqlite
```

## 安装与配置

### 方式一：自动安装（推荐）

自动初始化，默认配置，适合快速开始：

```bash
python3 scripts/init_memory.py --workspace ~/.openclaw/workspace
```

### 方式二：交互式安装

自定义配置，功能开关，适合深度定制：

```bash
python3 scripts/one_click_setup.py
```

交互式安装支持配置：
- 搜索核心（向量/全文/并行/RRF）
- 缓存优化（内存缓存/预计算/增量更新）
- LLM 增强（重排序/摘要/上下文扩展）
- 智能路由（自动判断/查询改写）
- 学习优化（历史学习/用户反馈/去重）

### 初始化检查

```bash
python3 scripts/memory.py stats   # 查看记忆统计
python3 scripts/memory.py search  # 测试搜索
```

### API Key 配置（可选）

部分功能需要外部 API 凭证，支持两种配置方式：

**方式一：环境变量**
```bash
export IMA_OPENAPI_CLIENTID="your_client_id"
export IMA_OPENAPI_APIKEY="your_api_key"
export GITEE_AI_KEY="your_gitee_ai_key"
export GLM5_API_KEY="your_glm5_api_key"
```

**方式二：配置文件**
```bash
# IMA 凭证（用于云端同步）
mkdir -p ~/.config/ima
echo -n "your_client_id" > ~/.config/ima/client_id
echo -n "your_api_key" > ~/.config/ima/api_key
chmod 600 ~/.config/ima/*
```

> ⚠️ 凭证优先级：环境变量 > ~/.config/ima/ > secrets.env

| 凭证 | 用途 | 配置位置 |
|------|------|----------|
| IMA_OPENAPI_CLIENTID/APIKEY | IMA 云端同步 | ~/.config/ima/ 或环境变量 |
| GITEE_AI_KEY | 向量嵌入 | 环境变量 |
| GLM5_API_KEY | LLM 增强 | 环境变量 |

### 向量模型配置
| 配置 | 值 |
|------|-----|
| Provider | Gitee AI |
| 模型 | Qwen3-Embedding-8B |
| 维度 | 4096维 |
| 数据库 | vectors.db / 36MB |

### LLM配置
| 配置 | 值 |
|------|-----|
| LLM | myprovider / LLM_GLM5 |
| 上下文 | 198K |
| 输出 | 6K |

### memory-tencentdb配置

**注意**：`vectors.db` 由 `memory-tencentdb` 插件首次运行时自动创建，位于 `~/.openclaw/workspace/memory/vectors.db`。

```json
{
  "memory-tencentdb": {
    "l1IdleTimeoutSeconds": 30,
    "embedding": {
      "provider": "gitee",
      "model": "Qwen3-Embedding-8B",
      "dimensions": 4096
    }
  }
}
```

---



## 性能指标

| 模式 | 目标 | 实测 | 状态 |
|------|------|------|------|
| 缓存命中 | < 10ms | **5ms** | ✅ |
| 快速模式 | < 2s | **0.05-1.2s** | ✅ |
| 平衡模式 | < 5s | **4.5s** | ✅ |
| 完整模式 | < 15s | **9-11s** | ✅ |
| 语义匹配召回 | > 80% | **90%** | ✅ |

## 安全模块

**运行时保护：**
- 脚本白名单验证
- 敏感文件保护
- 输入清理和长度限制
- 安全 JSON 解析
- 审计日志记录

```bash
# 运行安全检查
python3 scripts/security.py
```

**发布保护：**
- MIT License 开源协议
- 文件完整性哈希
- 危险模式检测

---

## 更新日志

| 版本 | 日期 | 内容 |
|------|------|------|
| v3.0.5 | 2026-04-07 | 新增审计日志功能：记录所有记忆操作，支持 stats/recent/clear 命令 | LLM Memory Integration：智能路由、查询改写、LLM增强(解释/摘要)、反馈学习、渐进式启用、性能指标 |
| v2.1.0 | 2026-04-06 | 安全增强：脚本白名单、输入清理、审计日志、MIT License、发布保护 |
| v2.0.7 | 2026-04-06 | UI交互优化：精美终端UI、进度条、彩色输出、交互式初始化美化 |
| v2.0.6 | 2026-04-06 | 新增多档自定义配置：功能开关让用户自定义，交互式初始化 |
| v2.0.5 | 2026-04-06 | 全优化版：搜索核心(向量+FTS+并行+RRF)、缓存优化(多级缓存+预计算)、LLM增强(重排序+摘要)、智能路由(自动判断)、学习优化(历史反馈+去重) |
| v2.0.4 | 2026-04-05 | 新增9个脚本：覆盖率检查、向量优化、混合搜索、智能更新等 |
| v2.0.3 | 2026-04-05 | 整合备份配置：向量模型、LLM、一键安装 |
| v2.0.2 | 2026-04-05 | 整合小艺Claw四层架构 |
| v2.0 | 2026-04-05 | 参考 git-notes-memory 全面优化：静默操作、重要性标志、自动分类、实体提取 |
| v1.0.11 | 2026-04-04 | 初始版本 |
