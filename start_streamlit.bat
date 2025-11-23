@echo off
chcp 65001 > nul
echo ==========================================
echo   LLM 评估平台 - Streamlit 版本
echo ==========================================
echo.
echo ⚠️  注意：这是旧版 Streamlit 界面
echo 💡 推荐使用新版 React 界面：运行 start.bat
echo.
echo 正在启动 Streamlit 应用...
echo.

REM 激活conda环境
call conda activate damoxingeval

REM 启动Streamlit应用
streamlit run integrated_app.py

pause
