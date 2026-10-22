from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# Local memory cache for fast development if Redis is offline
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'socialflow-dev-cache',
    }
}
