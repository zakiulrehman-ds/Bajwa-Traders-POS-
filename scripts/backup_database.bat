@echo off
setlocal
cd /d "%~dp0.."

:: 1. Secondary off-drive backup location (change D: if needed)
set "SECOND_DRIVE=D:"
set "OFFDRIVE_DIR=%SECOND_DRIVE%\Bajwa_Traders_Backups"
set "LOG_FILE=backups\backup.log"

if not exist "backups" mkdir "backups"
if exist "%SECOND_DRIVE%\" (
    if not exist "%OFFDRIVE_DIR%" mkdir "%OFFDRIVE_DIR%"
)

:: 2. Timestamp for file name and log entry
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set "stamp=%%i"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""') do set "now_str=%%i"

set "LOCAL_FILE=backups\bajwa_traders_%stamp%.sqlite3"

if not exist "db.sqlite3" (
    echo [%now_str%] ERROR: db.sqlite3 not found. >> "%LOG_FILE%"
    echo ERROR: db.sqlite3 not found.
    if /i not "%~1"=="--auto" pause
    exit /b 1
)

:: 3. Non-blocking SQLite online backup
".venv\Scripts\python.exe" -c "import sqlite3; src=sqlite3.connect('db.sqlite3', timeout=30.0); dst=sqlite3.connect(r'%LOCAL_FILE%'); src.backup(dst, pages=100); dst.close(); src.close()"
if errorlevel 1 (
    echo [%now_str%] ERROR: SQLite backup failed. >> "%LOG_FILE%"
    echo SQLite backup failed!
    if /i not "%~1"=="--auto" pause
    exit /b 1
)

echo [%now_str%] OK: Local backup created -^> %LOCAL_FILE% >> "%LOG_FILE%"
echo Backup created: %LOCAL_FILE%

:: 4. Copy backup and media folder to secondary drive
if exist "%OFFDRIVE_DIR%" (
    copy /Y "%LOCAL_FILE%" "%OFFDRIVE_DIR%\bajwa_traders_%stamp%.sqlite3" >nul
    if errorlevel 1 (
        echo [%now_str%] WARN: Failed to copy backup to %OFFDRIVE_DIR%. >> "%LOG_FILE%"
    ) else (
        echo [%now_str%] OK: Off-drive backup copied -^> %OFFDRIVE_DIR%\bajwa_traders_%stamp%.sqlite3 >> "%LOG_FILE%"
        echo Off-drive copy saved: %OFFDRIVE_DIR%\bajwa_traders_%stamp%.sqlite3
    )
    if exist "media" (
        xcopy "media" "%OFFDRIVE_DIR%\media\" /E /I /Q /Y >nul
    )
) else (
    echo [%now_str%] WARN: Off-drive folder not available (%OFFDRIVE_DIR%). >> "%LOG_FILE%"
)

:: 5. Keep last 30 days of backups on both locations
powershell -NoProfile -Command "Get-ChildItem 'backups\bajwa_traders_*.sqlite3' -ErrorAction SilentlyContinue | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Force"
if exist "%OFFDRIVE_DIR%" (
    powershell -NoProfile -Command "Get-ChildItem '%OFFDRIVE_DIR%\bajwa_traders_*.sqlite3' -ErrorAction SilentlyContinue | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Force"
)

if /i "%~1"=="--auto" exit /b 0
pause