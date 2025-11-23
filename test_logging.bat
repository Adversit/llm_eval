@echo off
echo 测试后端日志输出...
cd backend
set PYTHONPATH=%CD%\..
call conda activate damoxingeval
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info --log-config logging_config.json
