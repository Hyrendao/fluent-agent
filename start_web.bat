@echo off
chcp 65001 >nul
title Fluent-Agent Web UI

cd /d "%~dp0"

echo.
echo   ============================================
echo     Fluent-Agent 外语学习助手
echo   ============================================
echo.
echo   正在启动 Streamlit 服务...
echo.

start "" http://localhost:8501

streamlit run app/web_app.py --server.port 8501 --server.headless true

pause
