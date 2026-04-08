@echo off
setlocal
title Translation Agent

rem ========== Environment checks ==========

rem Prefer project-local Python executable from .venv
set "PYTHON_CMD=python"
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0.venv\Scripts\python.exe"
    echo [INFO] Using virtual environment Python: %~dp0.venv\Scripts\python.exe
) else (
    echo [WARNING] No local .venv Python found, using global Python.
)

rem Check for Python
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

rem Check for uvicorn
%PYTHON_CMD% -c "import uvicorn" 2>nul
if errorlevel 1 (
    echo [ERROR] uvicorn not installed
    echo Installing: %PYTHON_CMD% -m pip install uvicorn
    %PYTHON_CMD% -m pip install uvicorn
)

rem Check .env file
if not exist .env (
    echo [WARNING] .env file not found!
    echo Please copy .env.example to .env and configure your API keys.
    echo(
)

rem ========== Args ==========
set "FORCE_BUILD=0"
set "RELOAD_ARGS="
set "PORT=54321"
set "FORCE_KILL_PORT=0"
for %%a in (%*) do (
    if /I "%%a"=="--force-build" set "FORCE_BUILD=1"
    if /I "%%a"=="-f" set "FORCE_BUILD=1"
    if /I "%%a"=="--dev" set "RELOAD_ARGS=--reload"
    if /I "%%a"=="--force-kill-port" set "FORCE_KILL_PORT=1"
    echo %%a | findstr /I /B "--port=" >nul && (
        for /f "tokens=2 delims==" %%p in ("%%a") do set "PORT=%%p"
    )
)

echo ========================================
echo   Translation Agent
echo   Starting service on port %PORT%...
echo ========================================
echo(

set "FRONTEND_DIR=web\frontend"
set "FRONTEND_DIST=%FRONTEND_DIR%\dist"
set "FRONTEND_STAMP=%FRONTEND_DIST%\.buildstamp"
set "STARTUP_LOG_DIR=%~dp0artifacts\startup-logs"
set "FRONTEND_INSTALL_LOG=%STARTUP_LOG_DIR%\frontend-install.log"
set "FRONTEND_BUILD_LOG=%STARTUP_LOG_DIR%\frontend-build.log"
set "NEED_BUILD=0"

if not exist "%STARTUP_LOG_DIR%" mkdir "%STARTUP_LOG_DIR%" >nul 2>&1

if "%FORCE_BUILD%"=="1" (
    echo [INFO] Force rebuild requested.
    if exist "%FRONTEND_DIST%" rmdir /S /Q "%FRONTEND_DIST%"
    set "NEED_BUILD=1"
) else if not exist "%FRONTEND_DIST%\index.html" (
    set "NEED_BUILD=1"
) else (
    powershell -NoProfile -Command ^
        "$ErrorActionPreference='SilentlyContinue';" ^
        "$files=@();" ^
        "if(Test-Path 'web\\frontend\\src'){ $files += Get-ChildItem -Path 'web\\frontend\\src' -Recurse -File }" ^
        "if(Test-Path 'web\\frontend\\public'){ $files += Get-ChildItem -Path 'web\\frontend\\public' -Recurse -File }" ^
        "$cfg=@(" ^
        "'web\\frontend\\index.html'," ^
        "'web\\frontend\\package.json'," ^
        "'web\\frontend\\package-lock.json'," ^
        "'web\\frontend\\pnpm-lock.yaml'," ^
        "'web\\frontend\\yarn.lock'," ^
        "'web\\frontend\\vite.config.ts'," ^
        "'web\\frontend\\vite.config.js'," ^
        "'web\\frontend\\tsconfig.json'," ^
        "'web\\frontend\\tsconfig.node.json'," ^
        "'web\\frontend\\tailwind.config.js'," ^
        "'web\\frontend\\tailwind.config.ts'," ^
        "'web\\frontend\\postcss.config.js'," ^
        "'web\\frontend\\postcss.config.cjs'," ^
        "'web\\frontend\\.env'," ^
        "'web\\frontend\\.env.local'," ^
        "'web\\frontend\\.env.development'," ^
        "'web\\frontend\\.env.production'," ^
        "'web\\frontend\\.eslintrc'," ^
        "'web\\frontend\\.eslintrc.js'," ^
        "'web\\frontend\\.prettierrc'," ^
        "'web\\frontend\\.prettierrc.js'" ^
        ");" ^
        "$cfgFiles=@(); foreach($c in $cfg){ if(Test-Path $c){ $cfgFiles += Get-Item $c } }" ^
        "$latest=($files + $cfgFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 1);" ^
        "$stamp = Get-Item 'web\\frontend\\dist\\.buildstamp' -ErrorAction SilentlyContinue;" ^
        "if(-not $stamp){ exit 1 }" ^
        "if($latest -and $latest.LastWriteTime -gt $stamp.LastWriteTime){ exit 2 }" ^
        "exit 0"
    if errorlevel 1 set "NEED_BUILD=1"
)

if "%NEED_BUILD%"=="1" (
    echo [INFO] Frontend changed. Building...
    pushd %FRONTEND_DIR%
    if not exist "node_modules" (
        echo [INFO] Installing frontend dependencies...
        call npm install > "%FRONTEND_INSTALL_LOG%" 2>&1
        if errorlevel 1 (
            echo [ERROR] Frontend dependency installation failed.
            echo [INFO] Install log: %FRONTEND_INSTALL_LOG%
            powershell -NoProfile -Command "if(Test-Path '%FRONTEND_INSTALL_LOG%'){ Get-Content '%FRONTEND_INSTALL_LOG%' -Tail 40 }"
            popd
            exit /b 1
        )
    )
    echo [INFO] Frontend build log: %FRONTEND_BUILD_LOG%
    call npm run build > "%FRONTEND_BUILD_LOG%" 2>&1
    if errorlevel 1 (
        echo [ERROR] Frontend build failed.
        echo [INFO] Build log: %FRONTEND_BUILD_LOG%
        powershell -NoProfile -Command "if(Test-Path '%FRONTEND_BUILD_LOG%'){ Get-Content '%FRONTEND_BUILD_LOG%' -Tail 60 }"
        popd
        exit /b 1
    )
    popd
    powershell -NoProfile -Command "New-Item -ItemType File -Force -Path 'web\\frontend\\dist\\.buildstamp' | Out-Null"
    echo(
) else (
    echo [INFO] Frontend is up-to-date. Skipping build.
    echo(
)

rem Remove source maps to save space
if exist "web\frontend\dist\assets\*.map" (
    echo [INFO] Removing source map files...
    del /Q "web\frontend\dist\assets\*.map" 2>nul
)

rem ========== Force cleanup for port ==========
echo [INFO] Forcefully cleaning port %PORT%...

rem Method 1: netstat + taskkill (LISTENING only)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING 2^>nul') do (
    echo [INFO] Killing process %%a using port %PORT%
    taskkill /F /PID %%a >nul 2>&1
    wmic process where ProcessId=%%a delete >nul 2>&1
    powershell -NoProfile -Command "try { Stop-Process -Id %%a -Force -ErrorAction SilentlyContinue } catch {}" >nul 2>&1
)

rem Method 2: kill python processes that may hold the port
for /f "tokens=2" %%a in ('tasklist /fi "imagename eq python.exe" /fo table /nh 2^>nul') do (
    for /f "tokens=5" %%b in ('netstat -ano ^| findstr %%a ^| findstr :%PORT% 2^>nul') do (
        echo [INFO] Killing Python process %%a that may be using port %PORT%
        taskkill /F /PID %%a >nul 2>&1
        powershell -NoProfile -Command "try { Stop-Process -Id %%a -Force -ErrorAction SilentlyContinue } catch {}" >nul 2>&1
    )
)

rem Method 2b: kill stale uvicorn processes for the same app/port even if they are not listening
powershell -NoProfile -Command ^
    "$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'src\.api\.app:app' -and $_.CommandLine -match '--port %PORT%' };" ^
    "foreach($p in $procs){ try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }" >nul 2>&1

rem Method 3: netsh reset (requires admin)
netsh int ipv4 reset >nul 2>&1

rem Wait for port release (timeout fails under input redirection)
echo [INFO] Waiting for port release...
powershell -NoProfile -Command "Start-Sleep -Seconds 3" >nul 2>&1

rem Verify port is free (LISTENING)
netstat -ano | findstr :%PORT% | findstr LISTENING >nul 2>&1
if %errorlevel% equ 0 (
    echo [WARNING] Port %PORT% still occupied, attempting final cleanup...
    rem Final attempt: force kill again
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% 2^>nul') do (
        echo [INFO] Final attempt: killing PID %%a
        taskkill /F /PID %%a /T >nul 2>&1
        wmic process where ProcessId=%%a delete >nul 2>&1
        powershell -NoProfile -Command "try { Stop-Process -Id %%a -Force -ErrorAction SilentlyContinue } catch {}" >nul 2>&1
    )
    powershell -NoProfile -Command "Start-Sleep -Seconds 2" >nul 2>&1
)

rem Final check (exit if still occupied)
netstat -ano | findstr :%PORT% | findstr LISTENING >nul 2>&1
if %errorlevel% equ 0 (
    echo [ERROR] Unable to free port %PORT% ^(LISTENING^). Please run as Administrator or restart your computer.
    echo [INFO] Current port %PORT% usage:
    netstat -ano | findstr :%PORT%
    echo(
    pause
    exit /b 1
) else (
    echo [SUCCESS] Port %PORT% is now available ^(LISTENING not detected^).
)

rem Ignore remaining connections on port (ESTABLISHED, TIME_WAIT, etc.)

rem ========== Start server ==========
echo(
echo [INFO] Starting server...
echo [INFO] API:      http://localhost:%PORT%/api
echo [INFO] Web UI:   http://localhost:%PORT%
echo [INFO] API Docs: http://localhost:%PORT%/docs
echo(
echo A new server window will open. Press Ctrl+C there to stop.
echo ========================================
echo(

start "Translation Agent Server" "%PYTHON_CMD%" -m uvicorn src.api.app:app --host 0.0.0.0 --port %PORT% --timeout-keep-alive 5 --timeout-graceful-shutdown 10 --limit-concurrency 100 --limit-max-requests 1000 %RELOAD_ARGS%
exit /b 0
