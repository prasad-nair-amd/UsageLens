@echo off
REM UsageLens - Stop the server

echo Stopping UsageLens server...

wsl -e bash -lc "pkill -9 -f 'uvicorn backend.server:app' 2>/dev/null"
timeout /t 3 /nobreak >nul 2>&1

wsl -e bash -lc "pgrep -f 'uvicorn backend.server:app' >nul 2>&1" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Server stopped.
) else (
    echo Server may still be running. Try closing WSL manually.
)
