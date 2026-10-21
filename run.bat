@echo off
SETLOCAL EnableDelayedExpansion

echo.
echo  [93m[CraftX3D Studio[0m — Windows Setup
echo  =====================================
echo.

:: ── Check Python ──────────────────────────────────────
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo  [91mERROR: Python not found.[0m
    echo  Install Python 3.10+ from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

FOR /F "tokens=2 delims= " %%v IN ('python --version 2^>^&1') DO SET PYVER=%%v
echo  [92mPython found: %PYVER%[0m

:: ── Create virtual environment ─────────────────────────
IF NOT EXIST "venv" (
    echo.
    echo  Creating virtual environment...
    python -m venv venv
    IF ERRORLEVEL 1 (
        echo  [91mERROR: Could not create venv.[0m
        pause
        exit /b 1
    )
    echo  [92mVirtual environment created.[0m
)

:: ── Activate venv ─────────────────────────────────────
call venv\Scripts\activate.bat
echo  [92mVirtual environment activated.[0m

:: ── Install dependencies ───────────────────────────────
echo.
echo  Installing dependencies...
pip install -r requirements-sqlite.txt -q
IF ERRORLEVEL 1 (
    echo  [91mERROR: pip install failed.[0m
    pause
    exit /b 1
)
echo  [92mDependencies installed.[0m

:: ── Migrations ────────────────────────────────────────
echo.
echo  Running database migrations...
python manage.py makemigrations store manage_portal 2>nul
python manage.py migrate
IF ERRORLEVEL 1 (
    echo.
    echo  [91mERROR: Migration failed.[0m
    echo  Make sure your .env file has correct DB settings,
    echo  OR edit .env to use SQLite (see instructions below).
    pause
    exit /b 1
)
echo  [92mMigrations complete.[0m

:: ── Create superuser ──────────────────────────────────
echo.
echo  Creating admin accounts...
python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); U.objects.filter(username='admin').exists() or U.objects.create_superuser('admin','admin@craftix3d.com','admin123') or print('Django admin: admin / admin123')"

python manage.py shell -c "from manage_portal.models import StaffUser; s=StaffUser(username='admin',full_name='Admin',role='admin',is_active=True); s.set_password('admin123'); s.save() if not StaffUser.objects.filter(username='admin').exists() else print('Staff user exists')"

:: ── Seed initial data ──────────────────────────────────
python manage.py shell -c "from store.models import StoreSettings, AboutPageContent; StoreSettings.objects.exists() or StoreSettings.objects.create(store_name='CraftX3D Studio',gift_wrap_enabled=True,gift_wrap_price=50,free_delivery_above=999,standard_delivery_days=7,express_delivery_days=3); AboutPageContent.objects.exists() or AboutPageContent.objects.create(hero_heading='The Story Behind CraftX3D Studio',hero_subheading='Where creativity meets technology.',story_title='How It All Started',story_content='CraftX3D Studio was born from a passion for 3D printing.',mission_statement='To make high-quality personalised 3D products accessible to everyone.',team_section_title='Meet the Makers',team_subtitle='A passionate team of designers and engineers.',team_quote='Every product we make carries a piece of our passion.')"
echo  [92mInitial data seeded.[0m

:: ── Collect static ────────────────────────────────────
echo.
echo  Collecting static files...
python manage.py collectstatic --noinput -v 0
echo  [92mStatic files collected.[0m

:: ── Done ──────────────────────────────────────────────
echo.
echo  =====================================
echo  [92m  Setup complete! Starting server...[0m
echo  =====================================
echo.
echo   Customer Store :  http://127.0.0.1:8000/
echo   Staff Portal   :  http://127.0.0.1:8000/manage/
echo   Django Admin   :  http://127.0.0.1:8000/admin/
echo.
echo   Staff login    :  admin / admin123
echo   Django admin   :  admin / admin123
echo.
echo  Press Ctrl+C to stop the server.
echo.

python manage.py runserver

pause
