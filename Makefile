.DEFAULT_GOAL := help
.PHONY: help instalar up down dev migrar migracoes admin teste lint formatar css css-watch

help: ## Mostra os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-14s %s\n", $$1, $$2}'

instalar: ## Instala as dependências (uv)
	uv sync

up: ## Sobe o banco de dados (Postgres via Docker)
	docker compose up -d db

down: ## Para o banco de dados
	docker compose down

dev: ## Roda o servidor (acessível no celular pela rede local)
	uv run python manage.py runserver 0.0.0.0:8000

migrar: ## Aplica as migrações no banco
	uv run python manage.py migrate

migracoes: ## Cria novas migrações a partir dos modelos
	uv run python manage.py makemigrations

admin: ## Cria o superusuário (acesso ao painel interno)
	uv run python manage.py createsuperuser

teste: ## Roda os testes
	uv run pytest

lint: ## Verifica o código (ruff)
	uv run ruff check .

formatar: ## Formata o código (ruff)
	uv run ruff format .

css: ## Gera o CSS do Tailwind uma vez
	./bin/tailwindcss -i static/css/input.css -o static/css/output.css --minify

css-watch: ## Gera o CSS e fica observando mudanças
	./bin/tailwindcss -i static/css/input.css -o static/css/output.css --watch
