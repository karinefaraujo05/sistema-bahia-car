# LEVANTAMENTO — Sistema Bahia Car

Levantamento do que o sistema **faz hoje**, feito lendo o código (sem propor melhorias).

**Convenção:** `FATO` = lido diretamente no código (com arquivo:linha). `DEDUÇÃO` = inferência minha a partir do código. `NÃO IDENTIFICADO` = não deu para confirmar pela leitura.

---

## 1. STACK E ESTRUTURA

### 1.1 Linguagens, frameworks e infra (FATO)

| Item | Valor | Fonte |
|---|---|---|
| Linguagem | Python 3.13 (`>=3.13,<3.14`) | `pyproject.toml:5` |
| Framework web | Django 5.2 (`>=5.2,<5.3`) | `pyproject.toml:8` |
| Banco de dados | PostgreSQL (driver `psycopg[binary]`) | `pyproject.toml:9`, `config/settings/base.py:100-105` |
| ORM | Django ORM (sem ORM externo) | — |
| Gerenciador de pacotes | `uv` (lockfile `uv.lock`) | `Dockerfile:16,22` |
| Servidor de app | Gunicorn | `pyproject.toml:17`, `start.sh` |
| Estáticos | WhiteNoise (comprimido+manifest) | `pyproject.toml:18`, `config/settings/prod.py:11,68-70` |
| Arquivos de mídia (fotos/docs) | Bucket S3 compatível (R2/B2/S3) via `django-storages[s3]`, **privado**, URL assinada 1h | `config/settings/prod.py:49-67` |
| CSS | Tailwind (binário standalone, gerado no build) | `Dockerfile:27-34`, `static/css/input.css` |
| Interatividade | django-htmx + JS vanilla (sem SPA) | `pyproject.toml:10`, `base.py:70` |
| Histórico/auditoria | django-simple-history (todo modelo) | `pyproject.toml:11`, `core/models.py:22,72` |
| PDF | WeasyPrint | `pyproject.toml:15`, `contratos/geracao.py:238` |
| Word (.docx) | python-docx | `pyproject.toml:16`, `contratos/geracao.py:304` |
| Excel (.xlsx) | openpyxl | `pyproject.toml:16`, `negocios/views.py:749` |
| Valor por extenso | num2words | `pyproject.toml:14` |
| Imagens | Pillow | `pyproject.toml:13` |
| Config por ambiente | django-environ (`.env`) | `pyproject.toml:12`, `base.py:15-27` |

### 1.2 Deploy / hospedagem (FATO)

- **Hoje:** Render (Docker), plano `starter`, via `render.yaml`. Banco = **Neon** (Postgres externo). Fuso `America/Bahia`. (`render.yaml`, `Dockerfile`)
- `Dockerfile`: imagem `python:3.13-slim`, instala libs de sistema do WeasyPrint (pango/cairo), gera CSS do Tailwind e roda `collectstatic` **no build**. Boot via `start.sh`.
- `docker-compose.yml` existe para validar a imagem de produção localmente (inclui, pela leitura, MinIO como S3 local — `prod.py:62`).
- Documentação de migração para Hetzner/Dokploy/R2 existe nos `.md` da raiz (`MIGRAR-BANCO.md`, `PUBLICAR.md`) e na memória do projeto — **ainda não aplicada** (DEDUÇÃO: `render.yaml` ainda é a config ativa).
- Endpoint `/saude/` faz `SELECT 1` para "acordar" o Neon (que dorme). (`core/views.py:36-45`)

### 1.3 Árvore de pastas (FATO)

```
config/        # Projeto Django: settings (base/dev/prod/anexar_r2), urls raiz, wsgi/asgi
core/          # Base do sistema: ModeloBase, multi-tenancy, busca global, agenda, FIPE, painel inicial
contas/        # Usuário customizado (admin/vendedor) e Empresa (multi-loja)
pessoas/       # Clientes/vendedores/donos (Pessoa), validação CPF/CNPJ
veiculos/      # Veículo e FotoVeiculo, cadastro, estoque, pátio, validação placa/chassi
negocios/      # Compra/Venda/Troca/Consignação (wizard), partes, itens, cálculos de lucro
contratos/     # ConfiguracaoLoja, Documento, Contrato; geração PDF/DOCX; templates jurídicos
templates/     # HTML (base, parciais, por app, contratos jurídicos, PWA, login)
static/        # css (input.css/Tailwind), js (htmx, máscaras, guia), imagens
media/         # Uploads locais em dev (em prod vão pro bucket)
scripts/ bin/  # Scripts auxiliares de deploy/operação
```

Cada app Django segue o padrão `models.py / views.py / forms.py / urls.py / services.py / admin.py / migrations/`.

### 1.4 Dependências externas — serviços/APIs (FATO)

| Serviço | Uso | Chave? | Onde |
|---|---|---|---|
| **Tabela FIPE** (`parallelum.com.br/fipe`) | Preço de referência; auto-preenche cadastro de carro | Grátis, sem chave | `core/fipe.py:13`, `core/views.py:216-242` |
| **ViaCEP** (`viacep.com.br`) | Preenche endereço/cidade/UF pelo CEP (JS no form de pessoa) | Grátis, sem chave | `templates/pessoas/form.html` (JS) |
| **CNPJá** (`open.cnpja.com`) | Consulta dados de empresa por CNPJ | Grátis (endpoint `open`) | `core/views.py:170-212` |
| **Bucket S3/R2/B2** | Armazenar fotos e documentos (privado) | Sim (AWS_*) | `prod.py:49-67` |
| **Neon Postgres** | Banco | Sim (DATABASE_URL) | `base.py:101` |
| **WhatsApp** (`wa.me`) | Link com mensagem pronta (não anexa arquivo) | Não | `contratos/views.py` (`enviar_whatsapp`), `veiculos/patio.html` |

> Consulta veicular paga (Credify) está na memória do projeto como **pendente** — não há integração no código (NÃO IDENTIFICADO no repo).

---

## 2. MODELO DE DADOS

Todos os modelos de negócio herdam de `ModeloBase` (`core/models.py:41`), que adiciona a **toda tabela**: `criado_em`, `atualizado_em`, `criado_por`(FK user), `atualizado_por`(FK user), `arquivado`(bool), `arquivado_em`, `empresa`(FK) + histórico automático (`historico`).

**Regra central (FATO, `core/models.py:1-16`):** nada é apagado. "Excluir" = `arquivar()`. Manager padrão `objetos` esconde arquivados e filtra pela empresa logada; manager `todos` vê tudo. Multi-tenant: a empresa é preenchida sozinha a partir do usuário logado (`core/models.py:83-89`, `core/tenancy.py`).

### 2.1 `contas.Empresa` e `contas.Usuario` (FATO, `contas/models.py`)

- **Empresa:** `nome`, `criado_em`.
- **Usuario** (estende `AbstractUser`): + `papel` (`administrador`/`vendedor`, default **vendedor**), `empresa`(FK).
  - `eh_administrador` = superuser **ou** papel administrador. Vendedor **não vê** valor de compra nem lucro.

### 2.2 `veiculos.Veiculo` (FATO, `veiculos/models.py:52-161`)

| Campo | Tipo | Obrigatório | Origem |
|---|---|---|---|
| `placa` | CharField(7) + `validar_placa` | **Sim** | manual (normalizada no save) |
| `marca` | CharField(60) | **Sim** | manual (auto-preenchível via FIPE) |
| `modelo` | CharField(120) | **Sim** | manual (auto-preenchível via FIPE) |
| `ano_fabricacao` | PositiveSmallInt | **Sim** | manual |
| `ano_modelo` | PositiveSmallInt | **Sim** | manual |
| `cor` | CharField(40) | **Sim** | manual |
| `km` | PositiveInt | Não | manual |
| `combustivel` | choices `Combustivel` | Não | manual/FIPE |
| `cambio` | choices `Cambio` | Não | manual |
| `chassi` | CharField(17) + `validar_chassi` | Não (mas exigido p/ contrato) | manual |
| `renavam` | CharField(11) + `validar_renavam` | Não (mas exigido p/ contrato) | manual |
| `situacao` | choices `Situacao` (default `proprio`) | **Sim** (tem default) | automático/manual |
| `proprietario` | FK Pessoa (PROTECT) | Não | automático (set em consignação/troca) |
| `proprietario_registral` | CharField(120) | Não | manual |
| `alienado` | Bool (default False) | — | manual |
| `credor_alienacao`, `saldo_devedor`, `parcelas_restantes`, `valor_parcela`, `dia_vencimento`, `parcelas_vencidas` | — | Não | manual (só se alienado) |
| `tem_chave_reserva` | Bool/null | Não | manual |
| `avarias_declaradas` | Text | Não | manual |
| `sinistro_declarado` | Bool | — | manual |
| `sinistro_descricao` | Text | Não | manual |
| `valor_compra` | Decimal | Não | **automático** (gravado ao concluir compra/troca) |
| `valor_anunciado` | Decimal | Não | manual |
| `status` | choices `StatusVeiculo` (default `em_estoque`) | **Sim** (default) | **automático** (muda no negócio) |
| `observacoes` | Text | Não | manual |

- **Propriedades calculadas:** `placa_formatada`, `eh_consignado`, `foto_capa`, `dias_na_loja` (hoje − `criado_em`).
- **Restrição:** placa única entre não-arquivados por empresa (`models.py:121-128`).
- **Índices:** `situacao`, `status` (`db_index=True`), `criado_em` (ordering).

**`veiculos.FotoVeiculo`** (`models.py:163`): `veiculo`(FK), `imagem`, `miniatura`, `ordem`, `capa`(bool). Constraint: uma capa por veículo.

### 2.3 `pessoas.Pessoa` (FATO, `pessoas/models.py:19`)

`tipo`(física/jurídica), **`nome`(obrigatório)**, `cpf_cnpj`(valida dígito verificador), `telefone`, `email`, `endereco`, `cidade`, `uf`, `cep`, `rg`, `rg_orgao_emissor`, `nacionalidade`, `estado_civil`, `profissao`, `representante_nome`, `representante_cpf`, `observacoes`. Tudo manual (CEP auto-preenche endereço via JS/ViaCEP). Só `nome` é realmente obrigatório no modelo; o resto é exigido só na hora de gerar contrato. Documento único por empresa entre não-arquivados.

### 2.4 `negocios` (FATO, `negocios/models.py`)

- **`Negocio`** (`:99`): `tipo` (compra/venda/troca), `modalidade` (própria/intermediação), `numero_contrato` (**automático** ao concluir), `data`, `data_hora_entrega`, `local_entrega`, `valor_total` (**calculado**), `diferenca` (troca), `forma_pagamento`, `detalhes_pagamento`, `comissao_valor`, `comissao_pagador`(FK), `consignacao`(FK), `negocio_relacionado`(FK self), `observacoes`, `status` (rascunho/concluído/cancelado, default **concluído**).
- **`ParteNegocio`** (`:166`): liga `negocio`↔`pessoa` com `papel` (vendedor/comprador/permutante/anuente).
- **`ItemNegocio`** (`:186`): `negocio`, `veiculo`, `de_pessoa`/`para_pessoa` (vazio = a loja), `valor`, `km_entrega`, `quitacao_opcao`/`quitacao_responsavel` (alienação) + **snapshots** `status_anterior`/`situacao_anterior`/`valor_compra_anterior` (para desfazer no cancelamento). Propriedades `entra_na_loja`/`sai_da_loja`.
- **`Consignacao`** (`:57`): `veiculo`, `proprietario`, `numero_contrato`, `data_entrada`, `valor_liquido_minimo`, `comissao_tipo`/`comissao_valor`, `prazo_dias`(90), `aviso_dias`(15), `prazo_repasse_dias`(5), `documentos_entregues`, `status` (ativa/vendida/encerrada), `repasse_feito_em`.

### 2.5 `contratos` (FATO, `contratos/models.py`)

- **`ConfiguracaoLoja`** (`:22`): singleton por empresa com dados da loja usados nos contratos (`razao_social`, `cnpj`, `endereco`, `cidade`, `uf`, `cep`, `representante_nome`, `representante_cpf`, `nome_fantasia`) + regras padrão (`multa_percentual`, `regra_ipva`, `prazo_assinatura_dias`, `prazo_repasse_dias`, `numero_vias`). `campos_faltando()` valida o que falta para contrato.
- **`Documento`** (`:116`): arquivo ligado a negócio **ou** consignação **ou** veículo, com `tipo` (contrato, termo_vistoria, recibo, consulta, procuração, doc_veículo, doc_pessoal, outro), `gerado_pelo_sistema`, `descricao`.
- **`Contrato`** (`:177`): ligado a negócio/consignação, `modelo` (A–E), `titulo`, `versao`, `corpo`(texto editável), `corpo_editado`(bool), `num_testemunhas`(2), `assinado`/`data_assinatura`.

### 2.6 Enums / status / constantes (FATO)

| Enum | Valores | Arquivo |
|---|---|---|
| `Combustivel` | flex, gasolina, etanol, diesel, elétrico, híbrido, gnv | `veiculos/models.py:24` |
| `Cambio` | manual, automático | `:34` |
| `Situacao` (veículo) | próprio, consignado, terceiro | `:39` |
| `StatusVeiculo` | em_estoque, reservado, vendido, devolvido | `:45` |
| `TipoNegocio` | compra, venda, troca | `negocios/models.py:7` |
| `Modalidade` | própria, intermediação | `:13` |
| `StatusNegocio` | rascunho, concluído, cancelado | `:18` |
| `FormaPagamento` | dinheiro, pix, cartão, financiado, troca+dinheiro | `:24` |
| `PapelParte` | vendedor, comprador, permutante, anuente | `:32` |
| `QuitacaoOpcao` | responsável, desconta_preço, anuência_credor | `:39` |
| `ComissaoTipo` | percentual, fixa, sobrepreço | `:45` |
| `StatusConsignacao` | ativa, vendida, encerrada | `:51` |
| `TipoPessoa` | física, jurídica | `pessoas/models.py:14` |
| `TipoDocumento` | contrato, termo_vistoria, recibo, consulta, procuração, doc_veículo, doc_pessoal, outro | `contratos/models.py:97` |
| `ModeloContrato` | A=compra, B=venda, C=troca, D=consignação, E=intermediação | `contratos/models.py:169` |
| `Papel` (usuário) | administrador, vendedor | `contas/models.py:30` |

---

## 3. TELAS E ROTAS

### 3.1 Lista de rotas (FATO — `config/urls.py` + `*/urls.py`)

| URL | View | Propósito | Acesso |
|---|---|---|---|
| `/` | `core.inicio` | Painel inicial (indicadores, gráfico, atalhos, alertas) | logado |
| `/conta/entrar/`, `/conta/sair/` | auth views | Login/logout | público/logado |
| `/estoque/` | `veiculos.estoque` | Grade de carros com filtros (status/origem/ordem) | logado |
| `/patio/` | `veiculos.patio` | Vitrine com botão WhatsApp por carro | logado |
| `/carros/novo/` | `veiculos.novo` | Cadastrar carro (+ fotos, + FIPE) | logado |
| `/carros/<pk>/` | `veiculos.detalhe` | Detalhe do carro | logado |
| `/carros/<pk>/editar/` | `veiculos.editar` | Editar carro | logado |
| `/carros/<pk>/arquivar/` | `veiculos.arquivar` | Arquivar | logado |
| `/carros/<pk>/documento/` `/fotos/` | add documento/fotos | Anexos | logado |
| `/fotos/<pk>/remover/` `/capa/` | — | Gerir fotos | logado |
| `/pessoas/` | `pessoas.lista` | Lista de pessoas | logado |
| `/pessoas/nova/` | `pessoas.novo` | Cadastro completo (17 campos) | logado |
| `/pessoas/nova-rapida/` | `pessoas.novo_rapido` | Cadastro rápido (tipo/nome/telefone) | logado |
| `/pessoas/<pk>/` `/editar/` `/arquivar/` | — | Detalhe/editar/arquivar | logado |
| `/vendas/` | `negocios.vendas` | Painel de vendas do mês (resumo + lista) | logado (lucro só admin) |
| `/vendas/exportar/` | `negocios.exportar_excel` | Exporta Excel | **só admin** |
| `/negocios/novo/<tipo>/` | `negocios.iniciar` | Inicia wizard (compra/venda/troca) | logado |
| `/negocios/<pk>/passo/quem/` `/carro/` `/pagamento/` | passos | Wizard genérico | logado |
| `/negocios/<pk>/troca/carro-loja/` `/carro-cliente/` `/valores/` | passos troca | Wizard de troca | logado |
| `/negocios/<pk>/revisao/` | `negocios.revisao` | Confirma e conclui | logado |
| `/negocios/<pk>/cancelar/` `/confirmar/` `/descartar/` | — | Cancelar/descartar | logado |
| `/consignacoes/nova/` | `negocios.consignar` | Receber carro em consignação | logado |
| `/consignacoes/<pk>/vender/` `/repasse/` `/devolver/` | — | Fluxo de consignado | logado |
| `/negocios/<pk>/consignado/comprador/` `/valores/` | — | Venda de consignado | logado |
| `/configuracao/` | `contratos.configuracao` | Dados da loja p/ contratos | logado |
| `/negocios/<pk>/documentos/` | upload docs | Anexar documentos ao negócio | logado |
| `/negocios/<pk>/contrato/gerar/` `/vistoria/gerar/` | gerar | Gera contrato / termo vistoria | logado |
| `/consignacoes/<pk>/contrato/gerar/` | — | Gera contrato de consignação | logado |
| `/contratos/<pk>/editar/` | editar_contrato | Editor do contrato | logado (destravar assinado = só admin) |
| `/contratos/<pk>/pdf/` `/docx/` `/imprimir/` `/whatsapp/` | — | Baixar/imprimir/enviar | logado |
| `/buscar/` | `core.buscar` | Busca global | logado |
| `/ajuda/`, `/agenda/`, `/consulta/` | core | Ajuda, agenda de pendências, consultas | logado |
| `/fipe/`, `/cnpj/` | core | Endpoints AJAX (FIPE/CNPJ) | logado |
| `/backup/` | `core.baixar_backup` | ZIP de dump + mídia | **só superuser** |
| `/manifest.webmanifest`, `/sw.js`, `/saude/` | core | PWA e healthcheck | público |
| `<ADMIN_URL>` | Django admin | Admin (URL não óbvia) | superuser |

### 3.2 Formulários — campos, ordem e validações (FATO)

**`VeiculoForm`** (`veiculos/forms.py:7`) — 28 campos, nesta ordem: placa, marca, modelo, ano_fabricacao, ano_modelo, cor, km, combustivel, cambio, chassi, renavam, situacao, proprietario_registral, valor_compra, valor_anunciado, status, alienado, credor_alienacao, saldo_devedor, parcelas_restantes, valor_parcela, dia_vencimento, parcelas_vencidas, tem_chave_reserva, avarias_declaradas, sinistro_declarado, sinistro_descricao, observacoes. Validações: placa normalizada + única (`clean_placa`); campos numéricos recebem `inputmode="numeric"`. *(No template `veiculos/form.html` os campos são agrupados em 5 seções + FIPE + fotos.)*

**`PessoaForm`** (`pessoas/forms.py:32`) — 17 campos: tipo, nome, cpf_cnpj, telefone, email, endereco, cidade, uf, cep, rg, rg_orgao_emissor, nacionalidade, estado_civil, profissao, representante_nome, representante_cpf, observacoes. CEP marcado `required`. Validações: CPF/CNPJ único + coerência tipo×documento (física=11 díg., jurídica=14).

**`PessoaRapidaForm`** (`:22`): tipo, nome, telefone.

**`PagamentoEntregaForm`** (`negocios/forms.py:50`): valor, km_entrega, forma_pagamento, detalhes_pagamento, data, data_hora_entrega, local_entrega, (+quitacao_opcao só se carro alienado).

**`TrocaValoresForm`** (`:93`): valor_loja, valor_cliente, km_loja, km_cliente, forma_pagamento, detalhes_pagamento, data, data_hora_entrega, local_entrega.

**`ConsignacaoTermosForm`** (`:125`): valor_liquido_minimo, comissao_tipo, comissao_valor, prazo_dias(90), aviso_dias(15), prazo_repasse_dias(5), documentos_entregues.

**`ConfiguracaoLojaForm`** (`contratos/forms.py:6`): razao_social, nome_fantasia, cnpj, endereco, cidade, uf, cep, representante_nome, representante_cpf.

**`DocumentoUploadForm`** (`:35`): tipo, descricao, juntar_pdf (juntar várias imagens num PDF).

### 3.3 Campos aparentemente redundantes (DEDUÇÃO)

- **marca/modelo/ano/combustível** existem como campos de texto no `VeiculoForm` **e** como seleção na FIPE (que preenche os mesmos campos). É intencional (FIPE é ajuda opcional), mas o usuário vê o dado duas vezes na mesma tela. (`veiculos/form.html`)
- **valor do carro da troca**: `valor_anunciado` do veículo é usado como valor inicial no passo da troca e **redigitado** em `troca_valores` (`valor_loja`/`valor_cliente`). (`negocios/views.py` passo troca — ver 4d)
- **Endereço/cidade/UF** da loja (ConfiguracaoLoja) e das pessoas são campos separados em cada lugar (esperado), mas o representante da loja repete nome+CPF que também existem no cadastro de pessoa se ele for cliente.

---

## 4. FLUXOS PRINCIPAIS (passo a passo real)

> Base: `negocios/views.py`, `negocios/services.py`, `veiculos/views.py`, templates. O wizard salva a cada passo (dá para marcar "rascunho" e sair). `concluir_negocio()` é **transacional** (`@transaction.atomic`, `services.py:207`).

### a) Cadastrar um carro no estoque (FATO)
- **1 tela** (`/carros/novo/`, `veiculos/views.py:68`, template `veiculos/form.html`).
- Opcional: seção FIPE no topo (tipo→marca→modelo→ano) que **auto-preenche** marca, modelo, anos, combustível e valor anunciado (JS, `form.html:13-40`).
- Preenche ~28 campos (5 seções) + envia fotos no mesmo form.
- Ao salvar: cada foto é **redimensionada no próprio request** (1600px + miniatura 400px, correção EXIF — `veiculos/services.py:21-48`) → redireciona ao detalhe.
- **Campos digitados: ~28.** **Telas: 1.** **Redundância:** marca/modelo/combustível se usar a FIPE (texto + seleção na mesma tela).

### b) Registrar uma venda (FATO)
**4 telas.** (modalidade "própria")
1. **Quem** (`passo_pessoa`): busca/escolhe o comprador (ou cadastra rápido). Cria `ParteNegocio` papel=COMPRADOR.
2. **Carro** (`passo_carro` → `passo_carro_estoque`): escolhe 1 carro vendável do estoque. Cria `ItemNegocio`.
3. **Pagamento** (`passo_pagamento`): valor, km_entrega, forma_pagamento, data, detalhes, data/hora+local de entrega (+quitação se alienado). ~7 campos.
4. **Revisão** (`revisao`): confirma → `concluir_negocio` → veículo vira `VENDIDO`, gera `numero_contrato`.
- **Campos digitados: cliente (1 escolha) + 1 carro + ~7 campos. Sem redigitação.**

### c) Registrar uma compra (FATO)
**4 telas.**
1. **Quem** (`passo_pessoa`, título "de quem é o carro"): escolhe o vendedor. `ParteNegocio` papel=VENDEDOR.
2. **Carro** (`passo_carro` → `passo_carro_novo`): **cadastra o carro inteiro** (VeiculoForm, ~28 campos). `ItemNegocio` com `de_pessoa`=vendedor, `para_pessoa`=loja.
3. **Pagamento**: mesmos ~7 campos da venda.
4. **Revisão** → `concluir_negocio`: veículo vira PRÓPRIO/EM_ESTOQUE e `valor_compra` = valor do negócio.
- **Campos digitados: vendedor + ~28 (carro) + ~7. Sem redigitação.**

### d) Registrar uma troca (FATO)
**5 telas.**
1. **Quem** (`passo_pessoa`): cliente/permutante.
2. **Carro da loja** (`troca_carro_loja`): escolhe o carro que **sai** do estoque.
3. **Carro do cliente** (`troca_carro_cliente`): **cadastra** o carro que entra (VeiculoForm ~28 campos); vira `situacao=terceiro`, proprietário=cliente.
4. **Valores** (`troca_valores`): valor_loja, valor_cliente, km dos dois, forma de pagamento da diferença, data, entrega. `diferenca = valor_loja − valor_cliente`.
5. **Revisão** → `concluir_negocio`: carro da loja → VENDIDO; carro do cliente → PRÓPRIO/EM_ESTOQUE, `valor_compra`=valor_cliente.
- **Redundância (FATO, confirmada por um dos agentes):** o valor do carro da loja já vem de `valor_anunciado` no passo 2 e é **redigitado** como `valor_loja` no passo 4; o valor do carro do cliente começa em 0 no passo 3 e é digitado no passo 4.

### e) Gerar e imprimir um contrato (FATO)
- A partir do negócio → `gerar` (`contratos/views.py`). Se faltam dados (loja, pessoa, chassi/renavam), mostra `faltando.html` com **lista + links** para preencher (`contratos/geracao.py:64-94`).
- Gera `Contrato` (corpo de texto renderizado do modelo A–E) → `editar_contrato`: tela com nº de testemunhas, observações e textarea do texto (editar à mão marca `corpo_editado=True`), checkbox "assinado" (trava edição; só admin destrava).
- Saídas: **PDF** (WeasyPrint — layout "MARA" bonito se não editado, ou o texto se editado), **DOCX** (python-docx), **Imprimir** (abre PDF + `window.print()`), **WhatsApp** (salva o PDF como documento e abre `wa.me` com mensagem pronta — **não anexa o arquivo**, só texto).
- **Telas típicas: 2** (gerar→editar) + 1 ação de download.

### f) Consultar quanto vendeu no mês e o que tem em estoque (FATO)
- **Estoque:** `/estoque/` (grade de cards, filtros) e painel inicial `/` (nº de carros, valor em estoque).
- **Vendas do mês:** `/vendas/` (`negocios/views.py:677`): navegação por mês, resumo (total vendido, lucro bruto, quantidade — **lucro só admin**) e lista paginada (50/página). Também no painel inicial (vendas do mês + gráfico de 6 meses).
- **Telas: 1–2.** Sem digitação (só navegação).

---

## 5. CONTRATOS

### 5.1 Como é gerado (FATO — `contratos/geracao.py`)
1. **Texto:** `gerar_contrato()` escolhe o modelo (A–E) por tipo/modalidade (`escolher_modelo`), renderiza um template `.txt` (`templates/contratos/modelos/<X>.txt`) com os dados e salva como `Contrato.corpo` (editável). Versão incremental.
2. **PDF:** `renderizar_pdf()` (WeasyPrint). Se o usuário **não editou** o texto, usa o layout "MARA" (`contratos/mara/contrato.html` ou `.../consignacao.html`, contexto em `contratos/mara.py`). Se editou, o PDF sai do texto (`pdf_base.html`).
3. **DOCX:** `renderizar_docx()` quebra o `corpo` em parágrafos (python-docx).
4. **Termo de vistoria:** `gerar_termo_vistoria()` gera PDF com checklist + até 6 fotos (embutidas como data-URI) e salva como `Documento`.

### 5.2 Modelos (um por tipo) (FATO — `contratos/models.py:169`, `geracao.py:29-45`)

| Modelo | Título | Quando |
|---|---|---|
| A | Compra e venda (compra pela loja) | compra |
| B | Compra e venda (venda pela loja) | venda |
| C | Permuta com complementação de preço | troca |
| D | Consignação de veículo | consignação |
| E | Compra e venda com interveniência | intermediação (venda de consignado/terceiro) |

Arquivos: `templates/contratos/modelos/{A,B,C,D,E}.txt` + parciais `_veiculo.txt`, `_rodape.txt`, `_loja.txt`, `_pessoa.txt`.

### 5.3 Variáveis e origem (FATO — ex.: `modelos/B.txt`)
- **Da loja (`ConfiguracaoLoja`):** razão social, nome fantasia, CNPJ, endereço, cidade/UF, CEP, representante+CPF, multa %, cidade do foro.
- **Das partes (`Pessoa`):** nome, nacionalidade, estado civil, profissão, RG+órgão, CPF/CNPJ, endereço/cidade/UF/CEP.
- **Do veículo (`Veiculo`):** marca, modelo, ano fab/modelo, cor, combustível, placa, renavam, chassi, km na entrega, avarias, chave reserva.
- **Do negócio (`Negocio`/`ItemNegocio`):** nº contrato, valor (+por extenso via `num2words`), forma/detalhes de pagamento, data e local de entrega, diferença da troca.
- Filtros próprios formatam CPF/CNPJ, CEP, reais, valor por extenso, sim/não (templatetags `formato`, `contratos_extras`, `pessoas_extras`).

Pré-geração valida o que falta (loja + cada pessoa + chassi/renavam do veículo) e bloqueia com lista de pendências (`geracao.py:64-94`).

---

## 6. VEÍCULO: ORIGEM DOS DADOS

### 6.1 Como marca/modelo/ano/placa/chassi/renavam/cor/km são capturados (FATO)
- **marca, modelo, cor:** texto livre (`CharField`) no `VeiculoForm` — **mas** há ajuda da **FIPE** no topo da tela (selects em cascata tipo→marca→modelo→ano) que preenche esses campos via JS (`veiculos/form.html`, `core/fipe.py`). Não há lista fixa obrigatória.
- **ano_fabricacao/ano_modelo:** numérico manual (FIPE preenche ano_modelo).
- **placa:** texto, normalizada (maiúsc., sem pontuação) e validada (antiga `ABC1234` ou Mercosul `ABC1D23`).
- **chassi:** texto, validado (17 caracteres, sem I/O/Q).
- **renavam:** texto, validado (11 dígitos).
- **km:** numérico manual.

### 6.2 Integrações (FATO)
- **FIPE** (preço de referência) — `core/fipe.py` (cache 12–24h), usada no cadastro de carro e na tela `/consulta/`.
- **Consulta de placa/RENAVAM (DETRAN) — NÃO IDENTIFICADA** no código (Credify pendente na memória do projeto).
- **CNPJ** (`open.cnpja.com`) e **CEP** (ViaCEP) existem, mas para dados de **pessoa/empresa**, não do veículo.

### 6.3 Validações (FATO)
- **Placa:** regex formato antigo/Mercosul (`veiculos/validators.py:24`).
- **Chassi:** 17 chars sem I/O/Q (`:33`).
- **Renavam:** 11 dígitos (`:44`).
- **CPF/CNPJ:** dígitos verificadores completos + coerência com tipo de pessoa (`pessoas/validators.py`, `pessoas/forms.py:72-81`).
- Unicidade: placa por empresa; CPF/CNPJ por empresa.

---

## 7. DASHBOARD E RELATÓRIOS (FATO — `core/views.py:75-140`, `negocios/services.py`)

### 7.1 Painel inicial `/`
| Indicador | Cálculo | Linha |
|---|---|---|
| Carros na loja | count de `EM_ESTOQUE` exceto terceiro | `views.py:80-84` |
| Valor em estoque | `Sum(valor_anunciado)` dos próprios em estoque | `:87-90` |
| Carros de terceiros | count consignado/terceiro em estoque | `:92-96` |
| Vendas no mês | count de concluídos (venda+troca) do mês | `:99-104` |
| **Lucro do mês** (só admin) | `resumo_de_vendas()["lucro_bruto"]` | `:108` |
| Carros parados (top 3) | próprios parados > `DIAS_CARRO_PARADO` (90) | `:111`, `:25-33` |
| Repasses pendentes | count consignações vendidas sem repasse | `:133` |
| Últimos negócios | 5 concluídos | `:134` |
| Gráfico 6 meses | 6 counts (venda+troca) | `:135`, `:48-72` |
| Alertas | primeiros 4 da agenda | `:136` |

### 7.2 Painel de vendas `/vendas/` e `resumo_de_vendas` (FATO — `services.py:397-411`)
- **Total vendido:** soma de `valor_total` dos negócios venda+troca concluídos do mês.
- **Lucro bruto:** soma de `lucro_bruto(n)` — venda: `valor − valor_compra`; troca: `valor do carro que sai − seu valor_compra`; intermediação: comissão; compra: sem lucro (`services.py:350-377`). Devolve `None` se faltar `valor_compra`.
- **Quantidade:** count de **todos** os negócios do mês (inclui compra).
- Lista: por negócio mostra tipo, nº, carro que saiu/entrou, valor e (admin) lucro.

### 7.3 Agenda `/agenda/` (FATO — `core/agenda.py`)
Repasses a pagar; consignações vencidas/perto do prazo (`data_entrada + prazo_dias − hoje`); carros parados >90 dias; rascunhos antigos (>2 dias). Ordenadas por urgência. O context processor `pendencias` injeta a contagem em **toda** página.

### 7.4 Controle de acesso (FATO)
Vendedor não vê lucro nem valor de compra (`eh_administrador` controla `lucro_do_mes`, coluna de lucro, exportar Excel e backup).

---

## 8. PROBLEMAS TÉCNICOS OBSERVADOS

> Contexto importante (DEDUÇÃO): o volume de dados de uma loja de usados é pequeno (dezenas de carros, centenas de negócios/ano), então vários itens abaixo são de **baixo impacto real**, mesmo sendo anti-padrões.

### 8.1 Cálculos em Python em vez de no banco (FATO)
- `_carros_parados` (`core/views.py:25-33`) carrega **todos** os carros próprios em estoque e filtra em Python por `dias_na_loja` (property). O mesmo em `core/agenda.py` (carros parados). Impacto baixo pelo volume, mas não escala e impede índice.

### 8.2 Consultas repetidas por request (FATO)
- `lembretes(hoje)` roda **em toda página** pelo context processor `pendencias` (`core/context_processors.py`) — ~6-7 queries por request. No painel inicial roda **duas vezes** (uma no context processor e outra em `inicio` na linha 122). Sem cache.
- `_vendas_por_mes` faz **6 counts** separados (`core/views.py:60-66`), um por mês, a cada abertura do painel. Sem cache.
- Painel inicial recalcula todos os indicadores a cada acesso; nenhum é cacheado.

### 8.3 Processamento de imagem no request (FATO — `veiculos/services.py:21-48`)
- Cada foto enviada é aberta, corrigida por EXIF e redimensionada **2x** (grande + miniatura) de forma **síncrona** dentro do POST. Fotos grandes de celular podem deixar o cadastro lento / arriscar timeout. Sem fila assíncrona.
- Upload de fotos **não valida tipo MIME nem tamanho por foto** (só documentos validam tamanho). Arquivo corrompido/não-imagem pode estourar sem tratamento (`services.py` sem try/except no open/resize).

### 8.4 N+1 / prefetch ausentes (FATO, com uma correção)
- **CORREÇÃO a um achado de agente:** o loop do painel de vendas (`negocios/views.py:705-719`) usa `n.itens.all()` **depois** de `prefetch_related("itens__veiculo")` (linha 694). O Django reaproveita o cache do prefetch — **não há N+1 aqui** (o próprio código documenta isso em `services.py:364-365`). Foi marcado como "crítico" por um agente, mas está **incorreto**.
- `enviar_whatsapp` / funções de contrato acessam `contrato.negocio.partes` / `contrato.consignacao` sem `select_related`/`prefetch` (`contratos/views.py`) — poucas queries extras, baixo impacto (DEDUÇÃO/parcialmente verificado).
- `detalhe` de negócio carrega `contratos` e `documentos` sem prefetch e itera (`negocios/views.py:481,497`) — baixo impacto (poucos itens).
- `inicio` carrega `ultimos_negocios[:5]` sem prefetch dos itens; se o template acessar itens, pequeno N+1 (DEDUÇÃO).

### 8.5 Tratamento de erro em integrações externas (FATO)
- FIPE (`core/fipe.py:27-30`) e CNPJ (`core/views.py`) usam `urllib` com timeout mas **sem retry/circuit breaker**; se a API cair, a chamada falha.
- O `.catch()` do ViaCEP no JS silencia erros (usuário não é avisado se o CEP não resolver).

### 8.6 Lógica/código duplicado (FATO)
- Função de estilização de widgets de form repetida em `veiculos/forms.py:53-63` e `pessoas/forms.py:10-19` (em pessoas é `_estilizar`, em veículos é inline).
- Montagem da mensagem de WhatsApp existe em JS (`veiculos/patio.html`) e em Python (`contratos/views.py`) com formatos diferentes.
- O loop de upload de fotos (`for arquivo in request.FILES.getlist("fotos")`) se repete em `novo`, `editar` e `adicionar_fotos` (`veiculos/views.py`).

### 8.7 Erro de regra não tratado (DEDUÇÃO — a confirmar)
- `consignar` (`negocios/views.py`) chama `criar_consignacao()`, que pode lançar `RegraNegocioError`, **sem** try/except na view — resultaria em 500 em vez de mensagem amigável. (Apontado por agente; não reverifiquei a linha exata.)

### 8.8 Pontos positivos observados (FATO)
- Operações que mexem em várias tabelas são **transacionais** (`@transaction.atomic` em concluir/cancelar/consignar/repasse/devolver).
- `select_related`/`prefetch_related` corretos em estoque, revisão, detalhe de negócio, resumo de vendas.
- `CONN_MAX_AGE=600` + health checks para o Neon; sessão de 90 dias sem regravar a cada clique.
- Snapshots em `ItemNegocio` permitem desfazer o negócio ao cancelar.

---

## 9. RESPONSIVIDADE E MOBILE (FATO — templates + `static/css/input.css`)

- **É responsivo e mobile-first.** `base.html` tem viewport correto, fonte base 17px, PWA completo (manifest + service worker + apple-touch-icon), sidebar oculta no celular (hambúrguer) e visível em `md:`. Uso amplo de breakpoints Tailwind (`sm:`/`md:`/`lg:`/`xl:`).
- **Não há nenhuma tabela HTML de dados** nas listas — estoque e pátio usam **cards em grade**; vendas, pessoas e detalhe de negócio usam **listas** (`<ul>/<li>` flex). A única `<table>` é no termo de vistoria, que é **PDF** (não é tela). → Risco de "tabela larga no celular" **não existe**.
- **Alvos de toque** bem dimensionados: botões `min-height:48px` (formas de pagamento 56px, cartões de ação 72px), campos 48px, nav 44px.
- **Telas com risco moderado no celular (DEDUÇÃO a partir da leitura):**
  1. **Cadastro de carro** (`veiculos/form.html`): ~28 campos em 5 seções sempre visíveis + FIPE + fotos → **scroll muito longo** (não há acordeão/colapso). É estruturado, mas é a tela mais pesada.
  2. **Editor de contrato** (`contratos/editar.html`): `textarea rows=16` em fonte monoespaçada → apertado no celular.
  3. **Selects da FIPE** em cascata: podem ficar grandes com marcas/modelos de muitas opções.
  4. Pares de botões lado a lado com `gap-2` podem ficar justos em telas estreitas (ex.: iPhone SE).
- Upload de fotos usa `capture="environment"` (abre a câmera direto no celular) — bom para mobile.

---

## 10. RESUMO EM 10 LINHAS

1. É um **sistema Django (Python 3.13) + Postgres (Neon)**, hospedado no Render via Docker, para uma **loja de carros usados** gerenciar estoque, compra, venda, troca, consignação e contratos.
2. O usuário é um **dono de loja leigo**, usando **principalmente pelo celular** — e o frontend reflete isso: responsivo, PWA, cards em vez de tabelas, alvos de toque grandes.
3. Entidades centrais: **Veículo**, **Pessoa**, **Negócio** (com Partes e Itens) e **Contrato/ConfiguraçãoLoja**; tudo multi-loja e com "arquivar em vez de apagar" + histórico automático.
4. Os negócios são **wizards** passo a passo (4 telas venda/compra, 5 troca) que já salvam rascunho e concluem numa revisão transacional, mudando o status do carro automaticamente.
5. Há **FIPE** (preço), **ViaCEP** (endereço) e **CNPJ** integrados por conveniência; **não há** consulta de placa/DETRAN (Credify ainda pendente).
6. Contratos têm **5 modelos jurídicos** (A–E), geram texto editável e saem em **PDF (WeasyPrint), DOCX e impressão**, com envio por link de WhatsApp.
7. Dashboard mostra estoque, vendas do mês, lucro (só admin), carros parados e uma **agenda de pendências** (repasses, prazos, rascunhos).
8. Fonte de fricção nº 1: **cadastro de carro com ~28 campos numa tela só** + os mesmos dados do carro redigitados no fluxo de troca.
9. Fonte de fricção nº 2: **processamento de fotos síncrono no request** e **recálculo sem cache** de indicadores/agenda em toda página (a agenda roda até 2x no painel).
10. Fonte de fricção nº 3: **dependência de digitação manual** (marca/modelo/chassi/renavam) sem consulta de placa, e integrações externas **sem retry/tratamento de erro** (FIPE/CNPJ/CEP), que podem falhar silenciosamente.
</content>
</invoke>
