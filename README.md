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

## Deploy em produção (gratuito)

Stack: **Render** (app, Docker, tier grátis) + **Neon** (banco Postgres) + **bucket S3**
(Cloudflare R2 ou Backblaze B2) para fotos e documentos + **GitHub Actions** (backup diário).

> O app roda em container (`Dockerfile`), com `gunicorn` e `WhiteNoise` para os estáticos.
> As fotos/documentos vão para um bucket **privado**, servidos por **URL assinada com expiração**.

### 1. Banco (Neon, produção)
Crie um **projeto separado** no Neon só para produção (dados reais longe dos de teste) e copie a
`DATABASE_URL`. O Neon aqui é **Postgres 18** — o cliente de backup precisa ser o 18 (já tratado
no workflow e nos scripts).

### 2. Bucket de arquivos (R2 ou B2)
Crie um bucket **privado** e gere um par de chaves (Access Key / Secret). Anote o **endpoint S3**:
- Cloudflare R2: `https://<conta>.r2.cloudflarestorage.com` (região `auto`)
- Backblaze B2: `https://s3.<regiao>.backblazeb2.com`

### 3. App no Render (Blueprint)
1. Suba o código para um repositório no **GitHub**.
2. No Render: **New > Blueprint** e aponte para o repositório — ele lê o `render.yaml` e cria o
   Web Service (plano grátis) sozinho.
3. Em **Environment**, preencha as variáveis marcadas como `sync: false`:
   `DATABASE_URL`, `ALLOWED_HOSTS` (o domínio `.onrender.com`), `CSRF_TRUSTED_ORIGINS`
   (`https://seu-app.onrender.com`), `ADMIN_URL`, e as do bucket: `AWS_STORAGE_BUCKET_NAME`,
   `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_REGION_NAME`.
4. No primeiro deploy, o `start.sh` roda as migrações e coleta os estáticos; depois crie seu
   usuário com o shell do Render: `python manage.py createsuperuser`.

> O tier grátis do Render **hiberna após ~15 min** sem acesso; a primeira visita acorda em
> alguns segundos. Para um uso de loja pequena, costuma ser suficiente.

### 4. Backup diário (GitHub Actions)
O workflow `.github/workflows/backup.yml` roda todo dia e envia um `pg_dump` compactado para o
bucket de backup (mantém 30 diários e 12 mensais). Crie um **bucket de backup separado** e
configure os **Secrets** no GitHub: `DATABASE_URL`, `BACKUP_BUCKET`, `AWS_S3_ENDPOINT_URL`,
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.

### 5. Restauração (testar sempre!)
```bash
# restaure sempre primeiro num banco DESCARTÁVEL para conferir:
make restaurar ARQ=bahiacar-AAAAMMDD-HHMMSS.sql.gz DESTINO="postgres://.../banco_teste"
```
O ciclo backup → restauração já foi testado localmente contra um Postgres 18 descartável.

### Exportação manual
O administrador pode baixar uma planilha Excel (Veículos, Pessoas, Negócios) em **Vendas >
Exportar Excel**, para ter uma cópia própria dos dados.
