"""
Configurações comuns a todos os ambientes.

Tudo que varia entre máquina/produção vem de variáveis de ambiente (arquivo .env).
Nenhum segredo fica no código. Veja .env.example.
"""

from pathlib import Path

import environ

# config/settings/base.py -> config/settings -> config -> raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

# Lê o arquivo .env da raiz, se existir (em produção as variáveis vêm do ambiente).
env_file = BASE_DIR / ".env"
if env_file.exists():
    env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# URL do admin propositalmente não óbvia (só para o superusuário).
ADMIN_URL = env("ADMIN_URL", default="painel-interno/")


# Aplicativos
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "django_htmx",
    "simple_history",
]

LOCAL_APPS = [
    "core",
    "contas",
    "veiculos",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Banco de dados (PostgreSQL via DATABASE_URL)
DATABASES = {
    "default": env.db("DATABASE_URL"),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = False


# Usuário customizado (papéis administrador/vendedor)
AUTH_USER_MODEL = "contas.Usuario"

LOGIN_URL = "contas:entrar"
LOGIN_REDIRECT_URL = "inicio"
LOGOUT_REDIRECT_URL = "contas:entrar"


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Sessão longa no celular: o dono não precisa logar todo dia (90 dias).
SESSION_COOKIE_AGE = 60 * 60 * 24 * 90
SESSION_SAVE_EVERY_REQUEST = True


# Internacionalização (Brasil)
LANGUAGE_CODE = "pt-br"
TIME_ZONE = env("TIME_ZONE", default="America/Bahia")
USE_I18N = True
USE_TZ = True


# Arquivos estáticos e de mídia
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Limite padrão de upload de documento (20 MB), configurável.
TAMANHO_MAXIMO_UPLOAD_MB = env.int("TAMANHO_MAXIMO_UPLOAD_MB", default=20)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
