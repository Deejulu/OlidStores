# Production Deployment Guide for Olid Stores

This guide covers deploying Olid Stores to production with maximum performance.

## Pre-Deployment Checklist

### 1. Environment Variables Setup
Create these on your hosting platform (Render, Heroku, Railway, etc.):

```bash
# Django Settings
DJANGO_SECRET_KEY=your-super-secret-key-here-min-50-chars
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (PostgreSQL recommended)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Redis Cache (highly recommended for production)
REDIS_URL=redis://your-redis-host:6379/1

# Static/Media Storage
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_STORAGE_BUCKET=media

# Email (SendGrid recommended)
EMAIL_BACKEND=sendgrid
SENDGRID_API_KEY=SG.your-sendgrid-api-key
SENDGRID_SENDER_EMAIL=noreply@yourdomain.com
SENDGRID_SENDER_NAME=Your Store Name
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Payments
PAYSTACK_PUBLIC_KEY=pk_live_your-public-key
PAYSTACK_SECRET_KEY=sk_live_your-secret-key

# Performance Settings
CACHE_TTL=300  # 5 minutes
```

### 2. Database Migration
```bash
# Apply all migrations (including performance indexes)
python manage.py migrate

# Verify indexes were created
python manage.py dbshell
\di  # PostgreSQL: list all indexes
```

### 3. Static Files Collection
```bash
# Collect and compress static files
python manage.py collectstatic --no-input

# This will:
# - Copy all static files to STATIC_ROOT
# - Compress CSS/JS with WhiteNoise
# - Add cache-busting hashes to filenames
```

## Hosting Platform Setup

### Option 1: Render.com (Recommended)

#### render.yaml
```yaml
services:
  - type: web
    name: estore-web
    env: python
    buildCommand: pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --no-input
    startCommand: gunicorn e_stores.wsgi:application --workers 4 --threads 2 --timeout 30
    envVars:
      - key: PYTHON_VERSION
        value: 3.14.0
      - key: DJANGO_SECRET_KEY
        sync: false
      - key: DJANGO_DEBUG
        value: False
      - key: REDIS_URL
        fromService:
          type: redis
          name: estore-redis
          property: connectionString
      - key: DATABASE_URL
        fromDatabase:
          name: estore-db
          property: connectionString

  - type: redis
    name: estore-redis
    plan: starter
    maxmemoryPolicy: allkeys-lru

databases:
  - name: estore-db
    databaseName: estore
    user: estore
```

### Option 2: Heroku

#### Procfile
```
web: gunicorn e_stores.wsgi:application --workers 4 --threads 2 --worker-class gthread --max-requests 1000 --max-requests-jitter 50 --timeout 30 --keep-alive 5
```

#### Add-ons
```bash
# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Add Redis
heroku addons:create heroku-redis:mini

# Set environment variables
heroku config:set DJANGO_SECRET_KEY=your-secret-key
heroku config:set DJANGO_DEBUG=False
heroku config:set DJANGO_ALLOWED_HOSTS=yourapp.herokuapp.com
```

### Option 3: Railway.app

#### railway.toml
```toml
[build]
builder = "nixpacks"
buildCommand = "pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --no-input"

[deploy]
startCommand = "gunicorn e_stores.wsgi:application --workers 4 --threads 2"
healthcheckPath = "/"
healthcheckTimeout = 100
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 10
```

## Gunicorn Configuration

### Calculate Workers
```python
# Formula: (2 × CPU cores) + 1
# Examples:
# 1 CPU core  = 3 workers
# 2 CPU cores = 5 workers
# 4 CPU cores = 9 workers
```

### Production gunicorn.conf.py
```python
import multiprocessing

# Server Socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker Processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'gthread'
worker_connections = 1000
threads = 2
max_requests = 1000
max_requests_jitter = 50
timeout = 30
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = '-'  # stdout
errorlog = '-'   # stderr
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process Naming
proc_name = 'estore'

# Server Mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (if not using a reverse proxy)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'
```

## Performance Verification

### 1. Test Database Indexes
```bash
python manage.py shell

>>> from django.db import connection
>>> cursor = connection.cursor()
>>> cursor.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename LIKE 'products_%' OR tablename LIKE 'orders_%' OR tablename LIKE 'users_%';")
>>> for row in cursor.fetchall():
...     print(row)
```

### 2. Test Cache
```bash
python manage.py shell

>>> from django.core.cache import cache
>>> cache.set('test_key', 'test_value', 60)
>>> print(cache.get('test_key'))  # Should print: test_value
>>> cache.delete('test_key')
```

### 3. Load Testing
```bash
# Install Apache Bench
sudo apt-get install apache2-utils  # Linux
brew install httpie  # Mac

# Test homepage speed
ab -n 1000 -c 10 https://yourdomain.com/

# Results to look for:
# - Requests per second: > 100 (good), > 500 (excellent)
# - Time per request: < 100ms (good), < 50ms (excellent)
# - Failed requests: 0
```

## Post-Deployment Monitoring

### 1. Enable Application Monitoring
```python
# settings.py (add this for production)
if not DEBUG:
    # Add Sentry for error tracking
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=True,
    )
```

### 2. Database Connection Pooling
Already configured via `conn_max_age=600` in settings.py

### 3. Redis Monitoring
```bash
# Connect to Redis CLI
redis-cli

# Check stats
INFO stats
INFO memory

# Check cache hit rate
INFO stats | grep keyspace
```

## Performance Benchmarks

### Expected Metrics (Production with Redis):
```
Homepage:
- Load time: 400-800ms
- Time to first byte: 100-200ms
- Largest contentful paint: 600-1200ms
- Total page size: 600KB-1MB (compressed)

Product List:
- Load time: 300-600ms
- Database queries: 3-5 (with proper select_related)
- Cache hit rate: 80-95%

Checkout Process:
- Page load: 200-400ms
- Payment redirect: < 2s
```

## Troubleshooting

### Issue: Slow Page Loads
1. Check database query count with Django Debug Toolbar (dev only)
2. Verify Redis is connected: `redis-cli ping` should return `PONG`
3. Check Gunicorn worker count matches CPU cores
4. Review logs for slow queries

### Issue: High Memory Usage
1. Reduce Gunicorn workers
2. Add `--max-requests 1000` to restart workers periodically
3. Enable Redis maxmemory-policy: `allkeys-lru`

### Issue: Static Files Not Loading
1. Run `python manage.py collectstatic --no-input`
2. Verify `STATIC_ROOT` and `STATIC_URL` settings
3. Check WhiteNoise is in MIDDLEWARE (before CommonMiddleware)
4. Verify files exist in STATIC_ROOT directory

### Issue: Database Timeouts
1. Increase `DATABASE_CONNECT_TIMEOUT` env var
2. Check database connection limits
3. Verify `conn_max_age=600` is set
4. Consider upgrading database plan

## Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` (50+ random characters)
- [ ] `SECURE_SSL_REDIRECT=True` (enabled automatically when DEBUG=False)
- [ ] `SECURE_HSTS_SECONDS=31536000` (1 year)
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] `CSRF_COOKIE_SECURE=True`
- [ ] Database backups scheduled
- [ ] Environment variables secured (not in code)
- [ ] `ALLOWED_HOSTS` restricted to your domain(s)
- [ ] Admin URL changed from `/admin/` (optional)
- [ ] Rate limiting enabled (django-axes configured)
- [ ] File upload limits set

## Maintenance Tasks

### Weekly
```bash
# Clear expired sessions
python manage.py clearsessions

# Clear expired OTP codes
python manage.py shell
>>> from users.models import OTPVerification
>>> from django.utils import timezone
>>> OTPVerification.objects.filter(expires_at__lt=timezone.now()).delete()
```

### Monthly
```bash
# Analyze database performance
python manage.py dbshell
ANALYZE;

# Check table sizes
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### As Needed
```bash
# Rebuild search indexes (if using full-text search)
python manage.py update_index

# Clear all cache
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

## Scaling Strategies

### Phase 1: Single Server (0-10k users/month)
- 1 web dyno/service
- Shared PostgreSQL
- Shared Redis
- **Cost**: $10-25/month

### Phase 2: Optimized Single Server (10k-50k users/month)
- Upgrade to 2-4 workers
- Dedicated PostgreSQL (1GB+ RAM)
- Dedicated Redis (256MB)
- CDN for static files
- **Cost**: $50-100/month

### Phase 3: Multi-Server (50k+ users/month)
- Load balancer + 2-3 web servers
- Database read replicas
- Redis cluster
- CDN + object storage
- **Cost**: $200-500/month

## Support Resources

- Django Performance Tips: https://docs.djangoproject.com/en/stable/topics/performance/
- Render Docs: https://render.com/docs
- Heroku Docs: https://devcenter.heroku.com/categories/python-support
- Redis Best Practices: https://redis.io/docs/management/optimization/

---

**Last Updated**: May 2026
**Questions?** Review PERFORMANCE_OPTIMIZATION.md for detailed optimization info
