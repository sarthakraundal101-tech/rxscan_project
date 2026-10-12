#!/usr/bin/env bash
# One-step setup for macOS / Linux
set -e
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations scanner
python manage.py migrate
python manage.py seed_medicines
echo "Starting server at http://127.0.0.1:8000"
python manage.py runserver
