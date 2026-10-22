#!/bin/bash
# MonkHQ Vercel Build Script
echo "==> [Vercel Build] Installing dependencies from requirements.txt..."
python3 -m pip install -r requirements.txt

echo "==> [Vercel Build] Running collectstatic..."
export DJANGO_SETTINGS_MODULE=config.settings.production
python3 manage.py collectstatic --noinput --clear

echo "==> [Vercel Build] MonkHQ build complete!"
