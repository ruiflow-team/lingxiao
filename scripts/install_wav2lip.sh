#!/bin/bash
# Wav2Lip 安装脚本
# 专门处理口型同步模块

set -e

echo "=== Wav2Lip 安装 ==="

LINGXIAO_ROOT="$HOME/lingxiao"
WAV2LIP_DIR="$LINGXIAO_ROOT/deps/Wav2Lip"

# 1. 检查 Python 3.7/3.8
echo "检查 Python 版本..."
PYTHON_VERSION=$(python3 -c 'import sys; print(sys.version_info[1])')
if [ "$PYTHON_VERSION" -ge 10 ]; then
    echo "  Python 3.$PYTHON_VERSION - OK (不需要独立环境)"
    HAS_PY38=0
elif [ "$PYTHON_VERSION" -eq 7 ] || [ "$PYTHON_VERSION" -eq 8 ]; then
    echo "  Python 3.$PYTHON_VERSION - OK"
    HAS_PY38=1
else
    echo "  ⚠️  Python 版本可能不兼容，但尝试安装"
fi

# 2. 检查 GPU
echo ""
echo "检查 GPU..."
if python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')" 2>/dev/null; then
    echo "  ✅ GPU 可用"
else
    echo "  ⚠️  无 NVIDIA GPU，口型同步需要 GPU"
fi

# 3. 检查 Wav2Lip 目录
echo ""
echo "检查 Wav2Lip..."
if [ -d "$WAV2LIP_DIR" ]; then
    echo "  Wav2Lip 已存在: $WAV2LIP_DIR"
else
    echo "  克隆 Wav2Lip..."
    git clone --depth 1 https://github.com/Rudrabha/Wav2Lip.git "$WAV2LIP_DIR"
fi

# 4. 创建独立虚拟环境（如果需要）
if [ "$HAS_PY38" -eq 1 ]; then
    VENV_DIR="$WAV2LIP_DIR/venv"
    if [ ! -d "$VENV_DIR" ]; then
        echo ""
        echo "创建 Python 3.8 虚拟环境..."
        python3.8 -m venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        pip install --upgrade pip
    else
        source "$VENV_DIR/bin/activate"
    fi
fi

# 5. 安装依赖
echo ""
echo "安装 Wav2Lip 依赖..."
cd "$WAV2LIP_DIR"

# 检查 requirements.txt 是否存在
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt 2>&1 | tail -10
else
    # 手动安装核心依赖
    pip install torch==1.10.0 torchvision==0.11.0
    pip install librosa==0.9.1
    pip install opencv-python==4.7.0.68
    pip install face_alignment==1.3.5
fi

# 6. 下载预训练模型
echo ""
echo "下载 Wav2Lip 模型..."
MODEL_DIR="$LINGXIAO_ROOT/models/wav2lip/checkpoints"
mkdir -p "$MODEL_DIR"

if [ ! -f "$MODEL_DIR/wav2lip_gan.pth" ]; then
    echo "  下载 wav2lip_gan.pth (约 400MB)..."
    # 需要手动下载：https://github.com/Rudrabha/Wav2Lip#download
    echo "  ⚠️  请手动下载模型文件并放到: $MODEL_DIR/wav2lip_gan.pth"
    echo "  下载链接: https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth"
else
    echo "  ✅ 模型已存在"
fi

# 7. 创建模型符号链接（如果需要）
ln -sf "$LINGXIAO_ROOT/models/wav2lip" "$WAV2LIP_DIR/wav2lip"

echo ""
echo "=== 安装完成 ==="
echo ""
echo "使用方式:"
echo "  1. 手动下载 wav2lip_gan.pth 放入: $MODEL_DIR/"
echo "  2. 在项目中使用: from core.lipsync import Wav2LipClient"
echo ""
echo "详细说明:"
echo "  https://github.com/Rudrabha/Wav2Lip"