#!/usr/bin/env bash
# Render.com build script — runs automatically on every deploy.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py createcachetable
python manage.py create_staff_admin
