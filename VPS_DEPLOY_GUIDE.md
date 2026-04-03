# Dita Backend: VPS Deployment Guide

This guide provides steps to deploy the Dita Backend to a Linux VPS (Ubuntu/Debian recommended).

## 1. System Preparation

Update your system and install necessary packages (if not already installed):
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv libpq-dev postgresql-client redis-server nginx curl -y
```

## 2. Database (Neon Postgres)

Since you are using **Neon Postgres** via `DATABASE_URL`, you don't need to set up a local database on the VPS. Just ensure `postgresql-client` is installed so `psycopg2` can be built during installation.

## 3. Deployment Steps

1. **Clone and Setup Environment**:
   ```bash
   # navigate to your app directory
   cd /var/www/Dita-app-backend
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements/base.txt
   ```

2. **Environment Variables**:
   You can keep your current `.env`. This new version will automatically use your `DATABASE_URL` for the Neon connection and your `DJANGO_SECRET_KEY`.

3. **Firebase Setup**:
   Upload your real `serviceAccountKey.json` to `/etc/secrets/serviceAccountKey.json`.

4. **Initialize App**:
   ```bash
   python manage.py collectstatic --noinput
   python manage.py migrate
   ```

## 4. Gunicorn/Daphne & Nginx

If you are already running via a systemd service, update it to point to the new `config.asgi:application` instead of the old one if it changed.

## 5. Data Safety & Backups

> [!WARNING]
> Always backup your database before performing any updates or migrations on a production server.
>
> ```bash
> # Backup your Neon DB (replace values with your .env data)
> pg_dump "postgresql://neondb_owner:password@ep-snowy-hall...aws.neon.tech/neondb" > dita_db_backup_$(date +%F).sql
> ```

**Will you lose data?**
- **Existing Fields**: Data in fields that still exist (like `User.points`, `User.admission_number`) will be preserved.
- **Removed Fields**: Any data in removed fields (like `event.image_url`) will be lost during the migration `0002_remove_event_image_url_...`.
- **Incremental Updates**: If your previous version used a different migration history, Django might find conflicts. Always check `python manage.py showmigrations` first.

## 6. Updating Existing Deployment

If you are updating your current running instance at `/var/www/Dita-app-backend`:

1. **Pull changes**:
   ```bash
   cd /var/www/Dita-app-backend
   git pull origin main
   ```

2. **Update Dependencies**:
   ```bash
   source venv/bin/activate
   pip install -r requirements/base.txt
   ```

3. **Apply Database Changes**:
   ```bash
   python manage.py migrate
   ```

4. **Collect New Static Files**:
   ```bash
   python manage.py collectstatic --noinput
   ```

5. **Restart Service**:
   ```bash
   # adjust the service name to match yours (e.g., dita, gunicorn, etc.)
   sudo systemctl restart dita
   ```

## 7. Summary
Your backend is now updated to the new structure!
Your backend should now be accessible via your domain or VPS IP!
