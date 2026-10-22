import os
from django.core.wsgi import get_wsgi_application

# Default to production settings for WSGI serverless deployment on Vercel
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings.production'))

application = get_wsgi_application()

# Vercel looks for the WSGI callable named 'app'
app = application
