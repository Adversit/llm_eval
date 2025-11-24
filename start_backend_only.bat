@echo off
chcp 65001
echo 启动后端服务...
echo.

REM 保存当前目录
set "PROJECT_ROOT=%CD%"

REM 启动后端
cd /d "%PROJECT_ROOT%\backend"
set PYTHONPATH=%PROJECT_ROOT%
call conda activate damoxingeval
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
