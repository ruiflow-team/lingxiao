#!/bin/bash
# FFmpeg安装检查脚本

echo "🔍 检查 FFmpeg 安装状态..."
echo ""

if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg 已安装"
    echo ""
    ffmpeg -version | head -3
    echo ""
    echo "导出功能可用!"
else
    echo "❌ FFmpeg 未安装"
    echo ""
    echo "导出视频需要 FFmpeg，请按以下方式安装:"
    echo ""
    echo "  • Homebrew (推荐):  brew install ffmpeg"
    echo "  • MacPorts:            sudo port install ffmpeg"
    echo "  • 二进制下载:        https://ffmpeg.org/download.html"
    echo ""
    echo "安装完成后重新启动程序即可导出视频。"
fi
