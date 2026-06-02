@echo off
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo ERROR: Could not launch NETEXEC.
    echo Make sure Python and pygame are installed.
    echo.
    echo Install pygame with:
    echo     pip install pygame
    echo.
    pause
)
