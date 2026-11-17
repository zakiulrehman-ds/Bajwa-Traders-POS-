@echo off
cd /d "%~dp0.."
echo Installing Bajwa Traders dependencies...
py -3 -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate --run-syncdb
python manage.py collectstatic --noinput
python manage.py createsuperuser
echo.
echo Setup complete. Use start_bajwa_traders.bat to launch the app.
pause
