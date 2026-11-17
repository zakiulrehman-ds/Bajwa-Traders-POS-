@echo off
setlocal
cd /d "%~dp0.."

if not exist .venv\Scripts\pythonw.exe (
    echo Bajwa Traders is not installed. Run setup_windows.bat first.
    pause
    exit /b 1
)

netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
if errorlevel 1 (
    start "" /B cmd /c ".venv\Scripts\pythonw.exe manage.py runserver 0.0.0.0:8000 > server.log 2>&1"
    timeout /t 3 /nobreak >nul
)

set "CHROME_EXE="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined CHROME_EXE if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined CHROME_EXE if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=%LocalAppData%\Google\Chrome\Application\chrome.exe"

if defined CHROME_EXE (
    start "" "%CHROME_EXE%" --app=http://127.0.0.1:8000 --kiosk-printing --no-first-run
) else (
    where msedge.exe >nul 2>nul
    if %errorlevel%==0 (
        start "" msedge.exe --app=http://127.0.0.1:8000 --kiosk-printing --no-first-run
    ) else (
        start "" http://127.0.0.1:8000
    )
)
endlocal