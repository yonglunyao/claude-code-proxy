# Claude Code Proxy

一个代理服务器，让 **Claude Code** 能够使用兼容 OpenAI API 的各种 LLM 服务商。将 Claude API 请求转换为 OpenAI API 调用，让你可以通过 Claude Code CLI 使用多种 LLM 提供商。

![Claude Code Proxy](demo.png)

## 功能特性

- **多服务商支持**：同时配置多个 LLM 服务商（OpenAI、DeepSeek、Azure、本地模型等）
- **智能路由**：将不同的 Claude 模型层级（opus/sonnet/haiku）路由到不同的服务商
- **自动故障转移**：如果一个服务商失败，自动尝试链中的下一个服务商
- **完整的 Claude API 兼容**：完全支持 `/v1/messages` 端点
- **函数调用**：完整的工具使用支持，包含正确的转换
- **流式响应**：实时 SSE 流式传输支持
- **图像支持**：Base64 编码的图像输入
- **自定义请求头**：为 API 请求自动注入自定义 HTTP 请求头
- **错误处理**：全面的错误处理和日志记录

## 快速开始

### 1. 安装依赖

```bash
# 使用 UV（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置

在项目根目录创建 `providers.json` 文件（从示例复制）：

```bash
cp providers.json.example providers.json
# 编辑 providers.json 并添加你的 API 密钥和路由配置
```

### 3. 启动服务器

```bash
# 直接运行
python start_proxy.py

# 或使用 UV
uv run claude-code-proxy

# 或使用 docker compose
docker compose up -d
```

### 4. 与 Claude Code 配合使用

```bash
# 如果代理中未设置 ANTHROPIC_API_KEY：
ANTHROPIC_BASE_URL=http://localhost:8082 ANTHROPIC_API_KEY="任意值" claude

# 如果代理中设置了 ANTHROPIC_API_KEY：
ANTHROPIC_BASE_URL=http://localhost:8082 ANTHROPIC_API_KEY="完全匹配的密钥" claude
```

## 配置说明

### providers.json

代理使用 `providers.json` 文件来配置多个 LLM 服务商和模型路由。

```json
{
  "providers": [
    {
      "name": "openai",
      "api_key": "${OPENAI_API_KEY}",
      "base_url": "https://api.openai.com/v1",
      "api_version": null,
      "timeout": 90
    },
    {
      "name": "deepseek",
      "api_key": "${DEEPSEEK_API_KEY}",
      "base_url": "https://api.deepseek.com/v1",
      "api_version": null,
      "timeout": 90
    }
  ],
  "routing": {
    "opus": [
      {"provider": "openai", "model": "gpt-4o"},
      {"provider": "deepseek", "model": "deepseek-chat"}
    ],
    "sonnet": [
      {"provider": "deepseek", "model": "deepseek-chat"},
      {"provider": "openai", "model": "gpt-4o-mini"}
    ],
    "haiku": [
      {"provider": "openai", "model": "gpt-4o-mini"}
    ]
  }
}
```

#### 服务商字段

| 字段 | 必填 | 说明 |
|-------|------|------|
| `name` | 是 | 唯一的服务商标识符 |
| `api_key` | 是 | API 密钥，支持 `${ENV_VAR}` 语法引用环境变量 |
| `base_url` | 是 | API 端点 URL |
| `api_version` | 否 | Azure API 版本（仅 Azure OpenAI 需要） |
| `timeout` | 否 | 请求超时时间（秒），默认 90 |

#### 路由配置

`routing` 部分将 Claude 模型层级映射到服务商：

| 层级 | 匹配规则 |
|------|---------|
| `opus` | 名称中包含 "opus" 的 Claude 模型 |
| `sonnet` | 名称中包含 "sonnet" 的 Claude 模型 |
| `haiku` | 名称中包含 "haiku" 的 Claude 模型 |

每个路由条目是一个**有序数组** - 第一个条目是主服务商，后续条目是故障转移服务商。

#### 故障转移链

当服务商因可重试错误（超时、5xx、429 速率限制）失败时，代理会自动尝试链中的下一个服务商：

```
请求: claude-sonnet-4-6
  -> deepseek:deepseek-chat -> 失败（超时）
  -> openai:gpt-4o-mini -> 成功 -> 返回响应
```

#### 环境变量替换

API 密钥和 base URL 支持 `${ENV_VAR}` 语法来引用环境变量：

```json
{
  "api_key": "${OPENAI_API_KEY}",
  "base_url": "${OPENAI_BASE_URL}"
}
```

这样可以保持配置文件结构化，同时避免在文件中存储敏感信息。

### 环境变量

**配置相关：**

- `PROVIDERS_CONFIG` - providers.json 文件路径（默认：`providers.json`）

**安全相关：**

- `ANTHROPIC_API_KEY` - 用于客户端验证的 Anthropic API 密钥
  - 如果设置，客户端必须提供完全匹配的 API 密钥才能访问代理
  - 如果未设置，则接受任何 API 密钥

**服务器设置：**

- `HOST` - 服务器主机（默认：`0.0.0.0`）
- `PORT` - 服务器端口（默认：`8082`）
- `LOG_LEVEL` - 日志级别（默认：`INFO`）

**性能相关：**

- `MAX_TOKENS_LIMIT` - Token 限制（默认：`4096`）
- `MIN_TOKENS_LIMIT` - 最小 Token 限制（默认：`100`）
- `REQUEST_TIMEOUT` - 请求超时时间（秒），默认 90

**自定义请求头：**

- `CUSTOM_HEADER_*` - API 请求的自定义请求头

### 自定义请求头

通过设置带 `CUSTOM_HEADER_` 前缀的环境变量来添加自定义请求头：

```bash
CUSTOM_HEADER_ACCEPT="application/jsonstream"
CUSTOM_HEADER_AUTHORIZATION="Bearer your-token"
CUSTOM_HEADER_X_API_KEY="your-api-key"
```

### 直接模型透传

你也可以直接使用 OpenAI 模型名称发送请求 - 它们会直接透传到第一个配置的服务商：

```python
# 这些模型会绕过路由，直接发送到默认服务商
response = httpx.post("http://localhost:8082/v1/messages", json={
    "model": "gpt-4o",  # 直接透传
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "你好！"}]
})
```

支持的透传前缀：`gpt-*`、`o1-*`、`o3-*`、`o4-*`、`ep-*`、`doubao-*`、`deepseek-*`

### 服务商配置示例

#### 单个服务商（OpenAI）

```json
{
  "providers": [
    {
      "name": "openai",
      "api_key": "${OPENAI_API_KEY}",
      "base_url": "https://api.openai.com/v1"
    }
  ],
  "routing": {
    "opus": [{"provider": "openai", "model": "gpt-4o"}],
    "sonnet": [{"provider": "openai", "model": "gpt-4o"}],
    "haiku": [{"provider": "openai", "model": "gpt-4o-mini"}]
  }
}
```

#### Azure OpenAI

```json
{
  "providers": [
    {
      "name": "azure",
      "api_key": "${AZURE_API_KEY}",
      "base_url": "https://your-resource.openai.azure.com",
      "api_version": "2024-03-01-preview"
    }
  ],
  "routing": {
    "opus": [{"provider": "azure", "model": "gpt-4"}],
    "sonnet": [{"provider": "azure", "model": "gpt-4"}],
    "haiku": [{"provider": "azure", "model": "gpt-35-turbo"}]
  }
}
```

#### 本地模型（Ollama）

```json
{
  "providers": [
    {
      "name": "ollama",
      "api_key": "dummy-key",
      "base_url": "http://localhost:11434/v1"
    }
  ],
  "routing": {
    "opus": [{"provider": "ollama", "model": "llama3.1:70b"}],
    "sonnet": [{"provider": "ollama", "model": "llama3.1:70b"}],
    "haiku": [{"provider": "ollama", "model": "llama3.1:8b"}]
  }
}
```

### 多服务商配置指南

#### 场景 1：成本优化配置

尽可能将昂贵的请求路由到更便宜的服务商：

```json
{
  "providers": [
    {
      "name": "openai",
      "api_key": "${OPENAI_API_KEY}",
      "base_url": "https://api.openai.com/v1"
    },
    {
      "name": "deepseek",
      "api_key": "${DEEPSEEK_API_KEY}",
      "base_url": "https://api.deepseek.com/v1"
    }
  ],
  "routing": {
    "opus": [
      {"provider": "openai", "model": "gpt-4o"},
      {"provider": "deepseek", "model": "deepseek-chat"}
    ],
    "sonnet": [
      {"provider": "deepseek", "model": "deepseek-chat"},
      {"provider": "openai", "model": "gpt-4o-mini"}
    ],
    "haiku": [
      {"provider": "deepseek", "model": "deepseek-chat"}
    ]
  }
}
```

**优势：**
- Sonnet/haiku 请求优先使用更便宜的 DeepSeek
- Opus 请求优先使用 OpenAI GPT-4o，DeepSeek 作为备用
- 自动故障转移确保可靠性

#### 场景 2：高可用配置

在每个层级使用多个服务商实现冗余：

```json
{
  "providers": [
    {
      "name": "openai-primary",
      "api_key": "${OPENAI_API_KEY_1}",
      "base_url": "https://api.openai.com/v1"
    },
    {
      "name": "openai-backup",
      "api_key": "${OPENAI_API_KEY_2}",
      "base_url": "https://api.openai.com/v1"
    },
    {
      "name": "deepseek",
      "api_key": "${DEEPSEEK_API_KEY}",
      "base_url": "https://api.deepseek.com/v1"
    }
  ],
  "routing": {
    "opus": [
      {"provider": "openai-primary", "model": "gpt-4o"},
      {"provider": "openai-backup", "model": "gpt-4o"},
      {"provider": "deepseek", "model": "deepseek-chat"}
    ],
    "sonnet": [
      {"provider": "deepseek", "model": "deepseek-chat"},
      {"provider": "openai-primary", "model": "gpt-4o-mini"}
    ]
  }
}
```

**优势：**
- 多个 API 密钥分散速率限制
- 服务商级别的故障转移，实现最大正常运行时间
- 关键请求的跨服务商故障转移

#### 场景 3：混合云端 + 本地

结合云 API 和本地模型，兼顾隐私和成本：

```json
{
  "providers": [
    {
      "name": "openai",
      "api_key": "${OPENAI_API_KEY}",
      "base_url": "https://api.openai.com/v1"
    },
    {
      "name": "ollama-local",
      "api_key": "dummy-key",
      "base_url": "http://localhost:11434/v1"
    }
  ],
  "routing": {
    "opus": [
      {"provider": "openai", "model": "gpt-4o"}
    ],
    "sonnet": [
      {"provider": "ollama-local", "model": "llama3.1:70b"},
      {"provider": "openai", "model": "gpt-4o-mini"}
    ],
    "haiku": [
      {"provider": "ollama-local", "model": "llama3.1:8b"}
    ]
  }
}
```

**优势：**
- 敏感请求保留在本地（haiku 层级）
- 复杂任务在需要时使用云模型
- 简单任务节省成本

#### 场景 4：区域服务商

根据可用性路由到不同服务商：

```json
{
  "providers": [
    {
      "name": "openai-us",
      "api_key": "${OPENAI_API_KEY_US}",
      "base_url": "https://api.openai.com/v1"
    },
    {
      "name": "doubao-cn",
      "api_key": "${DOUBAO_API_KEY}",
      "base_url": "https://ark.cn-beijing.volces.com/api/v3"
    }
  ],
  "routing": {
    "opus": [
      {"provider": "doubao-cn", "model": "ep-20250519160812-h7qpt"},
      {"provider": "openai-us", "model": "gpt-4o"}
    ],
    "sonnet": [
      {"provider": "doubao-cn", "model": "ep-20250519160812-h7qpt"}
    ]
  }
}
```

### 多服务商配置故障排查

#### 服务商无响应

**症状：** 请求持续超时或失败

**解决方案：**
1. 检查服务商连通性：
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

2. 验证 base_url 是否正确（OpenAI 兼容 API 需要包含 `/v1`）

3. 在 providers.json 中增加超时时间：
   ```json
   {"timeout": 120}
   ```

#### 故障转移不工作

**症状：** 主服务商失败但请求没有重试

**检查：**
1. 验证故障转移服务商按正确顺序列出：
   ```json
   "sonnet": [
     {"provider": "primary", "model": "model-name"},
     {"provider": "fallback", "model": "backup-model"}  // 这是故障转移
   ]
   ```

2. 检查日志中的错误类型 - 只有可重试错误会触发故障转移：
   - 超时（408）
   - 速率限制（429）
   - 服务器错误（5xx）

3. 确保所有服务商都有有效的 API 密钥

#### 模型路由问题

**症状：** 请求路由到错误的服务商

**调试：**
1. 启用 DEBUG 日志查看路由决策：
   ```bash
   LOG_LEVEL=DEBUG python start_proxy.py
   ```

2. 检查模型名称匹配：
   - `claude-opus-*` → `opus` 层级
   - `claude-sonnet-*` → `sonnet` 层级
   - `claude-haiku-*` → `haiku` 层级

3. 对于直接模型透传，确保模型名称以以下内容开头：
   - `gpt-*`、`o1-*`、`o3-*`、`o4-*`
   - `ep-*`、`doubao-*`、`deepseek-*`

#### 跨服务商速率限制

**最佳实践：**

1. **为同一服务商使用多个 API 密钥：**
   ```json
   {
     "providers": [
       {"name": "openai-key1", "api_key": "${KEY1}", ...},
       {"name": "openai-key2", "api_key": "${KEY2}", ...}
     ]
   }
   ```

2. **跨层级平衡请求分布：**
   ```json
   "routing": {
     "opus": [{"provider": "openai-key1", ...}],
     "sonnet": [{"provider": "openai-key2", ...}]
   }
   ```

3. **监控日志**中的速率限制错误并调整路由

### 配置最佳实践

1. **安全优先：**
   - 绝不要提交包含真实 API 密钥的 `providers.json`
   - 对所有敏感信息使用 `${ENV_VAR}` 语法
   - 设置 `ANTHROPIC_API_KEY` 进行客户端验证

2. **从简单开始：**
   - 先从单个服务商开始
   - 在验证基本设置后再添加故障转移服务商
   - 在组合之前独立测试每个服务商

3. **监控性能：**
   - 检查 `logs/` 目录中的日志
   - 设置期间启用 DEBUG 日志
   - 使用 benchmark.py 进行性能测试

4. **版本控制：**
   - 提交带有安全默认值的 `providers.json.example`
   - 将 `providers.json` 添加到 `.gitignore`
   - 在团队文档中记录路由策略

## 使用示例

### 基础对话

```python
import httpx

response = httpx.post(
    "http://localhost:8082/v1/messages",
    json={
        "model": "claude-3-5-sonnet-20241022",  # 根据 providers.json 路由
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": "你好！"}
        ]
    }
)
```

## 与 Claude Code 集成

```bash
# 启动代理
python start_proxy.py

# 使用 Claude Code 配合代理
ANTHROPIC_BASE_URL=http://localhost:8082 claude

# 或永久设置
export ANTHROPIC_BASE_URL=http://localhost:8082
claude
```

## 测试

```bash
# 运行单元测试
python -m pytest tests/ -v

# 运行集成测试（需要运行中的服务器）
python tests/test_main.py
```

## 开发

### 使用 UV

```bash
# 安装依赖
uv sync

# 运行服务器
uv run claude-code-proxy

# 格式化代码
uv run black src/
uv run isort src/

# 类型检查
uv run mypy src/
```

### 项目结构

```
claude-code-proxy/
├── src/
│   ├── main.py                     # FastAPI 服务器
│   ├── api/endpoints.py            # 带故障转移的 API 路由
│   ├── core/
│   │   ├── config.py               # 应用配置（加载 providers.json）
│   │   ├── provider_config.py      # 服务商配置模型
│   │   ├── provider_manager.py     # 多服务商客户端管理器
│   │   ├── model_router.py         # 模型路由与故障转移
│   │   ├── client.py               # OpenAI 异步客户端
│   │   ├── constants.py            # API 常量
│   │   └── logging.py              # 日志设置
│   ├── models/claude.py            # Claude 请求/响应模型
│   └── conversion/                 # Claude <-> OpenAI 转换器
├── tests/                          # 单元测试
├── providers.json.example          # 配置模板
├── .env.example                    # 环境变量模板
├── start_proxy.py                  # 启动脚本
└── README.md
```

## 性能

- **异步/await** 实现高并发
- 每个服务商**独立的客户端池**
- **流式支持**实现实时响应
- **自动故障转移**实现高可用性
- **可配置的超时**和重试

## 性能测试

项目包含性能基准测试工具：

```bash
# 基本测试
python benchmark.py

# 自定义并发和请求数
python benchmark.py -c 10 -n 50

# 指定模型和提示词
python benchmark.py -m gpt-4o -p "写一首诗"

# 测试长输出
python benchmark.py --max-tokens 1000
```

**性能指标：**
- **TTFT**（首 token 时间）：从请求到收到第一个 token 的延迟
- **吞吐量**：每秒处理的请求数
- **Token 生成速度**：每秒生成的 token 数

## 许可证

MIT License
