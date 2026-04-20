@echo off
REM Translation Agent - 项目数据备份脚本 (Windows)
REM 用途：定期备份 projects/ 目录

setlocal enabledelayedexpansion

REM 配置
set BACKUP_DIR=backups
set PROJECTS_DIR=projects
set RETENTION_DAYS=7

REM 生成时间戳
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%
set BACKUP_FILE=projects_backup_%TIMESTAMP%.zip

REM 创建备份目录
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo [%date% %time%] Starting backup...

REM 使用 PowerShell 压缩（Windows 内置）
powershell -Command "Compress-Archive -Path '%PROJECTS_DIR%' -DestinationPath '%BACKUP_DIR%\%BACKUP_FILE%' -Force"

if %errorlevel% equ 0 (
    echo [%date% %time%] Backup created: %BACKUP_FILE%
) else (
    echo [%date% %time%] Backup failed!
    exit /b 1
)

REM 清理旧备份（保留最近 N 天）
forfiles /P "%BACKUP_DIR%" /M "projects_backup_*.zip" /D -%RETENTION_DAYS% /C "cmd /c del @path" 2>nul
echo [%date% %time%] Old backups cleaned (retention: %RETENTION_DAYS% days)

echo [%date% %time%] Backup completed successfully

endlocal
