@echo off
chcp 65001 >nul
title 温柔姐姐桌宠 - 打包程序

cd /d "%~dp0"

echo ========================================
echo       温柔姐姐桌宠 - 打包
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [错误] 虚拟环境不存在。
    echo 请先运行 install.bat
    pause
    exit /b 1
)

echo 正在清理旧的打包文件...

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo 开始打包...

".venv\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --windowed ^
    --name "温柔姐姐桌宠" ^
    --add-data "pictures;./pictures" ^
    "codes/main.py"

if errorlevel 1 (
    echo.
    echo ========================================
    echo 打包失败！
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo 打包完成！
echo ========================================
echo.
echo 输出目录：
echo dist\温柔姐姐桌宠\
echo.

pause
