# SalamaPay Backend - Plesk Deployment Guide

Domain: **api.lipasalama.co.tz**
VPS: **root@ns1:/var/www/salamapay#**

## Muhtasari

Backend ya Django itaendeshwa na Gunicorn (systemd), na Plesk itasimamia nginx.
Hatuwezi nginx moja kwa moja - tutatumia "Additional nginx directives" za Plesk.

---

## Hatua 1: Sakinisha project kwenye VPS

```bash
# Kama bado huna folder, ilete project kutoka local machine
# Njia rahisi: git clone au scp

# Kama unatumia git:
cd /var/www/salamapay
git clone <repo-url> .

# AU kopisha files kutoka kwenye local machine kwa scp:
# scp -r ./* root@ns1:/var/www/salamapay/
```

## Hatua 2:unda virtual environment

```bash
cd /var/www/salamapay
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn whitenoise
```

## Hatua 3: Sakinisha PostgreSQL + Redis (kama hazipo)

```bash
# PostgreSQL
apt install postgresql postgresql-contrib -y
sudo -u postgres psql -c "CREATE USER salamapay WITH PASSWORD 'salamapay';"
sudo -u postgres psql -c "CREATE DATABASE salamapay OWNER salamapay;"

# Redis
apt install redis-server -y
systemctl enable redis-server
systemctl start redis-server
```

## Hatua 4: Endesha deploy script

```bash
cd /var/www/salamapay
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

Script hii itafanya:
- Install dependencies
- Collect static files
- Run migrations
- Install + start systemd services (gunicorn, celery-worker, celery-beat)
- **HAIGUSI nginx** (Plesk inaendelea nayo)

## Hatua 5: Configure Plesk nginx directives

1. Nenda **Plesk Panel**
2. **Domains** > `api.lipasalama.co.tz`
3. Bonyeza **"Apache & nginx Settings"**
4. Scroll chini hadi **"Additional nginx directives"**
5. Nakili maudhui yote kutoka `deploy/nginx-plesk-directives.conf`
6. Paste kwenye box hiyo
7. Bonyeza **"Apply"** au **"OK"**

## Hatua 6: Hakikisha SSL imewashwa

1. **Plesk Panel** > **Domains** > `api.lipasalama.co.tz`
2. Bonyeza **"SSL/TLS Certificates"**
3. Washa **"Let's Encrypt"** certificate
4. Hakikisha SSL inafanya kazi: `https://api.lipasalama.co.tz/api/v1/`

## Hatua 7: Hakikisha DNS inafanya kazi

DNS record ya `api.lipasalama.co.tz` lazima ielekeze kwenye IP ya VPS yako (`144.91.64.180`).

```
A    api.lipasalama.co.tz    144.91.64.180
```

---

## Kagua status ya services

```bash
systemctl status gunicorn
systemctl status celery-worker
systemctl status celery-beat
systemctl status redis-server
systemctl status postgresql
```

## Logs

```bash
# Gunicorn logs
journalctl -u gunicorn -f

# Celery worker logs
journalctl -u celery-worker -f

# Celery beat logs
journalctl -u celery-beat -f
```

## Test API

```bash
curl https://api.lipasalama.co.tz/api/v1/
curl https://api.lipasalama.co.tz/api/docs/
```

---

## Kama kuna shida

### Gunicorn socket haiwezi kupatikana
```bash
ls -la /var/www/salamapay/run/gunicorn.sock
# Kama haipo, restart gunicorn:
systemctl restart gunicorn
```

### Nginx inarudisha 502 Bad Gateway
- Hakikisha gunicorn inaendelea: `systemctl status gunicorn`
- Hakikisha socket ipo: `ls -la /var/www/salamapay/run/gunicorn.sock`
- Hakikisha Plesk directives zimekwisha applied

### Database shida
```bash
sudo -u postgres psql -c "\l"  # ona databases
sudo -u postgres psql -c "SELECT * FROM pg_user WHERE usename='salamapay';"
```

### CORS shida
- Hakikisha `CORS_ALLOWED_ORIGINS` kwenye `.env` ina domain yako
- Kama frontend ipo kwenye domain tofauti, ongeza kwenye `.env`
