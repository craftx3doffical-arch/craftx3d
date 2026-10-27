#!/usr/bin/env bash
# Render.com build script — runs automatically on every deploy.
set -o errexit

# eMudhra CA compromise: pip trusts its own bundled certifi in addition to the
# system store, so upgrade pip + certifi first (pip >= 26.2.2, certifi >= 2026.10.19).
python -m pip install --upgrade "pip>=26.2.2" "certifi>=2026.10.19"

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py createcachetable
python manage.py create_staff_admin
