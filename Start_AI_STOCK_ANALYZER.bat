@echo off
title AI_STOCK_ANALYZER
cd /d "D:\Users\User\Desktop\ai_stock_analyzer_v2\ai_stock_analyzer_v2"

if not exist "app.py" (
    echo ERROR: app.py was not found in:
    echo %CD%
    echo.
    echo Edit this shortcut file and correct the project folder path.
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
