#!/bin/bash

echo "🚀 启动 LLM 评估平台..."

# 启动后端
echo "📦 启动后端服务..."
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# 等待后端启动
sleep 3

# 启动前端
echo "🎨 启动前端服务..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ 服务已启动！"
echo "📝 后端 API 文档: http://localhost:8000/api/docs"
echo "🌐 前端页面: http://localhost:3000"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获 Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT

# 等待
wait
