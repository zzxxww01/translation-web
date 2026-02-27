@echo off
set "PORT=54321"
echo Stopping Translation Agent on port %PORT%...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING 2^>nul') do (
    echo Killing PID %%a on port %PORT%
    taskkill /F /PID %%a /T >nul 2>&1
    wmic process where ProcessId=%%a delete >nul 2>&1
    powershell -NoProfile -Command "try { Stop-Process -Id %%a -Force -ErrorAction SilentlyContinue } catch {}" >nul 2>&1
)

echo Done.
powershell -NoProfile -Command "Start-Sleep -Seconds 2" >nul 2>&1
