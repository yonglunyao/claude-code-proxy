# 摇摇记忆系统 (yaoyao-memory)

> 四层渐进式长时记忆系统，让 AI 跨会话保持上下文、沉淀知识、持续进化

## ✨ 核心特性

- **静默自动** — AI 自动识别记录，永不询问"是否记录"
- **四层架构** — 短期 → 中期 → 长期 → 档案，渐进式沉淀
- **重要性分级** — Critical / High / Normal / Low 四级
- **记忆分类** — decision / preference / learning / task 等 8 种类型
- **混合检索** — 向量搜索 + 全文搜索，精准召回
- **IMA 同步** — 可选云端备份到 IMA 知识库

## 📦 安装

```bash
npx clawhub@latest install yaoyao-memory
```

## 🚀 初始化

```bash
python3 ~/.openclaw/workspace/skills/yaoyao-memory/scripts/init_memory.py
```

## 📚 记忆层级

| 层级 | 存储位置 | 保留时长 | 用途 |
|:---|:---|:---|:---|
| 短期 | 对话上下文 | 当前会话 | 即时交互 |
| 中期 | memory/*.md | 7-30 天 | 近期事项 |
| 长期 | MEMORY.md | 30 天+ | 核心知识 |
| 档案 | IMA 知识库 | 永久 | 知识沉淀 |

## 🔧 可选配置

### IMA 云端同步

```bash
mkdir -p ~/.config/ima
echo "your_client_id" > ~/.config/ima/client_id
echo "your_api_key" > ~/.config/ima/api_key
```

获取凭证：https://ima.qq.com/agent-interface

### 负一屏推送

配合 `today-task` 技能，任务完成后自动推送结果。

## 📖 使用方式

AI 会自动：
1. 识别对话中的重要信息
2. 判断重要性和类型
3. 静默记录到对应层级
4. 在后续对话中自动召回

**你无需任何操作，记忆系统自动运行。**

## 🔗 相关链接

- [ClawHub](https://clawhub.ai/skills/yaoyao-memory)
- [OpenClaw 文档](https://docs.openclaw.ai)
- [IMA 知识库](https://ima.qq.com)

## 📄 License

MIT
