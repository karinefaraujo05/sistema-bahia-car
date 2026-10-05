# Imagem de produção do Sistema Bahia Car.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

# Bibliotecas de sistema que o WeasyPrint precisa (pango/cairo) + fontes + curl.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 libffi8 libjpeg62-turbo \
    fonts-dejavu-core shared-mime-info ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Gerenciador uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Dependências primeiro (melhor cache).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"

COPY . .

# Gera o CSS do Tailwind (binário conforme a arquitetura da imagem).
ARG TARGETARCH
RUN ARCH="$([ "$TARGETARCH" = "arm64" ] && echo arm64 || echo x64)" \
    && curl -sL -o /usr/local/bin/tailwindcss \
       "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-${ARCH}" \
    && chmod +x /usr/local/bin/tailwindcss \
    && /usr/local/bin/tailwindcss -i static/css/input.css -o static/css/output.css --minify \
    && chmod +x start.sh

EXPOSE 8000
CMD ["./start.sh"]
