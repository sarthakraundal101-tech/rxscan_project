@echo off
REM One-step setup for Windows (RxScan)
where py >nul 2>nul
if %errorlevel% equ 0 (
    set PY_CMD=py
) else (
    set PY_CMD=python
)

echo [RxScan] Using Python command: %PY_CMD%
if not exist "venv" (
    echo [RxScan] Creating virtual environment...
    %PY_CMD% -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations scanner
python manage.py migrate
python manage.py seed_medicines
echo [RxScan] Starting server at http://127.0.0.1:8000
python manage.py runserver
