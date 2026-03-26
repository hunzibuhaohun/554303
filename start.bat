@echo off
chcp 65001 >nul
echo Starting Campus Checkin Platform...

cd /d "%~dp0"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run migrations
echo Running migrations...
python manage.py makemigrations
python manage.py migrate

REM Start server
echo Starting development server...
python manage.py runserver 0.0.0.0:8000

pause