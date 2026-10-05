#!/usr/bin/env bash
# Comando de inicialização em produção: aplica migrações, coleta estáticos e sobe o gunicorn.
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-3}" \
    --timeout 120
