# Relatório de Análise — Sistema de Gestão Bahia Car

**Data:** 2026-10-18
**Tipo:** auditoria somente‑leitura (nenhum arquivo do sistema foi alterado)
**Convenção:** **✅ Confirmado** = lido direto no código (arquivo:linha). **🔸 Dedução** = inferência a partir do código.

---

## 1. Stack e infra

**✅ Confirmado**
- **Linguagem:** Python 3.13 — `pyproject.toml:5` (`requires-python = ">=3.13,<3.14"`), `Dockerfile:2` (`FROM python:3.13-slim`).
- **Framework:** Django 5.2.x — `pyproject.toml:7` (`"django>=5.2,<5.3"`).
- **Banco:** PostgreSQL via `DATABASE_URL` — `config/settings/base.py:101` (`"default": env.db("DATABASE_URL")`), driver `psycopg[binary]>=3.2` (`pyproject.toml:8`). Em produção é o **Neon (Postgres 18)** — `.github/workflows/backup-banco.yml:25`.
- **ORM:** Django ORM nativo, com reuso de conexão — `base.py:103-104` (`CONN_MAX_AGE = 600`, `CONN_HEALTH_CHECKS = True`).
- **Front:** **server‑rendered (templates Django) + HTMX + PWA** — não é SPA. `base.py:76-90` (TEMPLATES), `base.py:45,70` (django‑htmx), PWA real: `config/urls.py:36-37` + `core/views.py:208-220` servem `manifest.webmanifest` e `sw.js`; arquivos em `templates/pwa/`.
- **Fotos e PDFs:** em **produção vão para bucket S3/R2 PRIVADO com URL assinada** — `config/settings/prod.py:49-67` (`S3Storage`, `default_acl: "private"`, `querystring_auth: True`, expira em 3600s). Campos: `veiculos/models.py:159-161` (imagem + miniatura), `contratos/models.py:142` (documento). **Portanto NÃO ficam no disco do servidor em produção → não há risco de perda em redeploy** para arquivos novos. (Em dev usam disco: `base.py:143-144`.)
- **Render:** plano **free**, runtime Docker — `render.yaml:4-8`. Build via Docker: `uv sync` (`Dockerfile:22`), Tailwind (`Dockerfile:29-34`), `collectstatic` no build (`Dockerfile:40-46`). Start: `Dockerfile:49` → `start.sh` (`migrate` + gunicorn 2 workers/4 threads, `start.sh:5,17-21`). **Sem cron/worker no Render** — `render.yaml` só tem `type: web`.
- **Variáveis de ambiente (só nomes)** — `render.yaml:9-43`: `DJANGO_SETTINGS_MODULE`, `SECRET_KEY`, `TIME_ZONE`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `ADMIN_URL`, `AWS_STORAGE_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_REGION_NAME`, `RESP_USUARIO`, `RESP_SENHA`, `RESP_NOME`, `RESP_EMPRESA`.
- **Backup do banco: existe e é automático**, via GitHub Actions — `.github/workflows/backup-banco.yml:14-15` (`cron "30 6 * * *"`) roda `scripts/backup.sh` (`pg_dump | gzip` → R2, retenção 30 diários/12 mensais, `backup.sh:24,56-57`). Restore: `scripts/restore.sh:14`. Backup manual no app (só superusuário): `core/views.py:239-283`.

**🔸 Dedução:** bucket provavelmente **Cloudflare R2** (`backup-banco.yml:10`, `prod.py:62`); o plano free do Render "dorme" após ~15 min (comentário do projeto, `manter-acordado.yml`). Há um workflow legado `backup.yml` desligado (só `workflow_dispatch`).

---

## 2. Modelo de dados

**✅ Confirmado**
- Todos os models de domínio herdam de `ModeloBase` (abstrato) com `empresa`, `arquivado`, auditoria e histórico — `core/models.py:41-69`. Multiempresa isolada no manager `NaoArquivadosManager` (`core/models.py:27-38`).
- **Models e relações:** `Empresa`, `Usuario(AbstractUser)` (`contas/models.py:5,20`); `Pessoa` (`pessoas/models.py:19`); `Veiculo` → FK `proprietario`→Pessoa (`veiculos/models.py:52,72-79`); `FotoVeiculo` → FK veiculo (`:155-158`); `Consignacao` → FKs veiculo+proprietario (`negocios/models.py:56-68`); `Negocio` (`:98`); `ParteNegocio` (negócio↔pessoa com `papel`, `:159`); `ItemNegocio` (negócio↔veículo, `:179`); `ConfiguracaoLoja` (`contratos/models.py:22`); `Documento` (`:116`); `Contrato` (`:177`). **Sem M2M e sem OneToOne** — os N:N são tabelas intermediárias explícitas.
- **Compra/venda/troca = uma entidade `Negocio` com campo `tipo`** (`negocios/models.py:98-99`), enum `TipoNegocio` = COMPRA/VENDA/TROCA (`:7-11`). **Consignação é entidade separada** `Consignacao`, com `StatusConsignacao` ATIVA/VENDIDA/ENCERRADA (`:50-53`).
- **Troca — carro que entrou e diferença:** **não há campos dedicados.** Direção por property: `entra_na_loja` = `para_pessoa` vazio, `sai_da_loja` = `de_pessoa` vazio (`negocios/models.py:229-237`); cada carro é um `ItemNegocio` com `veiculo` e `valor` (`:183-188,206`). **A diferença em dinheiro NÃO tem campo próprio.**
- **Status do carro — dois eixos:** `StatusVeiculo` = em_estoque/reservado/vendido/devolvido (`veiculos/models.py:45-49,110`) e `Situacao` = proprio/consignado/terceiro (`:39-42,67`). `ItemNegocio` guarda `status_anterior`/`situacao_anterior` para reverter no cancelamento (`negocios/models.py:215-220`).
- **Dados do cliente** (`pessoas/models.py:19-44`): `tipo`, `nome`, `cpf_cnpj` (validado), `telefone`, `email`, `endereco`, `cidade`, `uf`, `cep`, `rg`, `rg_orgao_emissor`, `nacionalidade`, `estado_civil`, `profissao`, `representante_nome/cpf` (PJ), `observacoes`. Unicidade de CPF/CNPJ só entre não‑arquivados (`:50-56`).

**🔸 Dedução**
- **"Um carro vendido pode aparecer no estoque?"** No ORM, **sim**: vender não arquiva e o manager `objetos` não filtra por status (`core/models.py:33-38`). O carro só some do estoque porque a *query da tela* filtra `status=EM_ESTOQUE` (`core/views.py:68-70`, `veiculos/services.py:94-102`). A separação depende do filtro na consulta, não do modelo.
- A mudança de status/situação e a diferença da troca acontecem na camada de **services/views**, não nos models.

---

## 3. Telas (rota · função · responsividade · toques)

**✅ Confirmado** — base responsiva global: `templates/base.html:5` (viewport), sidebar‑drawer mobile (`:42-44`), PWA (`:11,190-197`). Todas as telas herdam layout mobile‑first. A contagem de toques é 🔸 dedução.

| Rota | O que faz | Celular? | Toques |
|---|---|---|---|
| `/` `inicio` | Painel: indicadores, gráfico, atalhos | ✅ | 0 (leitura) |
| `/estoque/` | Estoque com filtros | ✅ (`sm/lg/xl`, `overflow-x-auto`) | 1 |
| `/patio/` | Modo pátio p/ celular | ✅ (`views.py:43`) | 1 |
| `/carros/novo/` · `/carros/<pk>/editar/` | Cadastrar/editar carro+fotos | ✅ | ~10+ |
| `/carros/<pk>/` | Ficha do carro (lucro se admin+vendido) | ✅ | 0 |
| `/pessoas/` · `/nova/` · `/nova-rapida/` · `/<pk>/` | Clientes: lista/cadastro/ficha | ✅ / ⚠️ | 1 a ~10 |
| `/vendas/` | Vendas/trocas do mês + resumo | ✅ (`overflow-x-auto`) | 1 |
| `/negocios/novo/<tipo>/` + passos `quem→carro→pagamento→revisao` | Assistente compra/venda | ✅/⚠️ | ~15‑25 |
| `/negocios/<pk>/troca/...` (carro‑loja, carro‑cliente, valores) | Assistente de troca (5 passos) | ✅/⚠️ | ~15‑25 |
| `/consignacoes/nova/` + `vender/` `repasse/` `devolver/` | Consignação e venda do consignado | ✅ | vários |
| `/contratos/<pk>/editar/` · `/pdf/` · `/docx/` | Editor do contrato, baixar PDF/DOCX | ⚠️ | ~2 |
| `/configuracao/` | Dados da loja (travado, `?editar=1`, admin) | ✅ | 1+campos |
| `/conta/entrar/` `/sair/` | Login/logout | ✅ | 3 |
| `/agenda/` `/buscar/` `/ajuda/` `/consulta/` `/fipe/` `/cnpj/` `/backup/` `/saude/` | Agenda, busca, guia, FIPE/CNPJ, backup, health | ✅/⚠️/N/A | 0‑1 |

**⚠️ Telas sem classes responsivas próprias (herdam só a base):** `agenda`, `busca/pagina`, `pessoas/lista` e `form_rapido`, `negocios/passo_pessoa`, `passo_carro_estoque`, `revisao`, `confirmar_cancelamento`, `contratos/editar`, `faltando`.

**🔸 Dedução:** concluir uma venda do zero ≈ **15‑25 toques**.

---

## 4. Fluxos

**✅ Confirmado (existem):**
- **Cadastrar carro** — `veiculos/views.py:68` `novo`, sobe fotos de `request.FILES.getlist("fotos")` (`:76-77`).
- **Cadastrar cliente** — completo (`pessoas/views.py:26`) e rápido (`:51`); volta ao negócio com a pessoa já selecionada (`:37-41`).
- **Registrar compra** — `inicio.html:66` "Comprei um carro" → `iniciar('compra')` → pessoa (vendedor) → cadastra carro novo → pagamento → revisão → põe em estoque (`services.py:182`).
- **Registrar venda** — "Vendi um carro" → carro do estoque (`_vendaveis()`) → conclui marcando VENDIDO (`services.py:169-172`).
- **Registrar troca** — 5 passos: carro que sai → carro que o cliente deu (`TERCEIRO`) → valores → revisão; vende o que sai e põe em estoque o que entra (`services.py:185-190`).
- **Registrar consignação** — form único (pessoa+carro+termos), deixa o veículo `CONSIGNADO` (`services.py:260,297`); venda do consignado via `iniciar_consignado` (intermediação).
- **Gerar contrato** — no detalhe do negócio (`detalhe.html:147-153`) → `gerar_contrato` escolhe modelo A–E e cria `Contrato` versionado (`geracao.py:124-141`).
- **Editar contrato antes de assinar** — `editar_contrato` (`contratos/views.py:134`): corpo, observações, nº de testemunhas.
- **Achar contrato antigo** — via Lista de Vendas → negócio → seção "Contratos e termos" (`negocios/detalhe.html:143-199`).
- **Mandar pro WhatsApp** — compartilhar documento via `navigator.share`/`window.open` (`detalhe.html:294-300`); `wa.me` direto só no Modo Pátio para anunciar o **carro** (`patio.html:57`).

**🔸 / NÃO EXISTE:**
- **Busca direta por contrato — NÃO EXISTE** (busca global só carros e pessoas, `core/busca.py`).
- **Mandar o CONTRATO direto pro WhatsApp via `wa.me` — NÃO EXISTE** (só compartilhamento genérico do PDF já salvo).
- **Imprimir contrato (`window.print`) — NÃO EXISTE** (imprime‑se baixando o PDF, `editar.html:58`).
- **"Assinado" não é um estado** — `Contrato` não tem campo de assinatura; assinatura é física, sem trava de edição.

---

## 5. Contratos

**✅ Confirmado**
- **Geração em 3 formatos:** (1) **corpo de texto** por template `.txt` (`geracao.py:131`, em `Contrato.corpo`); (2) **PDF via WeasyPrint** (`geracao.py:238,255`), montado de layout HTML "MARA" a partir dos **dados** (`contratos/mara/contrato.html`/`consignacao.html`, `:241-249`) — **não** usa o corpo editável; (3) **DOCX via python‑docx** (`geracao.py:302-312`), este usa o corpo.
- **Um modelo por operação:** `ModeloContrato` A=Compra, B=Venda, C=Troca, D=Consignação, E=Intermediação (`contratos/models.py:169-174`; `escolher_modelo` `geracao.py:38-45`). Arquivos `templates/contratos/modelos/{A..E}.txt`. PDF tem dois layouts.
- **Personalização:** dados da loja em `ConfiguracaoLoja` (singleton por empresa, travado, `?editar=1`, só admin); por contrato: nº de testemunhas (0‑2), observações, e o corpo (que só afeta o Word).
- **Onde ficam guardados:** modelo `Documento` (`contratos/models.py:116,142`), criado ao baixar o PDF (`salvar_pdf_como_documento`, `geracao.py:315`). **Em produção, em bucket S3/R2 privado** (`prod.py:49-67`).

**⚠️ Ponto de confusão (✅ confirmado):** editar o texto do contrato **não muda o PDF** (só o Word); o PDF é sempre remontado dos dados (`editar.html:52`, `geracao.py:241-249`).

---

## 6. Painel / números

**✅ Confirmado** (view `core/views.py:62` `inicio`):
- **Vendas do mês — MOSTRA**, mas o número conta **só VENDA** (`:72-77`), enquanto o **gráfico de 6 meses conta VENDA+TROCA** (`:35-59`) → critérios diferentes na mesma tela.
- **Estoque: quantidade MOSTRA** (`carros_na_loja`, `:67-71`); **valor total do estoque NÃO MOSTRA** (sem `Sum`/`aggregate` no contexto, `:89-99`).
- **Lucro por carro — NÃO MOSTRA no painel.** Existe (`services.py:344,372`) mas só na ficha do veículo (admin + vendido) e na lista de vendas.
- Também mostra `repasses_pendentes` (`:92`), gráfico 6 meses e últimos 5 negócios.

**🔸 Dedução:** "carros parados" não é métrica do painel; aparece como **alerta** na agenda (`dias_na_loja`, `veiculos/models.py:150-152`; card `partials/card.html:31-33`).

---

## 7. Auth e segurança

**✅ Confirmado**
- **Login existe.** Usuário customizado `contas.Usuario(AbstractUser)` com papéis ADMINISTRADOR/VENDEDOR (`contas/models.py:20,30-39,53-55`), multiempresa (`:40-47`), `LOGIN_URL` (`base.py:111`), login/logout padrão do Django (`contas/urls.py:7-12`). Todas as views de negócio usam `@login_required`. Sessão de 90 dias (`base.py:125`).
- **Fotos/PDFs — em PRODUÇÃO não vazam:** bucket privado + URL assinada que expira em 1h (`prod.py:49-67`; comentário LGPD `:46-47`).
- **Em DEV vazam:** `config/urls.py:42-44` serve `/media/` sem `@login_required` (só com `DEBUG=True`, local). Nomes de arquivo com sufixo aleatório (`veiculos/services.py:37`) — obscuridade, não controle de acesso.

**🔸 Dedução:** risco de vazamento de mídia é **só local** (em produção `DEBUG=False` e `/media/` não existe).

---

## 8. Performance (listado, sem corrigir)

1. **N+1 em `foto_capa`** — `veiculos/models.py:146-147`: `.filter(capa=True)` cria queryset novo e ignora o `prefetch_related("fotos")` (`services.py:109`, `busca.py:49`) → ~2 queries extras **por carro** no estoque (`partials/card.html:7-9`) e no pátio.
2. **N+1 na lista de vendas (admin)** — `negocios/views.py:670-684` chama `lucro_bruto(n)` em loop, que abre `list(negocio.itens...)` por negócio (`services.py:358`). `resumo_de_vendas` soma de novo em loop (`services.py:398`).
3. **Zero paginação no projeto** — `grep Paginator` = 0. Estoque, pátio, pessoas e vendas renderizam o queryset inteiro (`veiculos/services.py:94-109`, `pessoas/services.py:16`, `negocios/views.py:662-666`). Só a busca limita a 20 (`busca.py:49`).
4. **Pátio carrega foto em tamanho original** — `patio.html:19` usa `foto.imagem.url` (1600px) em vez da `miniatura`. Resize feito no upload (`services.py:17-31`); estoque usa miniatura (`partials/card.html:9`).
5. **Índices faltando** — sem `db_index`/`Meta.indexes` nos campos mais filtrados: `Veiculo.status`/`situacao`, `Negocio.status`/`tipo`/`data` (`veiculos/models.py:110,67`; filtrados em `core/views.py:48-77`, `negocios/views.py:658-660`).
6. **Front sem polling** (✅ ok) — HTMX só com debounce de busca (`base.html:57-58`), sem refresh periódico.

**🔸 Dedução:** volume de uma loja pequena é baixo → impacto prático hoje é pequeno, mas são os pontos que escalam mal com crescimento.

---

## 9. Testes

**✅ Confirmado:** pytest + pytest‑django (`pyproject.toml:24-25,50-53`, roda em `settings.dev`, `--reuse-db`). **6 arquivos (um por app), ~1700 linhas, ~103 funções `test_`**:
- `negocios/tests.py` (~31) — o mais forte: compra/venda/troca/consignação, bloqueios, cancelamento revertendo estado, fluxos end‑to‑end, lucro e permissões.
- `contratos/tests.py` (~24) — geração de contrato/termo, PDF/DOCX, limite de upload, bloqueio de vendedor na config.
- `veiculos/tests.py` (~22) — validadores, unicidade, capa, redimensionamento, estoque esconde terceiro, exige login.
- `pessoas/tests.py` (~16), `core/tests.py` (~16, inclui **isolamento por empresa**), `contas/tests.py` (5, login/papéis).

**🔸 Dedução — lacunas:** sem `assertNumQueries` (os N+1 do §8 não são testados) e sem teste do acesso a `/media/` sem login (§7).

---

## 10. Tamanho

**✅ Confirmado**
- **Código Python por app** (via `wc -l`, sem migrations): config 309 · core 1.207 · contas 129 · pessoas 603 · veiculos 897 · **negocios 2.314** · **contratos 1.611** → **~7.070 linhas** de app‑code (+1.322 em migrations).
- **Templates:** 48 arquivos `.html` / 3.764 linhas.
- **Dependências:** 13 de runtime + 3 de dev (`pyproject.toml:6-27`); `uv.lock` com 49 pacotes (~33 transitivas).
- **Front:** sem bundler JS. `htmx.min.js` ~51KB; `mascaras.js` ~5,7KB; `guia.js` ~5,7KB. Único "build" é o CSS do Tailwind → `output.css` ~40KB (servido comprimido pelo WhiteNoise).

---

## Síntese — os 5 pontos que eu levaria primeiro

1. **Divergência contrato PDF × texto editável** (§4/§5): editar o texto não muda o PDF — confunde o usuário.
2. **Sem busca de contratos/negócios** (§4): achar um contrato antigo exige navegar por mês.
3. **Vendas do mês (número) ≠ gráfico** e **painel não mostra valor de estoque nem lucro** (§6).
4. **N+1 em `foto_capa` + zero paginação + pátio com foto full‑size** (§8).
5. **Sem índices** nos campos mais filtrados (§8).

**Ressalva de método:** relatório baseado na leitura do código atual por 5 analistas, com reconciliação entre escopos (ex.: storage em §5 confirmado via §1). Itens 🔸 são inferências, não fatos verificados. Nenhum arquivo do sistema foi modificado.
