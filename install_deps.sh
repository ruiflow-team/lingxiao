#!/bin/bash
# 凌霄智能影视翻译系统 - 依赖安装脚本

set -e

echo "=== 凌霄系统依赖安装 ==="

# 检测系统
OS="$(uname -s)"
echo "检测到系统: $OS"

# 1. 安装 ffmpeg
echo ""
echo "[1/5] 安装 ffmpeg..."
if command -v ffmpeg &> /dev/null; then
    echo "  ffmpeg 已安装: $(ffmpeg -version | head -1)"
else
    if [ "$OS" == "Darwin" ]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install ffmpeg
        else
            echo "  错误: 需要先安装 Homebrew"
            echo "  访问: https://brew.sh"
            exit 1
        fi
    else
        # Linux
        sudo apt-get update && sudo apt-get install -y ffmpeg
    fi
fi

# 2. 安装 Python 依赖
echo ""
echo "[2/5] 安装 Python 依赖..."
pip install PyQt5==5.15.10 loguru==0.7.0 requests==2.31.0 openai==1.12.0 numpy

# 3. 编译 Whisper.cpp
echo ""
echo "[3/5] 编译 Whisper.cpp..."

WHISPER_CPP_DIR="$HOME/lingxiao/deps/whisper.cpp"
mkdir -p "$WHISPER_CPP_DIR"

if [ ! -d "$WHISPER_CPP_DIR/.git" ]; then
    git clone https://github.com/ggerganov/whisper.cpp.git "$WHISPER_CPP_DIR"
fi

cd "$WHISPER_CPP_DIR"
make clean
make -j $(sysctl -n hw.ncpu)

# 创建 build 目录并编译
mkdir -p build
cd build
cmake ..
make -j $(sysctl -n hw.ncpu)

# 复制 main 到 bin/
mkdir -p bin
cp main main/main 2>/dev/null || cp src/main main/main 2>/dev/null || true

echo "  Whisper.cpp 编译完成"

# 4. 下载 Whisper 模型
echo ""
echo "[4/5] 下载 Whisper 模型..."

WHISPER_MODEL_DIR="$HOME/lingxiao/models/whisper"
mkdir -p "$WHISPER_MODEL_DIR"

MODEL_NAME="ggml-small.bin"  # base, small, medium, large
if [ ! -f "$WHISPER_MODEL_DIR/$MODEL_NAME" ]; then
    echo "  下载 $MODEL_NAME..."
    curl -L -o "$WHISPER_MODEL_DIR/$MODEL_NAME" \
        "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$MODEL_NAME"
else
    echo "  模型已存在: $MODEL_NAME"
fi

# 5. 创建目录结构
echo ""
echo "[5/5] 创建目录..."
mkdir -p "$HOME/lingxiao/output"
mkdir -p "$HOME/lingxiao/temp"
mkdir -p "$HOME/lingxiao/logs"

echo ""
echo "=== 安装完成 ==="
echo "运行: cd ~/lingxiao && python3 main.py"