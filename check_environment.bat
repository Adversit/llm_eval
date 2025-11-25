@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ========================================
echo   环境依赖检查工具
echo ========================================
echo.

set "ALL_OK=1"

REM 检查 Python
echo [检查] Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ❌ Python 未安装
    set "ALL_OK=0"
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo   ✅ Python %%i
)

REM 检查 Conda
echo [检查] Conda...
conda --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ⚠️  Conda 未安装 (可选)
) else (
    for /f "tokens=2" %%i in ('conda --version 2^>^&1') do echo   ✅ Conda %%i
    
    REM 检查虚拟环境
    conda env list | findstr "damoxingeval" >nul 2>&1
    if %errorlevel% neq 0 (
        echo   ⚠️  Conda 环境 damoxingeval 不存在
        set "ALL_OK=0"
    ) else (
        echo   ✅ Conda 环境 damoxingeval 已创建
    )
)

REM 检查 Node.js
echo [检查] Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ❌ Node.js 未安装
    set "ALL_OK=0"
) else (
    for /f "tokens=1" %%i in ('node --version 2^>^&1') do echo   ✅ Node.js %%i
)

REM 检查 npm
echo [检查] npm...
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ❌ npm 未安装
    set "ALL_OK=0"
) else (
    for /f "tokens=1" %%i in ('npm --version 2^>^&1') do echo   ✅ npm %%i
)

REM 检查后端依赖
echo [检查] 后端依赖...
if exist "backend\requirements.txt" (
    python -c "import fastapi, uvicorn, pandas" >nul 2>&1
    if %errorlevel% neq 0 (
        echo   ❌ 后端依赖未完全安装
        set "ALL_OK=0"
    ) else (
        echo   ✅ 后端依赖已安装
    )
) else (
    echo   ⚠️  未找到 backend\requirements.txt
)

REM 检查前端依赖
echo [检查] 前端依赖...
if exist "frontend\node_modules" (
    echo   ✅ 前端依赖已安装
) else (
    echo   ❌ 前端依赖未安装
    set "ALL_OK=0"
)

REM 检查 Streamlit 依赖
echo [检查] Streamlit 依赖...
python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo   ❌ Streamlit 未安装
    set "ALL_OK=0"
) else (
    echo   ✅ Streamlit 已安装
)

echo.
echo ========================================
if "!ALL_OK!"=="1" (
    echo ✅ 环境检查通过，可以运行项目
    echo    执行 start.bat 启动项目
) else (
    echo ❌ 环境检查未通过
    echo    执行 install_dependencies.bat 安装依赖
)
echo ========================================
echo.

pause
