#!/bin/sh
set -e
python manage.py migrate --noinput
python manage.py seed_medicines
python manage.py collectstatic --noinput || true
exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 rxscan.wsgi:application
