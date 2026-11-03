@echo off
REM UsageLens - Start the server (Ctrl+C to stop)
setlocal

set PORT=%1
if "%PORT%"=="" set PORT=8000

echo =========================================
echo   UsageLens - System Usage Tracker
echo =========================================
echo.
echo   Press Ctrl+C to stop the server.
echo   Open: http://localhost:%PORT%
echo.

where wsl >nul 2>&1
if %ERRORLEVEL% NEQ 0 goto NO_WSL

wsl -e bash -lc "cd /mnt/c/Workarea/github/UsageLens && mkdir -p data && python3 -m uvicorn backend.server:app --host 0.0.0.0 --port %PORT%"
goto DONE

:NO_WSL
echo [ERROR] WSL not found. Install WSL or run manually.

:DONE
endlocal
