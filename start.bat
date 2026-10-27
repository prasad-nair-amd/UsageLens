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
wsl -e bash -lc "pkill -9 -f 'uvicorn backend.server:app' 2>/dev/null; sleep 2; echo done"

echo [3/3] Starting server on port %PORT%...
start /B wsl -e bash -lc "cd /mnt/c/Workarea/github/UsageLens && mkdir -p data && python3 -m uvicorn backend.server:app --host 0.0.0.0 --port %PORT% > /tmp/usagelens.log 2>&1"

echo.
echo Waiting for server...
echo.
set /a COUNT=0

:POLL
if %COUNT% GEQ 40 goto TIMEOUT
timeout /t 3 /nobreak >nul 2>&1
set /a COUNT=%COUNT%+1
set /a SECS=%COUNT%*3
wsl -e bash -lc "curl -sf http://127.0.0.1:%PORT%/api/hosts >nul 2>&1 && echo UP || echo DOWN" > "%TEMP%\ul_chk.txt" 2>&1
findstr /C:"UP" "%TEMP%\ul_chk.txt" >nul 2>&1
if %ERRORLEVEL% EQU 0 goto READY
echo   Starting... %SECS%s
goto POLL

:READY
del /q "%TEMP%\ul_chk.txt" >nul 2>&1
echo.
echo =========================================
echo   Server is running!
echo   Open: http://localhost:%PORT%
echo   Stop: stop.bat
echo =========================================
goto DONE

:TIMEOUT
del /q "%TEMP%\ul_chk.txt" >nul 2>&1
echo.
echo Server may still be loading. Try: http://localhost:%PORT%
goto DONE

:NO_WSL
echo [ERROR] WSL not found. Run manually:
echo   wsl -e bash -lc "cd /mnt/c/Workarea/github/UsageLens && python3 -m uvicorn backend.server:app --host 0.0.0.0 --port 8000"

:DONE
endlocal
