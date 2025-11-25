@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ========================================
echo   LLM 评估平台 - 环境依赖安装工具
echo ========================================
echo.

REM 保存当前目录
set "PROJECT_ROOT=%CD%"
set "ERROR_COUNT=0"
set "INSTALL_LOG=%PROJECT_ROOT%\install_log.txt"

REM 清空日志文件
echo 安装日志 - %date% %time% > "%INSTALL_LOG%"
echo. >> "%INSTALL_LOG%"

echo [1/6] 检查 Python 环境...
echo ----------------------------------------

REM 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未检测到 Python 环境
    echo    请先安装 Python 3.8 或更高版本
    echo    下载地址: https://www.python.org/downloads/
    echo. >> "%INSTALL_LOG%"
    echo [ERROR] Python 未安装 >> "%INSTALL_LOG%"
    set /a ERROR_COUNT+=1
    goto :check_conda
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo ✅ Python 已安装: !PYTHON_VERSION!
    echo [OK] Python 版本: !PYTHON_VERSION! >> "%INSTALL_LOG%"
)

:check_conda
echo.
echo [2/6] 检查 Conda 环境...
echo ----------------------------------------

REM 检查 Conda 是否安装
conda --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  警告: 未检测到 Conda 环境
    echo    建议安装 Anaconda 或 Miniconda 以便管理 Python 环境
    echo    下载地址: https://www.anaconda.com/download
    echo. >> "%INSTALL_LOG%"
    echo [WARNING] Conda 未安装 >> "%INSTALL_LOG%"
    set "USE_CONDA=0"
) else (
    for /f "tokens=2" %%i in ('conda --version 2^>^&1') do set CONDA_VERSION=%%i
    echo ✅ Conda 已安装: !CONDA_VERSION!
    echo [OK] Conda 版本: !CONDA_VERSION! >> "%INSTALL_LOG%"
    set "USE_CONDA=1"
    
    REM 检查 damoxingeval 环境是否存在
    conda env list | findstr "damoxingeval" >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo 📦 创建 Conda 虚拟环境: damoxingeval
        echo    这可能需要几分钟时间...
        conda create -n damoxingeval python=3.10 -y >> "%INSTALL_LOG%" 2>&1
        if %errorlevel% neq 0 (
            echo ❌ 创建 Conda 环境失败
            echo [ERROR] 创建 Conda 环境失败 >> "%INSTALL_LOG%"
            set /a ERROR_COUNT+=1
        ) else (
            echo ✅ Conda 环境创建成功
            echo [OK] Conda 环境创建成功 >> "%INSTALL_LOG%"
        )
    ) else (
        echo ✅ Conda 环境 damoxingeval 已存在
        echo [OK] Conda 环境已存在 >> "%INSTALL_LOG%"
    )
)

echo.
echo [3/6] 检查 Node.js 环境...
echo ----------------------------------------

REM 检查 Node.js 是否安装
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未检测到 Node.js 环境
    echo    请先安装 Node.js 16 或更高版本
    echo    下载地址: https://nodejs.org/
    echo. >> "%INSTALL_LOG%"
    echo [ERROR] Node.js 未安装 >> "%INSTALL_LOG%"
    set /a ERROR_COUNT+=1
    goto :check_npm
) else (
    for /f "tokens=1" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
    echo ✅ Node.js 已安装: !NODE_VERSION!
    echo [OK] Node.js 版本: !NODE_VERSION! >> "%INSTALL_LOG%"
)

:check_npm
REM 检查 npm 是否安装
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未检测到 npm
    echo    npm 通常随 Node.js 一起安装
    echo. >> "%INSTALL_LOG%"
    echo [ERROR] npm 未安装 >> "%INSTALL_LOG%"
    set /a ERROR_COUNT+=1
) else (
    for /f "tokens=1" %%i in ('npm --version 2^>^&1') do set NPM_VERSION=%%i
    echo ✅ npm 已安装: !NPM_VERSION!
    echo [OK] npm 版本: !NPM_VERSION! >> "%INSTALL_LOG%"
)

REM 如果有错误，提示用户
if !ERROR_COUNT! gtr 0 (
    echo.
    echo ========================================
    echo ❌ 检测到 !ERROR_COUNT! 个环境问题
    echo    请先安装缺失的环境后再运行此脚本
    echo ========================================
    echo.
    echo 详细日志已保存到: %INSTALL_LOG%
    pause
    exit /b 1
)

echo.
echo [4/6] 安装 Python 后端依赖...
echo ----------------------------------------

cd /d "%PROJECT_ROOT%\backend"

if "!USE_CONDA!"=="1" (
    echo 使用 Conda 环境安装依赖...
    call conda activate damoxingeval
    if %errorlevel% neq 0 (
        echo ❌ 激活 Conda 环境失败
        echo [ERROR] 激活 Conda 环境失败 >> "%INSTALL_LOG%"
        set /a ERROR_COUNT+=1
    ) else (
        echo 正在安装后端依赖包...
        pip install -r requirements.txt >> "%INSTALL_LOG%" 2>&1
        if %errorlevel% neq 0 (
            echo ❌ 后端依赖安装失败
            echo [ERROR] 后端依赖安装失败 >> "%INSTALL_LOG%"
            set /a ERROR_COUNT+=1
        ) else (
            echo ✅ 后端依赖安装成功
            echo [OK] 后端依赖安装成功 >> "%INSTALL_LOG%"
        )
    )
) else (
    echo 使用系统 Python 安装依赖...
    pip install -r requirements.txt >> "%INSTALL_LOG%" 2>&1
    if %errorlevel% neq 0 (
        echo ❌ 后端依赖安装失败
        echo [ERROR] 后端依赖安装失败 >> "%INSTALL_LOG%"
        set /a ERROR_COUNT+=1
    ) else (
        echo ✅ 后端依赖安装成功
        echo [OK] 后端依赖安装成功 >> "%INSTALL_LOG%"
    )
)

echo.
echo [5/6] 安装前端依赖...
echo ----------------------------------------

cd /d "%PROJECT_ROOT%\frontend"

REM 检查 node_modules 是否存在
if exist "node_modules" (
    echo ⚠️  检测到已有 node_modules 目录
    set /p "REINSTALL=是否重新安装? (y/N): "
    if /i "!REINSTALL!"=="y" (
        echo 正在删除旧的依赖...
        rmdir /s /q node_modules
    ) else (
        echo 跳过前端依赖安装
        goto :install_streamlit
    )
)

echo 正在安装前端依赖包...
echo 这可能需要几分钟时间，请耐心等待...
npm install >> "%INSTALL_LOG%" 2>&1
if %errorlevel% neq 0 (
    echo ❌ 前端依赖安装失败
    echo    尝试使用 npm install --legacy-peer-deps
    echo [ERROR] 前端依赖安装失败，尝试备用方案 >> "%INSTALL_LOG%"
    npm install --legacy-peer-deps >> "%INSTALL_LOG%" 2>&1
    if %errorlevel% neq 0 (
        echo ❌ 前端依赖安装失败
        echo [ERROR] 前端依赖安装失败 >> "%INSTALL_LOG%"
        set /a ERROR_COUNT+=1
    ) else (
        echo ✅ 前端依赖安装成功 (使用备用方案)
        echo [OK] 前端依赖安装成功 (legacy-peer-deps) >> "%INSTALL_LOG%"
    )
) else (
    echo ✅ 前端依赖安装成功
    echo [OK] 前端依赖安装成功 >> "%INSTALL_LOG%"
)

:install_streamlit
echo.
echo [6/6] 安装 Streamlit 依赖 (00k 模块)...
echo ----------------------------------------

cd /d "%PROJECT_ROOT%\00k"

if "!USE_CONDA!"=="1" (
    call conda activate damoxingeval
    pip install -r requirements.txt >> "%INSTALL_LOG%" 2>&1
) else (
    pip install -r requirements.txt >> "%INSTALL_LOG%" 2>&1
)

if %errorlevel% neq 0 (
    echo ❌ Streamlit 依赖安装失败
    echo [ERROR] Streamlit 依赖安装失败 >> "%INSTALL_LOG%"
    set /a ERROR_COUNT+=1
) else (
    echo ✅ Streamlit 依赖安装成功
    echo [OK] Streamlit 依赖安装成功 >> "%INSTALL_LOG%"
)

cd /d "%PROJECT_ROOT%"

echo.
echo ========================================
if !ERROR_COUNT! equ 0 (
    echo ✅ 所有依赖安装完成！
    echo.
    echo 📝 下一步操作:
    echo    1. 运行 start.bat 启动项目
    echo    2. 访问 http://localhost:3000 查看前端
    echo    3. 访问 http://localhost:8000/api/docs 查看 API 文档
    echo.
    echo [SUCCESS] 所有依赖安装完成 >> "%INSTALL_LOG%"
) else (
    echo ❌ 安装过程中遇到 !ERROR_COUNT! 个错误
    echo    请查看日志文件了解详情: %INSTALL_LOG%
    echo.
    echo [FAILED] 安装过程中遇到错误 >> "%INSTALL_LOG%"
)
echo ========================================
echo.
echo 详细日志已保存到: %INSTALL_LOG%
echo.

pause
exit /b !ERROR_COUNT!
