@echo off
chcp 65001 >nul
title 桌宠

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo 尚未安装运行环境。
    echo 请先运行 install.bat
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" "codes\main.py"

if errorlevel 1 (
    echo.
    echo ========================================
    echo 程序运行出现错误。
    echo ========================================
    echo.
    pause
)
