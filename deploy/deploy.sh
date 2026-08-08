#!/bin/bash
set -e

PROJECT_DIR="/var/www/vhosts/elanbrands.net/lipasalama.co.tz"
VENV_DIR="$PROJECT_DIR/venv"

echo "=== SalamaPay Production Deployment (Plesk-compatible) ==="
echo "Domain: lipasalama.co.tz"
echo "Project: $PROJECT_DIR"
echo ""

# Install dependencies
echo "[1/6] Installing Python dependencies..."
$VENV_DIR/bin/pip install -r requirements.txt

# Install gunicorn + whitenoise
echo "[2/6] Installing gunicorn + whitenoise..."
$VENV_DIR/bin/pip install gunicorn whitenoise

# Create runtime directories
echo "[3/6] Creating runtime directories..."
mkdir -p $PROJECT_DIR/run
mkdir -p $PROJECT_DIR/staticfiles
mkdir -p $PROJECT_DIR/media

# Collect static files
echo "[4/6] Collecting static files..."
$VENV_DIR/bin/python manage.py collectstatic --noinput

# Run migrations
echo "[5/6] Running database migrations..."
$VENV_DIR/bin/python manage.py migrate --noinput

# System check
echo "[6/6] Running system check..."
$VENV_DIR/bin/python manage.py check

# Install systemd services (Plesk hairuhusi systemd)
echo ""
echo "Installing systemd services..."
cp deploy/gunicorn.service /etc/systemd/system/
cp deploy/celery-worker.service /etc/systemd/system/
cp deploy/celery-beat.service /etc/systemd/system/
systemctl daemon-reload

# Restart services (gunicorn + celery only - nginx inaendelea na Plesk)
echo "Restarting services..."
systemctl restart gunicorn || systemctl start gunicorn
systemctl restart celery-worker || systemctl start celery-worker
systemctl restart celery-beat || systemctl start celery-beat

# Enable on boot
systemctl enable gunicorn celery-worker celery-beat

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "IMPORTANT: Nginx haifanywi hapa - Plesk inaendelea nayo!"
echo ""
echo "Endelea na hatua hizi kwenye Plesk Panel:"
echo "  1. Nenda Domains > lipasalama.co.tz"
echo "  2. Bonyeza 'Apache & nginx Settings'"
echo "  3. Nakili maudhui ya deploy/nginx-plesk-directives.conf"
echo "  4. Paste kwenye 'Additional nginx directives'"
echo "  5. Bonyeza 'Apply'"
echo ""
echo "API:      https://lipasalama.co.tz/api/v1/"
echo "Admin:    https://lipasalama.co.tz/admin/"
echo "Swagger:  https://lipasalama.co.tz/api/docs/"
echo ""
echo "Check status:"
echo "  systemctl status gunicorn"
echo "  systemctl status celery-worker"
echo "  systemctl status celery-beat"
