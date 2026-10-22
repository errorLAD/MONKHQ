import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# In serverless environments like Vercel, the project filesystem is read-only except /tmp.
is_vercel = os.environ.get('VERCEL') == '1' or 'VERCEL_ENV' in os.environ
default_db_url = 'sqlite:////tmp/db.sqlite3' if is_vercel else f'sqlite:///{BASE_DIR / "db.sqlite3"}'

env = environ.Env(
    DEBUG=(bool, True),
    SECRET_KEY=(str, 'django-insecure-monkhq-production-super-secret-key-2026!'),
    ALLOWED_HOSTS=(list, ['*', '.vercel.app', 'localhost', '127.0.0.1']),
    DATABASE_URL=(str, default_db_url),
    REDIS_URL=(str, 'redis://localhost:6379/0'),
)

environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY', default='django-insecure-monkhq-production-super-secret-key-2026!')
DEBUG = env('DEBUG', default=True)
ALLOWED_HOSTS = env('ALLOWED_HOSTS', default=['*', '.vercel.app', 'localhost', '127.0.0.1'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'django_filters',
    'corsheaders',

    # SocialFlow AI apps
    'accounts',
    'workspaces',
    'creator',
    'brands',
    'automations',
    'engagement',
    'ai_engine',
    'promotions',
    'linkhub',
    'products',
    'orders',
    'campaigns',
    'analytics',
    'social',
    'developer',
    'billing',
    'audit',
    'notifications',
    'admin_platform',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Custom Security & Isolation Middleware
    'security.middleware.SecurityHeadersMiddleware',
    'accounts.middleware.RoleAuthorizationMiddleware',
    'workspaces.middleware.WorkspaceMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.user_role_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
# ASGI_APPLICATION = 'config.asgi.application' (Keep commented so Vercel defaults strictly to WSGI)

DATABASES = {
    'default': env.db('DATABASE_URL')
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
WHITENOISE_USE_FINDERS = True
WHITENOISE_MANIFEST_STRICT = False

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Session and Cookie Security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://monkhq.in',
    'https://www.monkhq.in',
    'https://*.vercel.app',
])
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 86400 * 7 # 7 days

# Celery Configuration
CELERY_BROKER_URL = env('REDIS_URL')
CELERY_RESULT_BACKEND = env('REDIS_URL')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}

# Meta / Instagram API (Instagram Login for Tech Providers)
META_APP_ID = env('META_APP_ID', default='')
META_APP_SECRET = env('META_APP_SECRET', default='')
INSTAGRAM_REDIRECT_URI = env('INSTAGRAM_REDIRECT_URI', default='http://localhost:8000/social/callback/')
META_WEBHOOK_VERIFY_TOKEN = env('META_WEBHOOK_VERIFY_TOKEN', default='')
INSTAGRAM_SCOPES = env('INSTAGRAM_SCOPES', default='instagram_business_basic,instagram_business_manage_comments')

# Google Gemini AI Integration (MonkHQ AI Engine)
GEMINI_API_KEY = env('GEMINI_API_KEY', default=env('GOOGLE_API_KEY', default=''))
GEMINI_MODEL = env('GEMINI_MODEL', default='gemini-3.8-flash')
GEMINI_FALLBACK_MODELS = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest', 'gemini-1.5-flash-latest']

# Token Cost Estimates (in USD per 1,000,000 tokens for Gemini Flash)
GEMINI_COST_PER_MILLION_INPUT = float(env('GEMINI_COST_PER_MILLION_INPUT', default=0.075))
GEMINI_COST_PER_MILLION_OUTPUT = float(env('GEMINI_COST_PER_MILLION_OUTPUT', default=0.300))

# Usage Safeguards & Abuse Protection (per user)
GEMINI_MAX_REQUESTS_PER_USER_HOUR = int(env('GEMINI_MAX_REQUESTS_PER_USER_HOUR', default=30))
GEMINI_MAX_REQUESTS_PER_USER_DAY = int(env('GEMINI_MAX_REQUESTS_PER_USER_DAY', default=120))
GEMINI_MAX_DAILY_TOKENS_PER_USER = int(env('GEMINI_MAX_DAILY_TOKENS_PER_USER', default=100000))

# Cache TTLs (in seconds)
GEMINI_CACHE_TTL_RELEVANCE = int(env('GEMINI_CACHE_TTL_RELEVANCE', default=43200)) # 12 hours
GEMINI_CACHE_TTL_IDEAS = int(env('GEMINI_CACHE_TTL_IDEAS', default=7200))          # 2 hours
GEMINI_CACHE_TTL_DEBOUNCE = int(env('GEMINI_CACHE_TTL_DEBOUNCE', default=8))        # 8s anti-double-click
