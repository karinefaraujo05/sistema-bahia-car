"""Configurações de desenvolvimento (máquina local)."""

from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# No celular, acessar pelo IP da máquina na rede local (ex.: 192.168.x.x).
# Acrescente o IP em ALLOWED_HOSTS no .env quando for testar no telefone.

# E-mails caem no console durante o desenvolvimento.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
