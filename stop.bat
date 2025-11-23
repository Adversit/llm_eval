@echo off
chcp 65001 > nul
echo 🛑 停止 LLM 评估平台...
echo.

REM 停止后端进程
echo 📦 停止后端服务...
for /f "tokens=2" %%a in ('tasklist /FI "WINDOWTITLE eq LLM-Backend*" /NH 2^>nul ^| findstr "cmd.exe"') do (
    taskkill /F /PID %%a 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    taskkill /F /PID %%a 2>nul
)

REM 停止前端进程
echo 🎨 停止前端服务...
for /f "tokens=2" %%a in ('tasklist /FI "WINDOWTITLE eq LLM-Frontend*" /NH 2^>nul ^| findstr "cmd.exe"') do (
    taskkill /F /PID %%a 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000.*LISTENING"') do (
    taskkill /F /PID %%a 2>nul
)

echo.
echo ✅ 所有服务已停止！
echo.
pause
