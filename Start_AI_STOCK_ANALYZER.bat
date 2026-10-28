@echo off
title AI_STOCK_ANALYZER
cd /d "%~dp0"

if not exist "app.py" (
    echo ERROR: app.py was not found in:
    echo %CD%
    echo.
    echo Run this file from the project folder that contains app.py.
    pause
    exit /b 1
)

echo Starting AI_STOCK_ANALYZER...
echo Keep this window open while using the app.
echo.
uv run streamlit run app.py
echo.
echo The app has stopped. If an error appeared above, take a screenshot.
pause
