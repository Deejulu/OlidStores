# E-Stores

This is a Django e-commerce project prepared for deployment on Render using PostgreSQL.

## What’s included

- Django 6.0 project structure
- `e_stores/settings.py` configured for environment variables
- `requirements.txt` for dependency installation
- `.gitignore` to keep local files out of Git
- `runtime.txt` for Python version on host
- `Procfile` for Gunicorn startup

## Recommended deployment flow

### 1. Use Supabase for Postgres
- Create a Supabase project
- Copy the Postgres connection string
- Add `DATABASE_URL` in Render environment variables

### 2. Host the app on Render
- Create a new Web Service from this GitHub repo
- Use `requirements.txt` for dependencies
- Set the build command to `pip install -r requirements.txt`
- Use the start command: `gunicorn e_stores.wsgi:application`

### 3. Environment variables
Set these in Render:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG` = `False`
- `DJANGO_ALLOWED_HOSTS` = `yourapp.onrender.com`
- `DATABASE_URL` = Supabase connection string
- `CONTACT_NOTIFY_EMAIL` (optional)
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` (if used)

### 4. Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Notes

- Static files are configured for Whitenoise in `e_stores/settings.py`
- Use `collectstatic` before or during deployment
- Keep secrets out of Git by using environment variables
