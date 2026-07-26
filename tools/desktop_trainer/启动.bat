@echo off
title BlindRoad Desktop Trainer

echo.
echo   ====================================
echo    BlindRoad Desktop Trainer
echo   ====================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Python not found. Please install Python 3.8+
    echo   Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check dependencies
python -c "import PyQt5" >nul 2>&1
if errorlevel 1 (
    echo   [INFO] Installing dependencies, please wait...
    echo.
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo.
        echo   [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

echo   [START] Launching...
echo.

python main.py

if errorlevel 1 (
    echo.
    echo   ====================================
    echo   [ERROR] Program exited abnormally
    echo   ====================================
    pause
)