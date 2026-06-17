#!/bin/bash
# 凌霄智能影视翻译系统 - macOS 启动器
# 双击此文件启动应用

cd "$(dirname "$0")"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 需要 Python 3"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
python3 -c "import PyQt5, whisper, edge_tts, soundfile, loguru" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "警告: 部分依赖可能缺失"
    echo "运行: pip install -r requirements.txt"
fi

# 设置环境
export PYTHONPATH="$HOME/lingxiao:$PYTHONPATH"
export QT_MAC_WANTS_LAYER=1

# 启动
echo "启动凌霄智能影视翻译系统..."
exec python3 main.py