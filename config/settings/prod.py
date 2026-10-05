"""Configurações de produção. HTTPS obrigatório e proteções do Django ligadas."""

import os

from .base import *  # noqa: F403

DEBUG = False

# WhiteNoise serve os estáticos em produção (logo após o SecurityMiddleware).
MIDDLEWARE = MIDDLEWARE.copy()  # noqa: F405
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# ALLOWED_HOSTS vem do ambiente (obrigatório em produção). No Render, o host externo
# é injetado automaticamente nesta variável.
hostname_render = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if hostname_render:
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, hostname_render]  # noqa: F405

# Segurança (exige HTTPS)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Atrás de proxy/load balancer que termina o TLS (Render).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF_TRUSTED_ORIGINS deve ser informado no ambiente (ex.: https://seudominio.com.br).
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405

# ---------------------------------------------------------------------------
# Arquivos: fotos e documentos em bucket S3 (R2, B2 ou S3), estáticos no WhiteNoise.
# Os arquivos têm CPF e documentos pessoais (LGPD): bucket PRIVADO e URL assinada
# com expiração — nunca públicos.
# ---------------------------------------------------------------------------
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("AWS_STORAGE_BUCKET_NAME"),  # noqa: F405
            "access_key": env("AWS_ACCESS_KEY_ID"),  # noqa: F405
            "secret_key": env("AWS_SECRET_ACCESS_KEY"),  # noqa: F405
            "endpoint_url": env("AWS_S3_ENDPOINT_URL"),  # noqa: F405
            "region_name": env("AWS_S3_REGION_NAME", default="auto"),  # noqa: F405
            "default_acl": "private",
            "querystring_auth": True,
            "querystring_expire": env.int("AWS_QUERYSTRING_EXPIRE", default=3600),  # noqa: F405
            "signature_version": "s3v4",
            "addressing_style": "virtual",
            "file_overwrite": False,
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
