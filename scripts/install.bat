@echo off
REM Memory Keeper — Quick Install Script (Windows)

echo ===================================
echo   Memory Keeper — Installation
echo ===================================
echo.

REM Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python 3.10+ is required but not found.
    echo Download from https://www.python.org/downloads/
    pause
    exit /b 1
)

python -c "import sys; assert sys.version_info >= (3, 10)" 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python 3.10+ is required.
    pause
    exit /b 1
)

echo Installing Memory Keeper...
python -m pip install -e ".[dev]"

echo.
echo Running setup wizard...
memory-keeper init

echo.
echo ===================================
echo   Installation Complete!
echo ===================================
echo.
echo Start Memory Keeper:
echo   memory-keeper serve
echo.
echo Then install the SillyTavern extension:
echo   Copy adapters\sillytavern\ to your ST extensions directory
echo.
pause
