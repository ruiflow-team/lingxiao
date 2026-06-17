#!/bin/bash
# 下载GPT-SoVITS模型脚本

set -e

MODELS_DIR="$HOME/lingxiao/models/gpt-sovits"
echo "🔄 准备下载GPT-SoVITS模型到: $MODELS_DIR"
mkdir -p "$MODELS_DIR"

cd "$MODELS_DIR"

# 创建必要目录
mkdir -p gpt sovits bert t2s

echo ""
echo "⚠️ GPT-SoVITS模型需要手动下载或通过以下方式获取:"
echo ""
echo "方案A: 使用模型库镜像 (推荐)"
echo "  1. 访问: https://www.modelscope.cn/models"
echo "  2. 搜索: GPT-SoVITS"
echo "  3. 下载预训练模型文件"
echo ""
echo "方案B: 从HuggingFace下载"
echo "  git clone https://huggingface.co/lj1995/GPT-SoVITS"
echo ""
echo "需要的文件结构:"
echo "  gpt-sovits/"
echo "  ├── gpt/"
echo "  │   └── model.ckpt          (GPT模型)"
echo "  ├── sovits/"
echo "  │   └── model.pth           (SoVITS模型)"
echo "  ├── bert/"
echo "  │   └── chinese-roberta-wwm-ext-large/"
echo "  └── t2s/"
echo "      └── model.pth           (文本到音频)"
echo ""
echo "模型大小约: 2-3GB"
echo ""
echo "📖 备选轻量级方案:"
echo "  如果GPT-SoVITS过重，可以考虑F5-TTS (500MB级别)"
echo "  https://github.com/SWivid/F5-TTS"
