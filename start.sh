#!/usr/bin/env bash
# Comando de inicialização em produção: aplica migrações, coleta estáticos e sobe o gunicorn.
set -e

python manage.py migrate --noinput
# Ignora o input.css (fonte do Tailwind com @import "tailwindcss"): o site usa o output.css já gerado.
python manage.py collectstatic --noinput --ignore=input.css

# Cria a loja e o login do dono, se as variáveis RESP_* estiverem definidas (idempotente).
if [ -n "${RESP_USUARIO:-}" ]; then
    python manage.py criar_responsavel
fi

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-3}" \
    --timeout 120
