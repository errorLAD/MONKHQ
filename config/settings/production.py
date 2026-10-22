from .base import *

# In production, DEBUG must be False by default for security
DEBUG = env.bool('DEBUG', default=False)
# Prevent development .env file from inadvertently enabling DEBUG in production mode
if os.environ.get('DJANGO_SETTINGS_MODULE') == 'config.settings.production':
    DEBUG = env.bool('PROD_DEBUG', default=False)

# Support Vercel deployment domains, custom domains, and local testing
prod_hosts = env.list('ALLOWED_HOSTS', default=['monkhq.in', 'www.monkhq.in', 'socialflow.ai', 'www.socialflow.ai'])
ALLOWED_HOSTS = list(dict.fromkeys(prod_hosts + ['.vercel.app', 'localhost', '127.0.0.1', 'testserver']))

prod_csrf = env.list('CSRF_TRUSTED_ORIGINS', default=['https://monkhq.in', 'https://www.monkhq.in'])
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(prod_csrf + ['https://*.vercel.app', 'http://localhost:8000', 'http://127.0.0.1:8000']))

# Proxy & Security Headers
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Vercel handles HTTPS termination at its edge network.
# Keep SECURE_SSL_REDIRECT configurable (default False to prevent proxy redirect loops).
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=True)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=True)

SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Cache: Redis if configured and remote; fallback to LocMemCache in serverless if Redis is local/unavailable
redis_url = env('REDIS_URL', default='')
if redis_url and not redis_url.startswith('redis://localhost'):
    CACHES = {
        'default': env.cache('REDIS_URL')
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'monkhq-prod-cache',
        }
    }
