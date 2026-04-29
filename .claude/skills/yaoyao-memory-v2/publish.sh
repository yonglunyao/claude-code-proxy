#!/bin/bash
# =============================================================================
# 发布脚本 - 从开发版同步到发布版，然后发布
# =============================================================================
# 版本结构：
# - yaoyao-memory-v2   = 开发版
# - yaoyao-memory-homo = 使用版（发布专用）
# =============================================================================

set -e

WORKSPACE="$HOME/.openclaw/workspace/skills"
DEV_DIR="$WORKSPACE/yaoyao-memory-v2"
PUBLISH_DIR="$WORKSPACE/yaoyao-memory-homo"

if [ -z "$1" ]; then
    echo "用法: ./publish.sh <版本号>"
    echo "例如: ./publish.sh 3.9.0"
    exit 1
fi
VERSION="$1"

echo "=========================================="
echo "🚀 yaoyao-memory 发布流程"
echo "=========================================="
echo "开发版: $DEV_DIR"
echo "发布版: $PUBLISH_DIR"
echo "版本: $VERSION"

# 步骤1: 从开发版同步到发布版
echo ""
echo "📂 步骤1: 同步开发版 → 发布版..."
rsync -av --exclude='publish.sh' --exclude='publish-clean.sh' \
    --exclude='__pycache__' --exclude='*.pyc' \
    "$DEV_DIR/" "$PUBLISH_DIR/"
echo "✅ 同步完成"

# 步骤2: 在发布版执行清理
echo ""
echo "🧹 步骤2: 执行隐私清理..."
cd "$PUBLISH_DIR"
./publish-clean.sh

# 步骤3: 验证敏感文件
echo ""
echo "🔍 步骤3: 验证清理结果..."
for f in embeddings_cache.json persona_update.json user_config.json samba.json llm_config.json; do
    if [ -f "config/$f" ]; then
        echo "❌ 发现敏感文件: config/$f"
        exit 1
    fi
done
echo "✅ 验证通过"

# 步骤4: 更新版本号
echo ""
echo "📝 步骤4: 更新版本号..."
sed -i "s/^version:.*/version: $VERSION/" "$PUBLISH_DIR/SKILL.md"
sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" "$PUBLISH_DIR/_meta.json"
echo "✅ 版本号更新为 $VERSION"

# 步骤5: 发布到 ClaWHub
echo ""
echo "📤 步骤5: 发布到 ClaWHub..."
clawhub publish skills/yaoyao-memory --version "$VERSION"

# 步骤6: 隐藏
echo ""
echo "🙈 步骤6: 隐藏旧版本..."
clawhub hide --yes yaoyao-memory

# 步骤7: 重启 API server
echo ""
echo "🔄 步骤7: 重启 API server..."
pkill -f "api_server.py" 2>/dev/null || true
sleep 1
python3 "$PUBLISH_DIR/scripts/api_server.py" &
echo "✅ API server 已切换到发布版"

echo ""
echo "=========================================="
echo "✅ 发布完成! 版本 $VERSION"
echo "=========================================="
