@echo off
setlocal
cd /d "%~dp0.."

:: 1. Secondary off-drive backup location (change D: to your USB/other partition or OneDrive folder)
set "SECOND_DRIVE=D:"
set "OFFDRIVE_DIR=%SECOND_DRIVE%\Bajwa_Traders_Backups"

if not exist "backups" mkdir "backups"
if exist "%SECOND_DRIVE%\" (
    if not exist "%OFFDRIVE_DIR%" mkdir "%OFFDRIVE_DIR%"
)

:: 2. Timestamp (YYYY-MM-DD_HH-mm)
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set "stamp=%%i"
set "LOCAL_FILE=backups\bajwa_traders_%stamp%.sqlite3"

:: 3. Non-blocking SQLite online backup (pages=100 + 30s timeout so live POS billing never freezes)
".venv\Scripts\python.exe" -c "import sqlite3; src=sqlite3.connect('db.sqlite3', timeout=30.0); dst=sqlite3.connect(r'%LOCAL_FILE%'); src.backup(dst, pages=100); dst.close(); src.close()"

:: 4. Copy snapshot and product images (media folder) to your second drive
if exist "%OFFDRIVE_DIR%" (
    copy /Y "%LOCAL_FILE%" "%OFFDRIVE_DIR%\bajwa_traders_%stamp%.sqlite3" >nul
    if exist "media" (
        xcopy "media" "%OFFDRIVE_DIR%\media\" /E /I /Q /Y >nul
    )
)

:: 5. Keep last 30 days of backups on both drives automatically
powershell -NoProfile -Command "Get-ChildItem 'backups\bajwa_traders_*.sqlite3' -ErrorAction SilentlyContinue | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Force"
if exist "%OFFDRIVE_DIR%" (
    powershell -NoProfile -Command "Get-ChildItem '%OFFDRIVE_DIR%\bajwa_traders_*.sqlite3' -ErrorAction SilentlyContinue | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Force"
)

echo Backup created: %LOCAL_FILE%
if exist "%OFFDRIVE_DIR%" echo Off-drive copy saved: %OFFDRIVE_DIR%\bajwa_traders_%stamp%.sqlite3
if /i "%~1"=="--auto" exit /b 0
pause