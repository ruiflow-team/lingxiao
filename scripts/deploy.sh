#!/bin/bash
# 凌霄智能影视翻译系统 - 自动化部署脚本
# 适用于 macOS/Linux 服务器

set -e

echo "======================================"
echo "  凌霄智能影视翻译系统 - 部署脚本"
echo "======================================"
echo

# 配置
APP_NAME="LingXiao"
INSTALL_DIR="$HOME/lingxiao"
PYTHON_BIN=$(which python3)

# 检查 Python
if [ ! -x "$PYTHON_BIN" ]; then
    echo "❌ 需要 Python 3"
    exit 1
fi

echo "✓ Python: $PYTHON_BIN"
echo "✓ 版本: $($PYTHON_BIN --version)"

# 检查系统
if [ "$(uname)" = "Darwin" ]; then
    echo "✓ 系统: macOS"
    PLATFORM="macos"
elif [ "$(uname -s)" = "Linux" ]; then
    echo "✓ 系统: Linux"
    PLATFORM="linux"
else
    echo "⚠️  系统: $(uname) (未测试)"
    PLATFORM="unknown"
fi

# 安装依赖
echo
echo "======================================"
echo "  安装依赖"
echo "======================================"

if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    $PYTHON_BIN -m pip install --user -r "$INSTALL_DIR/requirements.txt"
    echo "✓ 依赖安装完成"
else
    echo "⚠️  requirements.txt 未找到"
fi

# 验证核心模块
echo
echo "======================================"
echo "  验证核心模块"
echo "======================================"

$PYTHON_BIN -c "
import sys
sys.path.insert(0, '$INSTALL_DIR')

modules = [
    'core.config',
    'core.asr',
    'core.translator',
    'core.translator_free',
    'core.tts',
    'core.ffmpeg_utils',
    'core.pipeline',
    'core.lipsync',
    'core.license',
]

for m in modules:
    try:
        __import__(m)
        print(f'  ✓ {m}')
    except Exception as e:
        print(f'  ✗ {m}: {e}')
        sys.exit(1)

print()
print('✓ 所有核心模块加载成功')
"

# 检查 PyInstaller
if $PYTHON_BIN -c "import PyInstaller" 2>/dev/null; then
    echo "✓ PyInstaller 已安装"
else
    echo "安装 PyInstaller..."
    $PYTHON_BIN -m pip install --user pyinstaller
    echo "✓ PyInstaller 安装完成"
fi

# 打包
echo
echo "======================================"
echo "  打包应用"
echo "======================================"

cd "$INSTALL_DIR"

if [ -f "lingxiao.spec" ]; then
    $PYTHON_BIN -m PyInstaller lingxiao.spec --clean
    echo "✓ 打包完成"
    echo
    echo "输出目录: $INSTALL_DIR/dist/"
    ls -la "$INSTALL_DIR/dist/"
else
    echo "⚠️  lingxiao.spec 未找到，跳过打包"
fi

# 创建快捷方式
echo
echo "======================================"
echo "  创建快捷方式"
echo "======================================"

if [ -f "start_mac.command" ]; then
    chmod +x start_mac.command
    echo "✓ start_mac.command 已就绪"
fi

echo
echo "======================================"
echo "  部署完成"
echo "======================================"
echo
echo "启动方式:"
echo "  GUI: python3 $INSTALL_DIR/main.py"
echo "  或:  ./$INSTALL_DIR/start_mac.command"
echo "  测试: python3 $INSTALL_DIR/scripts/test_e2e.py"
echo