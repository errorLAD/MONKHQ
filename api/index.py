"""
Vercel Serverless Function entrypoint for MonkHQ.
This allows Vercel to route incoming requests directly to Django's WSGI application.
"""
from config.wsgi import app
