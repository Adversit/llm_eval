@echo off
chcp 65001 > nul
echo 🚀 启动 LLM 评估平台 (生产模式 - 适合长时间运行评估任务)...
echo.

REM 保存当前目录
set "PROJECT_ROOT=%CD%"

REM 创建日志目录
if not exist "%PROJECT_ROOT%\logs" mkdir "%PROJECT_ROOT%\logs"

REM 启动后端 (不使用 --reload，避免任务中断)
echo 📦 启动后端服务 (生产模式)...
start "LLM-Backend" cmd /k "cd /d "%PROJECT_ROOT%\backend" && set PYTHONPATH=%PROJECT_ROOT% && call conda activate damoxingeval && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

REM 等待几秒
timeout /t 3 /nobreak > nul

REM 启动前端
echo 🎨 启动前端服务...
start "LLM-Frontend" cmd /k "cd /d "%PROJECT_ROOT%\frontend" && npm run dev"

echo.
echo ✅ 服务已启动 (生产模式)！
echo 📝 后端 API 文档: http://localhost:8000/api/docs
echo 🌐 前端页面: http://localhost:3000
echo.
echo ⚠️  注意: 生产模式下修改代码不会自动重启服务
echo 💡 如需开发调试，请使用 start.bat
echo.
pause
