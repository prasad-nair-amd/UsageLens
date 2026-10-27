@echo off
REM UsageLens - Start the server
setlocal

set PORT=%1
if "%PORT%"=="" set PORT=8000

echo =========================================
echo   UsageLens - System Usage Tracker
echo =========================================
echo.

where wsl >nul 2>&1
if %ERRORLEVEL% NEQ 0 goto NO_WSL

echo [INFO] Using WSL...
echo.

echo [1/3] Installing dependencies...
wsl -e bash -lc "pip3 install --quiet --break-system-packages fastapi uvicorn paramiko pyyaml filelock sse-starlette 2>/dev/null; echo done"

echo [2/3] Stopping old instance...
wsl -e bash -lc "pkill -f 'uvicorn backend.server:app' 2>/dev/null; sleep 1; echo done"

echo [3/3] Starting server on port %PORT%...
wsl -e bash -lc "cd /mnt/c/Workarea/github/UsageLens && mkdir -p data && nohup python3 -m uvicorn backend.server:app --host 0.0.0.0 --port %PORT% > /tmp/usagelens.log 2>&1 & disown"

echo.
echo Waiting for server to be ready...
set /a TRIES=0

:POLL
if %TRIES% GEQ 90 goto TIMEOUT
timeout /t 2 /nobreak >nul
set /a TRIES=%TRIES%+1
wsl -e bash -lc "curl -s -o /dev/null http://127.0.0.1:%PORT%/api/hosts 2>/dev/null && echo READY || echo WAIT" | findstr "READY" >nul 2>&1
if %ERRORLEVEL% NEQ 0 goto POLL

echo.
echo =========================================
echo   Server is running!
echo   Open: http://localhost:%PORT%
echo   Stop: stop.bat
echo =========================================
goto END

:TIMEOUT
echo.
echo Server may still be starting. Check: http://localhost:%PORT%
goto END

:NO_WSL
echo [ERROR] WSL not found. Please install WSL or run manually:
echo   wsl -e bash -lc "cd /mnt/c/Workarea/github/UsageLens && python3 -m uvicorn backend.server:app --host 0.0.0.0 --port 8000"
goto END

:END
endlocal
