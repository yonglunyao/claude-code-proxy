# 日志系统配置说明

## 概述

claude-code-proxy 使用增强的日志系统，支持：
- 日志文件轮转（单个文件最大 10MB）
- 自动清理过期日志
- 多层级日志记录
- 详细的工具调用追踪

## 环境变量配置

### 日志级别

**变量名**: `LOG_LEVEL`

**默认值**: `INFO`

**可选值**:
- `DEBUG` - 详细调试信息
- `INFO` - 一般信息（默认）
- `WARNING` - 警告信息
- `ERROR` - 错误信息
- `CRITICAL` - 严重错误

**示例**:
```bash
export LOG_LEVEL=DEBUG
python -m uvicorn src.main:app
```

### 日志保留天数

**变量名**: `LOG_RETENTION_DAYS`

**默认值**: `7` (保留 7 天)

**说明**: 自动删除超过指定天数的日志文件

**示例**:
```bash
# 保留 30 天的日志
export LOG_RETENTION_DAYS=30

# 保留 3 天的日志
export LOG_RETENTION_DAYS=3
```

## 日志文件结构

```
logs/
├── proxy_2026-04-26.log          # 所有日志（轮转，每文件最大 10MB）
├── proxy_2026-04-26.log.1        # 轮转备份
├── proxy_errors_2026-04-26.log   # 仅错误日志
├── tool_usage_2026-04-26.log     # 工具调用详情
└── ...
```

### 日志文件说明

| 文件名模式 | 说明 | 内容 |
|-----------|------|------|
| `proxy_YYYY-MM-DD.log` | 主日志文件 | 所有级别的日志（DEBUG+） |
| `proxy_errors_YYYY-MM-DD.log` | 错误日志文件 | 仅 ERROR 和 CRITICAL 级别 |
| `tool_usage_YYYY-MM-DD.log` | 工具使用日志 | 工具参数转换详情 |

## 日志格式

### 控制台输出（简洁格式）
```
07:39:20 - INFO - Request received
07:39:21 - DEBUG - Converting tools
```

### 文件输出（详细格式）
```
2026-04-26 07:39:20 | INFO     | src.api.endpoints:123 | Request received
2026-04-26 07:39:20 | DEBUG    | src.conversion.request_converter:95 | Tool conversion started
```

### 工具日志格式
```
================================================================================
[2026-04-26 07:39:20.123] Request ID: abc-123-def
Tool Name: get_weather
Description: Get weather for a location
Input Schema:
{"type": "object", "properties": {"location": {"type": "string"}}}
================================================================================
```

## 自动清理机制

### 触发时机
每次服务启动时自动执行清理

### 清理规则
- 基于文件修改时间（mtime）判断
- 删除超过 `LOG_RETENTION_DAYS` 天的日志文件
- 仅清理匹配以下模式的文件：
  - `proxy_*.log`
  - `proxy_errors_*.log`
  - `tool_usage_*.log`

### 清理日志示例
```
2026-04-26 07:52:25 | INFO     | src.core.logging:48 | Cleaned up 2 old log files (0.00 MB), keeping 7 days
```

## 使用示例

### 启动服务（默认配置）
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8082
```

### 启动服务（自定义配置）
```bash
# 设置日志级别为 DEBUG，保留 30 天
LOG_LEVEL=DEBUG LOG_RETENTION_DAYS=30 python -m uvicorn src.main:app --port 8082
```

### Windows 设置环境变量
```cmd
# 命令行
set LOG_LEVEL=DEBUG
set LOG_RETENTION_DAYS=30
python -m uvicorn src.main:app

# PowerShell
$env:LOG_LEVEL="DEBUG"
$env:LOG_RETENTION_DAYS="30"
python -m uvicorn src.main:app
```

### 实时查看日志
```bash
# 查看主日志
tail -f logs/proxy_$(date +%Y-%m-%d).log

# 查看错误日志
tail -f logs/proxy_errors_$(date +%Y-%m-%d).log

# 查看工具使用日志
tail -f logs/tool_usage_$(date +%Y-%m-%d).log
```

## 日志轮转说明

### 文件大小轮转
- 单个日志文件最大 10MB
- 达到大小限制后自动创建新文件
- 保留最近 5 个备份文件

### 文件命名
- `proxy_YYYY-MM-DD.log` - 当前日志文件
- `proxy_YYYY-MM-DD.log.1` - 第 1 个备份
- `proxy_YYYY-MM-DD.log.2` - 第 2 个备份
- ... 最多到 `.5`

## 故障排查

### 日志文件未创建
- 检查是否有写入权限
- 确认 `logs/` 目录可访问

### 旧日志未删除
- 检查 `LOG_RETENTION_DAYS` 设置
- 查看日志中的清理记录
- 确认文件修改时间是否正确

### 磁盘空间不足
- 减少 `LOG_RETENTION_DAYS` 值
- 减少轮转备份文件数量（修改 `backupCount` 参数）
