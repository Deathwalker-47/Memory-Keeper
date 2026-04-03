@echo off
REM Memory Keeper — Quick Install Script (Windows)

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

echo ===================================
echo   Memory Keeper - Installation
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

REM Create virtual environment if it doesn't exist
set VENV_DIR=%PROJECT_DIR%\.venv
if not exist "%VENV_DIR%" (
    echo.
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
)

REM Activate virtual environment
echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

REM Install memory-keeper
echo.
echo Installing Memory Keeper...
cd /d "%PROJECT_DIR%"
pip install -e ".[dev]"

echo.
echo Running setup wizard...
memory-keeper init

echo.
echo ===================================
echo   Installation Complete!
echo ===================================
echo.
echo To activate the environment in future sessions:
echo   %VENV_DIR%\Scripts\activate.bat
echo.
echo Start Memory Keeper:
echo   memory-keeper serve
echo.
echo Then install the SillyTavern extension:
echo   Copy adapters\sillytavern\ to your ST extensions directory
echo.
pause
