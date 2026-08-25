@echo off
title RAG Application Launcher

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║              RAG Application Launcher               ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: Start FastAPI backend in a new window
echo  [1/2] Starting FastAPI backend on http://localhost:8000 ...
start "RAG Backend (FastAPI)" cmd /k "cd /d %~dp0 && python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload"

:: Brief pause so the backend gets a head start
timeout /t 3 /nobreak >nul

:: Start Streamlit frontend in a new window
echo  [2/2] Starting Streamlit frontend on http://localhost:8501 ...
start "RAG Frontend (Streamlit)" cmd /k "cd /d %~dp0 && python -m streamlit run frontend.py"

echo.
echo  ✓ Both services are starting in separate windows.
echo  ✓ Open http://localhost:8501 in your browser.
echo.
pause
