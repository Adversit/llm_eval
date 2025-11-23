@echo off
chcp 65001 > nul
echo 测试后端日志输出...
echo.

cd backend
set PYTHONPATH=..
set PYTHONUNBUFFERED=1

echo 启动 uvicorn，日志应该显示在此窗口...
echo.

call conda activate damoxingeval
python -u -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info --access-log

pause
