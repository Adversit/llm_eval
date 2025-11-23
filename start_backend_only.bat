@echo off
chcp 65001
echo 启动后端服务（测试日志显示）...
echo.

cd backend
set PYTHONPATH=..
set PYTHONUNBUFFERED=1

call conda activate damoxingeval

echo 开始运行 uvicorn...
echo.

python -u -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info --access-log

pause
