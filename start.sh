#!/usr/bin/env bash
# Comando de inicialização em produção: aplica migrações, coleta estáticos e sobe o gunicorn.
set -e

python manage.py migrate --noinput
# collectstatic NÃO roda aqui: já é feito no build (Dockerfile), para o boot ser
# rápido quando o Render acorda. Os estáticos já estão dentro da imagem.

# Cria a loja e o login do dono, se as variáveis RESP_* estiverem definidas (idempotente).
if [ -n "${RESP_USUARIO:-}" ]; then
    python manage.py criar_responsavel
fi

# Plano grátis do Render tem pouca memória (512MB) e CPU fraca.
# 2 processos + threads: gasta menos memória (evita travar) e ainda atende
# vários cliques ao mesmo tempo (as threads ajudam na espera do banco/fotos).
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --threads "${WEB_THREADS:-4}" \
    --timeout 120
