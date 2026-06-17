#!/bin/bash
# 凌霄智能影视翻译系统 - 开发启动脚本

set -e

echo "========================================"
echo "  凌霄智能影视翻译系统 - 启动器"
echo "========================================"

cd "$(dirname "$0")/.."

# 1. 检查依赖
echo ""
echo "[1/4] 检查依赖..."
python3 -c "import PyQt5; import whisper; import edge_tts; import soundfile; print('  ✅ 所有依赖已安装')" 2>/dev/null || {
    echo "  ⚠️  部分依赖缺失，运行: pip install -r requirements.txt"
}

# 2. 设置 API Key
echo ""
echo "[2/4] 环境变量..."
if [ -z "$MINIMAX_API_KEY" ]; then
    echo "  ⚠️  MINIMAX_API_KEY 未设置（翻译功能将使用 fallback）"
fi

if [ -z "$VAST_API_KEY" ]; then
    echo "  ⚠️  VAST_API_KEY 未设置（云端 GPU 集群功能不可用）"
fi

# 3. 检查测试视频
echo ""
echo "[3/4] 检查测试视频..."
DESKTOP_VIDEO=$(ls ~/Desktop/*.mp4 ~/Desktop/*.mkv 2>/dev/null | head -1)
if [ -n "$DESKTOX_VIDEO" ]; then
    echo "  ✅ 发现测试视频: $DESKTOP_VIDEO"
else
    echo "  ℹ️  桌面上没有测试视频（放到 ~/Desktop/*.mp4）"
fi

# 4. 启动应用
echo ""
echo "[4/4] 启动应用..."
echo ""

# 设置 Python path
export PYTHONPATH="$HOME/lingxiao:$PYTHONPATH"

# 启动
exec python3 main.py