#!/bin/bash
# 凌霄Web端启动脚本

cd "$(dirname "$0")"

# 检查依赖
echo "🔍 检查依赖..."
pip3 show fastapi >/dev/null 2>&1 || pip3 install -r requirements.txt

# 创建必要目录
mkdir -p uploads output

# 启动API服务
echo "🚀 启动 API 服务 (http://localhost:8000)..."
python3 api/main.py &
API_PID=$!

# 等待API启动
sleep 2

# 检查API是否启动
if curl -s http://localhost:8000/ > /dev/null; then
    echo "✅ API 已启动"
    echo ""
    echo "🌐 Web界面: http://localhost:8000/static/index.html"
    echo "📦 API文档: http://localhost:8000/docs"
    echo ""
    echo "按 Ctrl+C 停止服务"
else
    echo "❌ API 启动失败"
    kill $API_PID 2>/dev/null
    exit 1
fi

# 保持运行
wait $API_PID
