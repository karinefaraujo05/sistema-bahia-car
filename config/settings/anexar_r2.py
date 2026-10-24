"""
Settings TEMPORÁRIA só pra anexar arquivos: banco e demais configs iguais ao dev
(DEBUG, banco Neon do .env), mas o ARMAZENAMENTO aponta pro R2 de produção.

Use só para rodar `anexar_contratos` / `anexar_documentos` localmente subindo os
arquivos pro bucket real. Não é pra servir o site.

    python manage.py anexar_contratos --settings=config.settings.anexar_r2
"""

from .dev import *  # noqa: F403  (DEBUG, ALLOWED_HOSTS, banco do .env)

# Armazenamento no R2 (idêntico ao prod.py).
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
            "addressing_style": env("AWS_S3_ADDRESSING_STYLE", default="virtual"),  # noqa: F405
            "file_overwrite": False,
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
