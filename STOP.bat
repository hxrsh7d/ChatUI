@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem ============================================================================
rem  STOP.bat - One-click shutdown for ChatUI
rem
rem  Stops only the backend (FastAPI, port 8000) and frontend (Vite, port
rem  5173) processes belonging to THIS project. Identifies them by the PID
rem  recorded at startup AND by verifying the process's own command line
rem  references this project folder (or uvicorn/vite) before touching it, so
rem  unrelated Python/Node processes elsewhere on the machine are left alone.
rem  Does not close the browser.
rem ============================================================================

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "BACKEND_DIR=%ROOT%\chatui-backend"
set "FRONTEND_DIR=%ROOT%\app"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"

set "LOG=%ROOT%\chatui-start.log"
set "BACKEND_PID_FILE=%ROOT%\.chatui-backend.pid"
set "FRONTEND_PID_FILE=%ROOT%\.chatui-frontend.pid"
set "HELPER_PS1=%TEMP%\chatui_stop_helper_%RANDOM%.ps1"

echo ============================================== >> "%LOG%"
echo ChatUI shutdown - %DATE% %TIME% >> "%LOG%"
echo ============================================== >> "%LOG%"

echo ================================================
echo  ChatUI - stopping...
echo ================================================
echo.

where powershell >nul 2>&1
if errorlevel 1 (
    echo [FAILED] PowerShell was not found on PATH.
    pause
    exit /b 1
)

rem ----------------------------------------------------------------------
rem Reconstruct the PowerShell helper from an embedded Base64 blob (see
rem START.bat for why: it avoids hand-escaping PowerShell syntax for
rem cmd.exe, which is fragile). It stops ONE project process at a time:
rem by stored PID, falling back to whatever is listening on its known
rem port - but only after confirming the process's command line actually
rem belongs to this project. Deleted again right after it runs.
rem ----------------------------------------------------------------------
del "%HELPER_PS1%" >nul 2>&1

set "B64=cGFyYW0oCiAgICBbc3RyaW5nXSRQaWRGaWxlLAogICAgW3N0cmluZ10kUHJvamVjdERpciwKICAgIFtpbnRdJFBvcnQsCiAgICBbc3RyaW5nXSRMYWJlbCwKICAgIFtzdHJpbmddJE1haW5Mb2cKKQoKZnVuY3Rpb24gV3JpdGUtTG9nKFtzdHJpbmddJG1zZykgewog"
set "B64=%B64%ICAgJGxpbmUgPSAoR2V0LURhdGUgLUZvcm1hdCAneXl5eS1NTS1kZCBISDptbTpzcycpICsgJyAgJyArICRtc2cKICAgIEFkZC1Db250ZW50IC1QYXRoICRNYWluTG9nIC1WYWx1ZSAkbGluZQogICAgV3JpdGUtSG9zdCAkbXNnCn0KCiRjYW5kaWRhdGVzID0gTmV3"
set "B64=%B64%LU9iamVjdCBTeXN0ZW0uQ29sbGVjdGlvbnMuR2VuZXJpYy5MaXN0W2ludF0KCmlmIChUZXN0LVBhdGggJFBpZEZpbGUpIHsKICAgICRyYXcgPSBHZXQtQ29udGVudCAkUGlkRmlsZSAtRXJyb3JBY3Rpb24gU2lsZW50bHlDb250aW51ZQogICAgJHN0b3JlZFRleHQg"
set "B64=%B64%PSAkbnVsbAogICAgaWYgKCRyYXcgLWlzIFthcnJheV0pIHsgaWYgKCRyYXcuTGVuZ3RoIC1ndCAwKSB7ICRzdG9yZWRUZXh0ID0gJHJhd1swXSB9IH0gZWxzZSB7ICRzdG9yZWRUZXh0ID0gJHJhdyB9CiAgICAkc3RvcmVkUGlkID0gMAogICAgaWYgKCRzdG9yZWRU"
set "B64=%B64%ZXh0IC1hbmQgW2ludF06OlRyeVBhcnNlKCRzdG9yZWRUZXh0LlRyaW0oKSwgW3JlZl0kc3RvcmVkUGlkKSkgewogICAgICAgIGlmICgtbm90ICRjYW5kaWRhdGVzLkNvbnRhaW5zKCRzdG9yZWRQaWQpKSB7ICRjYW5kaWRhdGVzLkFkZCgkc3RvcmVkUGlkKSB9CiAg"
set "B64=%B64%ICB9Cn0KCnRyeSB7CiAgICAkY29ubnMgPSBHZXQtTmV0VENQQ29ubmVjdGlvbiAtTG9jYWxQb3J0ICRQb3J0IC1TdGF0ZSBMaXN0ZW4gLUVycm9yQWN0aW9uIFNpbGVudGx5Q29udGludWUKICAgIGZvcmVhY2ggKCRjIGluICRjb25ucykgewogICAgICAgIGlmICgt"
set "B64=%B64%bm90ICRjYW5kaWRhdGVzLkNvbnRhaW5zKCRjLk93bmluZ1Byb2Nlc3MpKSB7ICRjYW5kaWRhdGVzLkFkZCgkYy5Pd25pbmdQcm9jZXNzKSB9CiAgICB9Cn0gY2F0Y2ggewp9CgokYW55U3RvcHBlZCA9ICRmYWxzZQpmb3JlYWNoICgkcHJvY0lkIGluICRjYW5kaWRh"
set "B64=%B64%dGVzKSB7CiAgICAkd21pUHJvYyA9IEdldC1DaW1JbnN0YW5jZSBXaW4zMl9Qcm9jZXNzIC1GaWx0ZXIgKCdQcm9jZXNzSWQgPSAnICsgJHByb2NJZCkgLUVycm9yQWN0aW9uIFNpbGVudGx5Q29udGludWUKICAgIGlmICgtbm90ICR3bWlQcm9jKSB7IGNvbnRpbnVl"
set "B64=%B64%IH0KICAgICRjbWRMaW5lID0gW3N0cmluZ10kd21pUHJvYy5Db21tYW5kTGluZQogICAgJGNtZExvd2VyID0gJGNtZExpbmUuVG9Mb3dlcigpCiAgICAkcHJvakxvd2VyID0gJFByb2plY3REaXIuVG9Mb3dlcigpCiAgICAkaXNNYXRjaCA9ICRmYWxzZQogICAgaWYg"
set "B64=%B64%KCRjbWRMb3dlci5Db250YWlucygkcHJvakxvd2VyKSkgeyAkaXNNYXRjaCA9ICR0cnVlIH0KICAgIGlmICgkTGFiZWwgLWVxICdiYWNrZW5kJyAtYW5kICRjbWRMb3dlci5Db250YWlucygndXZpY29ybicpKSB7ICRpc01hdGNoID0gJHRydWUgfQogICAgaWYgKCRM"
set "B64=%B64%YWJlbCAtZXEgJ2Zyb250ZW5kJyAtYW5kICRjbWRMb3dlci5Db250YWlucygndml0ZScpKSB7ICRpc01hdGNoID0gJHRydWUgfQogICAgaWYgKCRMYWJlbCAtZXEgJ2Zyb250ZW5kJyAtYW5kICRjbWRMb3dlci5Db250YWlucygnbnBtIHJ1biBkZXYnKSkgeyAkaXNN"
set "B64=%B64%YXRjaCA9ICR0cnVlIH0KICAgIGlmICgtbm90ICRpc01hdGNoKSB7CiAgICAgICAgV3JpdGUtTG9nICgnU2tpcHBlZCBwaWQ9JyArICRwcm9jSWQgKyAnIGZvciAnICsgJExhYmVsICsgJyAtIGNvbW1hbmQgbGluZSBkaWQgbm90IG1hdGNoIHRoaXMgcHJvamVjdDog"
set "B64=%B64%JyArICRjbWRMaW5lKQogICAgICAgIGNvbnRpbnVlCiAgICB9CiAgICBXcml0ZS1Mb2cgKCdTdG9wcGluZyAnICsgJExhYmVsICsgJyBwaWQ9JyArICRwcm9jSWQgKyAnIDogJyArICRjbWRMaW5lKQogICAgU3RhcnQtUHJvY2VzcyAtRmlsZVBhdGggJ3Rhc2traWxs"
set "B64=%B64%LmV4ZScgLUFyZ3VtZW50TGlzdCAnL1BJRCcsICRwcm9jSWQsICcvVCcgLVdpbmRvd1N0eWxlIEhpZGRlbiAtV2FpdCAtRXJyb3JBY3Rpb24gU2lsZW50bHlDb250aW51ZQogICAgU3RhcnQtU2xlZXAgLU1pbGxpc2Vjb25kcyAxNTAwCiAgICAkc3RpbGwgPSBHZXQt"
set "B64=%B64%UHJvY2VzcyAtSWQgJHByb2NJZCAtRXJyb3JBY3Rpb24gU2lsZW50bHlDb250aW51ZQogICAgaWYgKCRzdGlsbCkgewogICAgICAgIFN0YXJ0LVByb2Nlc3MgLUZpbGVQYXRoICd0YXNra2lsbC5leGUnIC1Bcmd1bWVudExpc3QgJy9QSUQnLCAkcHJvY0lkLCAnL1Qn"
set "B64=%B64%LCAnL0YnIC1XaW5kb3dTdHlsZSBIaWRkZW4gLVdhaXQgLUVycm9yQWN0aW9uIFNpbGVudGx5Q29udGludWUKICAgICAgICBXcml0ZS1Mb2cgKCdGb3JjZS1zdG9wcGVkICcgKyAkTGFiZWwgKyAnIHBpZD0nICsgJHByb2NJZCkKICAgIH0KICAgICRhbnlTdG9wcGVk"
set "B64=%B64%ID0gJHRydWUKfQoKaWYgKC1ub3QgJGFueVN0b3BwZWQpIHsKICAgIFdyaXRlLUxvZyAoJ05vIHJ1bm5pbmcgJyArICRMYWJlbCArICcgcHJvY2VzcyBmb3VuZCBmb3IgdGhpcyBwcm9qZWN0IChwaWQgZmlsZSAvIHBvcnQgJyArICRQb3J0ICsgJykuJykKfQoKaWYg"
set "B64=%B64%KFRlc3QtUGF0aCAkUGlkRmlsZSkgeyBSZW1vdmUtSXRlbSAkUGlkRmlsZSAtRm9yY2UgLUVycm9yQWN0aW9uIFNpbGVudGx5Q29udGludWUgfQpleGl0IDAK"

powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.IO.File]::WriteAllText('%HELPER_PS1%', [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('%B64%')))"
if errorlevel 1 (
    echo [FAILED] Could not write the temporary PowerShell helper script.
    pause
    exit /b 1
)
if not exist "%HELPER_PS1%" (
    echo [FAILED] Temporary PowerShell helper script was not created.
    pause
    exit /b 1
)

echo Stopping backend...
powershell -NoProfile -ExecutionPolicy Bypass -File "%HELPER_PS1%" -PidFile "%BACKEND_PID_FILE%" -ProjectDir "%BACKEND_DIR%" -Port %BACKEND_PORT% -Label "backend" -MainLog "%LOG%"

echo Stopping frontend...
powershell -NoProfile -ExecutionPolicy Bypass -File "%HELPER_PS1%" -PidFile "%FRONTEND_PID_FILE%" -ProjectDir "%FRONTEND_DIR%" -Port %FRONTEND_PORT% -Label "frontend" -MainLog "%LOG%"

del "%HELPER_PS1%" >nul 2>&1

echo.
echo ================================================
echo  Done. ChatUI backend and frontend have been stopped, if they were running.
echo  Full log: %LOG%
echo ================================================
timeout /t 3 >nul
exit /b 0
