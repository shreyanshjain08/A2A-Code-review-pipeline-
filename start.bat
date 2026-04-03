@echo off
setlocal

echo ============================================================
echo   A2A Code Review Pipeline (Windows Bootstrapper)
echo ============================================================
echo.

if not exist ".env" (
    echo [WARNING] No .env file found. Copying .env.example to .env...
    copy .env.example .env
    echo [ERROR] Please edit .env and add your GEMINI_API_KEY.
    exit /b 1
)

:: Crude check for the placeholder key
findstr /C:"your_gemini_api_key_here" .env >nul
if %errorlevel%==0 (
    echo [ERROR] GEMINI_API_KEY is not set in .env
    exit /b 1
)

echo [OK] Environment is configured.
echo.

echo Starting Code Writer Agent...
start /b venv\Scripts\python.exe agents\code_writer\agent.py
timeout /t 2 >nul

echo Starting Code Reviewer Agent...
start /b venv\Scripts\python.exe agents\code_reviewer\agent.py
timeout /t 2 >nul

echo Starting Code Refactorer Agent...
start /b venv\Scripts\python.exe agents\code_refactorer\agent.py
timeout /t 2 >nul

echo.
echo ============================================================
echo   ✅ All services starting!
echo   Web UI: http://localhost:3000
echo   Press Ctrl+C to terminate services.
echo ============================================================
echo.

venv\Scripts\python.exe orchestrator\server.py
