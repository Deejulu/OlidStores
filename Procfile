web: bash -lc "mkdir -p $MEDIA_ROOT && python manage.py migrate --noinput && gunicorn e_stores.wsgi:application --bind 0.0.0.0:$PORT"web: gunicorn e_stores.wsgi:application --timeout 120
