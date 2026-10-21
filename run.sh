#!/bin/bash
# ═══════════════════════════════════════════════════════
#  CraftX3D Studio — Quick Setup & Run Script
# ═══════════════════════════════════════════════════════

set -e

echo ""
echo "🖨️  CraftX3D Studio — Django Setup"
echo "════════════════════════════════════"

# ─── 1. Install dependencies ──────────────────────────
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements.txt --break-system-packages -q

# ─── 2. Check .env ────────────────────────────────────
if [ ! -f .env ]; then
  echo ""
  echo "⚙️  Creating .env from .env.example..."
  cp .env.example .env
  echo "   ⚠️  Edit .env with your database credentials before proceeding!"
  echo "   Using SQLite for quick test run..."
  # Patch settings for SQLite if no real DB configured
fi

# ─── 3. Run migrations ────────────────────────────────
echo ""
echo "🗃️  Running migrations..."
python manage.py makemigrations store manage_portal 2>/dev/null || true
python manage.py migrate

# ─── 4. Create superuser (skip if exists) ─────────────
echo ""
echo "👤 Creating Django superuser (if needed)..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@craftix3d.com', 'admin123')
    print('  ✅ Superuser created: admin / admin123')
else:
    print('  ℹ️  Superuser already exists')
" 2>/dev/null

# ─── 5. Create Staff user ─────────────────────────────
echo ""
echo "🔐 Creating Staff portal admin..."
python manage.py shell -c "
from manage_portal.models import StaffUser
if not StaffUser.objects.filter(username='admin').exists():
    s = StaffUser(username='admin', full_name='Admin', role='admin', is_active=True)
    s.set_password('admin123')
    s.save()
    print('  ✅ Staff user created: admin / admin123')
else:
    print('  ℹ️  Staff user already exists')
"

# ─── 6. Create initial store data ─────────────────────
echo ""
echo "🏪 Setting up initial store data..."
python manage.py shell -c "
from store.models import StoreSettings, AboutPageContent
if not StoreSettings.objects.exists():
    StoreSettings.objects.create(
        store_name='CraftX3D Studio',
        free_delivery_above=999,
        gift_wrap_enabled=True,
        gift_wrap_price=50,
        standard_delivery_days=7,
        express_delivery_days=3,
    )
    print('  ✅ StoreSettings created')

if not AboutPageContent.objects.exists():
    AboutPageContent.objects.create(
        hero_heading='The Story Behind CraftX3D Studio',
        hero_subheading='Where creativity meets technology. We turn your ideas into beautiful 3D-printed realities.',
        story_title='How It All Started',
        story_content='CraftX3D Studio was born from a passion for 3D printing and a love for creating unique, personalised gifts.\n\nWhat started as a hobby project quickly became a full-fledged studio when we realised how many people wanted beautiful, custom-made objects that you just cannot find in stores.',
        mission_statement='To make high-quality, personalised 3D printed products accessible to everyone — turning ordinary moments into extraordinary memories.',
        team_section_title='Meet the Makers',
        team_subtitle='A passionate team of designers and engineers dedicated to crafting perfection.',
        team_quote='Every product we make carries a piece of our passion. We are not just printing objects — we are creating memories.',
    )
    print('  ✅ AboutPageContent created')
"

# ─── 7. Collect static files ──────────────────────────
echo ""
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput -v 0

# ─── 8. Done! ─────────────────────────────────────────
echo ""
echo "════════════════════════════════════"
echo "✅  Setup Complete!"
echo ""
echo "  Customer Store:  http://localhost:8000/"
echo "  Staff Portal:    http://localhost:8000/manage/"
echo "  Django Admin:    http://localhost:8000/admin/"
echo ""
echo "  Staff login:     admin / admin123"
echo "  Django admin:    admin / admin123"
echo ""
echo "  Starting development server..."
echo "════════════════════════════════════"
echo ""

python manage.py runserver 0.0.0.0:8000
