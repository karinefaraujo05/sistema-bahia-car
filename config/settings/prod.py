"""Configurações de produção. HTTPS obrigatório e proteções do Django ligadas."""

from .base import *  # noqa: F403

DEBUG = False

# ALLOWED_HOSTS vem do ambiente (obrigatório em produção).

# Segurança (exige HTTPS)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Atrás de proxy/load balancer que termina o TLS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF_TRUSTED_ORIGINS deve ser informado no ambiente (ex.: https://seudominio.com.br).
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405
