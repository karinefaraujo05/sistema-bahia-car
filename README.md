# Sistema Bahia Car

Sistema de gestão para uma loja de veículos (seminovos e usados): estoque, pessoas,
negócios (compra, venda, troca), consignação, contratos em PDF e busca.

As regras do projeto estão em [`ESPECIFICACAO.md`](ESPECIFICACAO.md) (fonte de verdade) e os
modelos de contrato em [`CONTRATOS.md`](CONTRATOS.md).

## Stack

- Python 3.13 + Django 5.2 LTS
- PostgreSQL (via Docker no desenvolvimento)
- HTMX + templates do Django (sem SPA)
- Tailwind CSS via CLI standalone (sem Node)
- Ambiente gerenciado com [uv](https://docs.astral.sh/uv/)
- Testes com pytest; lint e formatação com ruff

## Rodar localmente

Pré-requisitos: [uv](https://docs.astral.sh/uv/getting-started/installation/) e Docker.

```bash
# 1. Instalar as dependências
make instalar            # (uv sync)

# 2. Copiar as variáveis de ambiente e ajustar
cp .env.example .env
# gere uma SECRET_KEY nova:
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# e cole no .env a DATABASE_URL do seu banco (ver "Banco de dados" abaixo).

# 3. Aplicar as migrações
make migrar

# 4. Criar o seu usuário administrador (superusuário)
make admin

# 5. Gerar o CSS (ou use `make css-watch` enquanto desenvolve)
make css

# 6. Rodar o servidor
make dev
```

Acesse em `http://localhost:8000`.

### Banco de dados

O desenvolvimento usa um **PostgreSQL gerenciado na nuvem (Neon)**. Basta ter a `DATABASE_URL`
do Neon no `.env` — não precisa de Docker.

Se preferir rodar o banco localmente com Docker, há um `docker-compose.yml`: rode `make up`
(sobe o Postgres na porta 5433) e use a `DATABASE_URL` local comentada no `.env.example`.

### Testar no celular

Com o servidor rodando (`make dev` já escuta em `0.0.0.0`), descubra o IP da sua máquina na
rede local (ex.: `192.168.0.10`), acrescente esse IP em `ALLOWED_HOSTS` no `.env`, e acesse
`http://192.168.0.10:8000` pelo celular na mesma rede.

## Testes

```bash
make teste               # uv run pytest
```

## Qualidade de código

```bash
make lint                # uv run ruff check .
make formatar            # uv run ruff format .
```

## Comandos

Rode `make` (sem argumentos) para ver todos os comandos disponíveis.

## Estrutura

```
config/          projeto Django (settings por ambiente: base, dev, prod)
core/            ModeloBase (arquivamento, histórico) e tela inicial
contas/          usuário customizado (papéis admin/vendedor) e login
templates/       templates globais (base, login, início, partials/)
static/          CSS (Tailwind) e JS (htmx)
bin/             binário do Tailwind (não versionado)
```

## Painel interno (Django admin)

Fica em uma URL não óbvia definida por `ADMIN_URL` no `.env` (padrão `painel-interno/`).
É só para o superusuário — não é a interface do usuário final.

## Deploy, backup e restauração

Serão documentados na Fase 8 (produção): Dockerfile, gunicorn, storage S3, backup diário com
`pg_dump` e restauração testada.
