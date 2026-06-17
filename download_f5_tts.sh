#!/bin/bash
# F5-TTS 模型下载脚本 (轻量级语音克隆, ~500MB)

set -e

MODELS_DIR="$HOME/lingxiao/models/f5-tts"
echo "🔄 准备下载F5-TTS模型到: $MODELS_DIR"
mkdir -p "$MODELS_DIR"

cd "$MODELS_DIR"

# 方案1: 从HuggingFace下载 (需要代理)
echo ""
echo "方案A: HuggingFace (推荐, 需代理)"
echo "  git clone https://huggingface.co/SWivid/F5-TTS"
echo ""

# 方案2: 从ModelScope下载 (国内可用)
echo "方案B: ModelScope (国内镜像)"
echo "  git clone https://www.modelscope.cn/models/SWivid/F5-TTS.git"
echo ""

# 方案3: 直接下载关键文件
echo "方案C: 直接下载模型文件"
echo "  模型文件: https://huggingface.co/SWivid/F5-TTS/resolve/main/model.pt"
echo "  配置文件: https://huggingface.co/SWivid/F5-TTS/resolve/main/config.json"
echo ""

# 创建目录结构
mkdir -p checkpoints vocab

echo "📦 需要的文件结构:"
echo "  f5-tts/"
echo "  ├── checkpoints/"
echo "  │   └── model.pt          (约400MB, 核心模型)"
echo "  ├── vocab/"
echo "  │   └── vocab.txt         (词表文件)"
echo "  └── config.json           (模型配置)"
echo ""

# 尝试自动下载
echo "🔄 尝试从ModelScope自动下载..."

MODEL_URL="https://www.modelscope.cn/models/SWivid/F5-TTS/resolve/master/model.pt"
CONFIG_URL="https://www.modelscope.cn/models/SWivid/F5-TTS/resolve/master/config.json"

if command -v wget &> /dev/null; then
    echo "使用wget下载..."
    wget -O checkpoints/model.pt "$MODEL_URL" 2>/dev/null || echo "⚠️ 模型下载失败, 请手动下载"
    wget -O config.json "$CONFIG_URL" 2>/dev/null || echo "⚠️ 配置下载失败"
elif command -v curl &> /dev/null; then
    echo "使用curl下载..."
    curl -L -o checkpoints/model.pt "$MODEL_URL" 2>/dev/null || echo "⚠️ 模型下载失败, 请手动下载"
    curl -L -o config.json "$CONFIG_URL" 2>/dev/null || echo "⚠️ 配置下载失败"
else
    echo "❌ 未找到wget或curl, 请手动下载"
fi

echo ""
echo "✅ 完成! 如果自动下载失败, 请使用浏览器手动下载到:"
echo "   $MODELS_DIR"
