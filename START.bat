@echo off
setlocal EnableExtensions

title ChatUI Starting...

REM ==============================================
REM ChatUI Startup Script
REM ==============================================

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

set "BACKEND=%ROOT%\chatui-backend"
set "FRONTEND=%ROOT%\app"

echo.
echo ==============================================
echo              Starting ChatUI
echo ==============================================
echo.

REM Check project files
if not exist "%BACKEND%\main.py" (
    echo ERROR: Backend not found:
    echo %BACKEND%\main.py
    pause
    exit /b 1
)

if not exist "%FRONTEND%\package.json" (
    echo ERROR: Frontend not found:
    echo %FRONTEND%\package.json
    pause
    exit /b 1
)

REM Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Check npm
where npm >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js/npm is not installed or not in PATH.
    pause
    exit /b 1
)

REM Create virtual environment if necessary
echo Checking Python environment...

if not exist "%BACKEND%\.venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    cd /d "%BACKEND%"
    python -m venv .venv

    if errorlevel 1 (
        echo ERROR: Failed to create Python environment.
        pause
        exit /b 1
    )
)

REM Install backend dependencies
echo Installing backend dependencies...

"%BACKEND%\.venv\Scripts\python.exe" -m pip install -r "%BACKEND%\requirements.txt"

if errorlevel 1 (
    echo ERROR: Failed to install backend dependencies.
    pause
    exit /b 1
)

REM Install frontend dependencies if needed
echo.
echo Checking frontend dependencies...

if not exist "%FRONTEND%\node_modules" (
    echo Installing frontend dependencies...
    cd /d "%FRONTEND%"
    call npm install

    if errorlevel 1 (
        echo ERROR: Failed to install frontend dependencies.
        pause
        exit /b 1
    )
)

REM ----------------------------------------------
REM Start backend
REM ----------------------------------------------

echo.
echo Starting ChatUI backend...

start "ChatUI Backend" /min cmd /c "cd /d "%BACKEND%" && "%BACKEND%\.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000"

REM Wait for backend
echo Waiting for backend...

set /a BACKEND_TRIES=0

:WAIT_BACKEND

set /a BACKEND_TRIES+=1

powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"

if not errorlevel 1 goto BACKEND_READY

if %BACKEND_TRIES% GEQ 45 (
    echo.
    echo ERROR: Backend did not start within 90 seconds.
    echo.
    pause
    exit /b 1
)

timeout /t 2 /nobreak >nul
goto WAIT_BACKEND

:BACKEND_READY

echo Backend is ready.

REM ----------------------------------------------
REM Start frontend
REM ----------------------------------------------

echo.
echo Starting ChatUI frontend...

start "ChatUI Frontend" /min cmd /c "cd /d "%FRONTEND%" && call npm run dev -- --host 127.0.0.1"

REM Wait for frontend
echo Waiting for frontend...

set /a FRONTEND_TRIES=0

:WAIT_FRONTEND

set /a FRONTEND_TRIES+=1

powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5173 -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"

if not errorlevel 1 goto FRONTEND_READY

if %FRONTEND_TRIES% GEQ 30 (
    echo.
    echo ERROR: Frontend did not start within 60 seconds.
    pause
    exit /b 1
)

timeout /t 2 /nobreak >nul
goto WAIT_FRONTEND

:FRONTEND_READY

echo.
echo ==============================================
echo       ChatUI started successfully!
echo ==============================================
echo.

start "" "http://127.0.0.1:5173"

echo ChatUI is running.
echo You may close this window.

timeout /t 3 >nul

exit /b 0
