"""
CraftX3D Studio — One-command setup & run
Run with:  python setup_and_run.py
"""
import subprocess, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

PY = sys.executable

def ok(msg):  print(f"  [OK] {msg}")
def err(msg): print(f"  [!!] {msg}")
def hdr(msg): print(f"\n  === {msg} ===")

print()
print("  ╔═══════════════════════════════════╗")
print("  ║   CraftX3D Studio  — Setup & Run  ║")
print("  ╚═══════════════════════════════════╝")
print(f"  Python: {sys.version.split()[0]}")

# ── Step 1: Install packages ──────────────────────────────
hdr("1 / 5  Installing packages")

PACKAGES = [
    "Django>=5.1",       # 5.1+ has Python 3.13/3.14 compatibility fixes
    "Pillow>=10.0",
    "python-dotenv>=1.0",
    "whitenoise>=6.0",
]

for pkg in PACKAGES:
    name = pkg.split(">=")[0].strip()
    print(f"  Installing {name}...", end=" ", flush=True)
    result = subprocess.run(
        [PY, "-m", "pip", "install", pkg, "-q", "--disable-pip-version-check"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("done")
    else:
        print("FAILED")
        print(result.stderr[-300:] if result.stderr else "")
        sys.exit(1)

ok("All packages installed")

# ── Step 2: Configure ─────────────────────────────────────
hdr("2 / 5  Configuring environment")

os.environ["DJANGO_SETTINGS_MODULE"] = "craftix3d.settings"
os.environ["USE_SQLITE"] = "True"

# ── Python 3.14 compatibility patch for Django Admin ──────
import sys as _sys
if _sys.version_info >= (3, 13):
    try:
        import django.template.context as _ctx
        def _py314_fixed_copy(self):
            cls = type(self)
            dup = cls.__new__(cls)
            dup.__dict__.update(self.__dict__)
            dup.dicts = self.dicts[:]
            return dup
        _ctx.BaseContext.__copy__ = _py314_fixed_copy
        ok("Applied Python 3.14 Django admin compatibility patch")
    except Exception as _e:
        print(f"  [warn] Could not patch Django: {_e}")

try:
    import django
    django.setup()
    ok(f"Django {django.__version__} configured with SQLite")
except Exception as e:
    err(f"Django setup failed: {e}")
    sys.exit(1)

# ── Step 3: Run migrations ────────────────────────────────
hdr("3 / 5  Setting up database")

from django.core.management import call_command
import io

try:
    call_command("makemigrations", "store", "manage_portal", verbosity=0, stdout=io.StringIO())
    ok("Migrations created")
    call_command("migrate", verbosity=0, stdout=io.StringIO())
    ok("Database tables created (db.sqlite3)")
except Exception as e:
    err(f"Migration error: {e}")
    raise

# ── Step 4: Seed admin & initial data ────────────────────
hdr("4 / 5  Creating admin accounts & seed data")

from manage_portal.models import StaffUser
from store.models import StoreSettings, AboutPageContent

if not StaffUser.objects.filter(username="admin").exists():
    s = StaffUser(username="admin", full_name="Admin", role="admin", is_active=True)
    s.set_password("admin123")
    s.save()
    ok("Staff account created  →  admin / admin123")
else:
    ok("Staff account already exists  →  admin / admin123")

from django.contrib.auth.models import User
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser("admin", "admin@craftix3d.com", "admin123")
    ok("Django superuser created  →  admin / admin123")
else:
    ok("Django superuser already exists")

StoreSettings.objects.get_or_create(defaults={
    'store_name': 'CraftX3D Studio',
    'gift_wrap_enabled': True, 'gift_wrap_price': 50,
    'free_delivery_above': 999, 'standard_delivery_days': 7, 'express_delivery_days': 3,
})
AboutPageContent.objects.get_or_create(defaults={
    'hero_heading': 'The Story Behind CraftX3D Studio',
    'hero_subheading': 'Where creativity meets technology.',
    'story_title': 'How It All Started',
    'story_content': 'CraftX3D Studio was born from a passion for 3D printing.',
    'mission_statement': 'Quality, precision, and personalisation — always.',
    'team_section_title': 'Meet the Makers',
    'team_subtitle': 'A passionate team of designers and engineers.',
    'team_quote': 'Every product we make carries a piece of our passion.',
})
ok("Seed data ready")

# ── Step 5: Start server ──────────────────────────────────
hdr("5 / 5  Starting server")

print()
print("  ╔══════════════════════════════════════════╗")
print("  ║           Server is running!             ║")
print("  ╠══════════════════════════════════════════╣")
print("  ║  Customer Store :  http://127.0.0.1:8000 ║")
print("  ║  Staff Portal   :  /manage/              ║")
print("  ║  Django Admin   :  /admin/               ║")
print("  ╠══════════════════════════════════════════╣")
print("  ║  Login: admin   Password: admin123        ║")
print("  ╚══════════════════════════════════════════╝")
print()
print("  Press Ctrl+C to stop.")
print()

# Apply the patch again at runtime (for the WSGI server process)
try:
    import django.template.context as _ctx2
    def _py314_patch(self):
        cls = type(self)
        dup = cls.__new__(cls)
        dup.__dict__.update(self.__dict__)
        dup.dicts = self.dicts[:]
        return dup
    _ctx2.BaseContext.__copy__ = _py314_patch
except Exception:
    pass

call_command("runserver", "127.0.0.1:8000")
