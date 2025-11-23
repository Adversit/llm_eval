@echo off
chcp 65001 > nul
echo 🚀 启动 LLM 评估平台...
echo.

REM 保存当前目录
set "PROJECT_ROOT=%CD%"

REM 启动后端
echo 📦 启动后端服务...
if not exist "%PROJECT_ROOT%\logs" mkdir "%PROJECT_ROOT%\logs"
start "LLM-Backend" cmd /k "cd /d "%PROJECT_ROOT%\backend" && set PYTHONPATH=%PROJECT_ROOT% && set PYTHONUNBUFFERED=1 && call conda activate damoxingeval && python -u -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info --access-log"

REM 等待几秒
timeout /t 3 /nobreak > nul

REM 启动前端
echo 🎨 启动前端服务...
start "LLM-Frontend" cmd /k "cd /d "%PROJECT_ROOT%\frontend" && npm run dev"

echo.
echo ✅ 服务已启动！
echo 📝 后端 API 文档: http://localhost:8000/api/docs
echo 🌐 前端页面: http://localhost:3000
echo.
echo 💡 提示: 后端日志将显示在 "LLM-Backend" 窗口中
echo.
exit
