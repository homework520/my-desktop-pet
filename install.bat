@echo off
chcp 65001 >nul
title 桌宠环境安装程序

echo ========================================
echo       温柔姐姐桌宠 - 环境安装
echo ========================================
echo.

cd /d "%~dp0"

echo [1/4] 检查 Python...

py --version >nul 2>&1

if errorlevel 1 (
    echo.
    echo [错误] 没有找到 Python。
    echo.
    echo 请先安装 Python 3.10 或更高版本。
    echo 安装时请勾选：
    echo     Add Python to PATH
    echo.
    pause
    exit /b 1
)

echo Python 检查完成。
echo.

echo [2/4] 创建虚拟环境...

if not exist ".venv" (
    py -m venv .venv
)

echo 虚拟环境准备完成。
echo.

echo [3/4] 升级 pip...

call ".venv\Scripts\python.exe" -m pip install --upgrade pip

echo.

echo [4/4] 安装依赖...

call ".venv\Scripts\python.exe" -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ========================================
    echo 安装失败。
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo       安装完成！
echo ========================================
echo.
echo 接下来可以双击 run.bat 启动桌宠。
echo.

pause
