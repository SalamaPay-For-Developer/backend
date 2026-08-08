#!/bin/bash
set -e

PROJECT_DIR="/var/www/salamapay"
VENV_DIR="$PROJECT_DIR/venv"

echo "=== SalamaPay Production Deployment ==="

# Install dependencies
echo "[1/8] Installing Python dependencies..."
$VENV_DIR/bin/pip install -r requirements.txt

# Install gunicorn + whitenoise
echo "[2/8] Installing gunicorn + whitenoise..."
$VENV_DIR/bin/pip install gunicorn whitenoise

# Create runtime directories
echo "[3/8] Creating runtime directories..."
mkdir -p $PROJECT_DIR/run
mkdir -p $PROJECT_DIR/staticfiles
mkdir -p $PROJECT_DIR/media

# Collect static files
echo "[4/8] Collecting static files..."
$VENV_DIR/bin/python manage.py collectstatic --noinput

# Run migrations
echo "[5/8] Running database migrations..."
$VENV_DIR/bin/python manage.py migrate --noinput

# System check
echo "[6/8] Running system check..."
$VENV_DIR/bin/python manage.py check

# Install systemd services
echo "[7/8] Installing systemd services..."
cp deploy/gunicorn.service /etc/systemd/system/
cp deploy/celery-worker.service /etc/systemd/system/
cp deploy/celery-beat.service /etc/systemd/system/
systemctl daemon-reload

# Install Nginx config
echo "[8/8] Installing Nginx config..."
cp deploy/nginx-salamapay.conf /etc/nginx/sites-available/salamapay
ln -sf /etc/nginx/sites-available/salamapay /etc/nginx/sites-enabled/salamapay
rm -f /etc/nginx/sites-enabled/default
nginx -t

# Restart services
echo "Restarting services..."
systemctl restart gunicorn
systemctl restart celery-worker
systemctl restart celery-beat
systemctl restart nginx

# Enable on boot
systemctl enable gunicorn celery-worker celery-beat nginx

echo ""
echo "=== Deployment Complete ==="
echo "API:      http://144.91.64.180/api/v1/"
echo "Admin:    http://144.91.64.180/admin/"
echo "Swagger:  http://144.91.64.180/api/docs/"
echo ""
echo "Check status:"
echo "  systemctl status gunicorn"
echo "  systemctl status celery-worker"
echo "  systemctl status celery-beat"
echo "  systemctl status nginx"
