# Sistema da Loja de Veículos: especificação do MVP

Este arquivo é a fonte de verdade do projeto. Leia inteiro antes de escrever qualquer código.

## 0. Como trabalhar neste projeto

- Trabalhe por fases (seção 9). Ao terminar cada fase, pare, rode os testes, me mostre o que foi feito e espere meu ok antes de seguir.
- Antes de cada fase, escreva um plano curto (arquivos que vai criar ou alterar e por quê) e espere aprovação.
- Se algo nesta especificação estiver ambíguo ou faltando, pergunte. Não invente regra de negócio.
- Itens marcados com **[SUPOSIÇÃO]** são palpites meus que ainda não confirmei com o usuário final. Implemente de forma que seja fácil mudar depois.
- Não adicione funcionalidades fora do escopo (seção 10), mesmo que pareçam úteis. Anote como sugestão no final da fase.
- Commits pequenos, mensagens em português, uma mudança lógica por commit.

## 1. Contexto

O usuário final é dono de uma loja de veículos pequena (seminovos e usados). Ele é leigo em tecnologia: não conhece termos técnicos, se perde em telas com muitas opções e desiste se algo parecer complicado.

Problemas que o sistema precisa resolver, em ordem de prioridade:

1. **Não perder dados**: hoje informações de carros, clientes e contratos se perdem.
2. **Encontrar contratos**: de compra, venda e troca.
3. **Encontrar vendas**: saber o que foi vendido, para quem, quando e por quanto.
4. **Controlar estoque**: saber quais carros estão na loja, quanto custaram e por quanto estão anunciados.

Critério de sucesso: ele consegue, sozinho e pelo celular, cadastrar um carro, registrar uma venda com foto do contrato e achar esse contrato meses depois digitando só a placa ou o nome do cliente.

## 2. Stack

- Python, versão estável mais recente suportada pelo Django.
- Django (versão LTS ou estável mais recente) com templates do próprio Django.
- HTMX para interatividade (busca ao digitar, formulários sem recarregar a página). Sem React, Vue ou qualquer SPA.
- Tailwind CSS via CLI standalone (sem Node no projeto, se possível). Se não for viável, use Tailwind via build simples e documente.
- Banco: PostgreSQL. Em desenvolvimento, Postgres via Docker Compose.
- Arquivos (fotos e contratos): django-storages com backend compatível com S3. Em desenvolvimento, pasta local `media/`.
- Geração de PDF: WeasyPrint, a partir de template HTML.
- Testes: pytest + pytest-django.
- Qualidade: ruff (lint e format).
- Configuração por variáveis de ambiente (`.env`, com `.env.example` versionado). Nenhum segredo no código.

> Decisões confirmadas no início do projeto: Python 3.13 + Django 5.2 LTS, ambiente gerenciado com `uv` + `pyproject.toml`. Cor de destaque: azul-petróleo. Fonte: Inter.

## 3. Modelo de dados

Todos os modelos herdam de uma base com:

- `criado_em`, `atualizado_em` (automáticos)
- `criado_por`, `atualizado_por` (FK para usuário)
- `arquivado` (bool, padrão False) e `arquivado_em`

**Nada é apagado de verdade.** Não exponha delete em nenhuma tela. "Excluir" na interface significa arquivar. O manager padrão filtra arquivados; crie um manager `todos` que inclui arquivados.

### 3.1 Pessoa

Serve para clientes, para quem vende carro para a loja, para quem deixa carro em consignação e para os dois lados de um negócio intermediado.

| Campo | Tipo | Regras |
|---|---|---|
| tipo | escolha: física, jurídica | obrigatório |
| nome | texto | obrigatório |
| cpf_cnpj | texto | opcional no cadastro rápido, obrigatório para gerar contrato; validar dígitos verificadores; único entre não arquivados |
| telefone | texto | opcional; guardar só dígitos, exibir formatado |
| email | email | opcional |
| endereco, cidade, uf, cep | texto | opcionais; obrigatórios para gerar contrato |
| rg, rg_orgao_emissor | texto | opcionais; obrigatórios para contrato de pessoa física |
| nacionalidade, estado_civil, profissao | texto | opcionais; obrigatórios para contrato de pessoa física |
| representante_nome, representante_cpf | texto | só pessoa jurídica |
| observacoes | texto longo | opcional |

### 3.2 Veiculo

| Campo | Tipo | Regras |
|---|---|---|
| placa | texto | obrigatório; aceitar formato antigo (ABC1234) e Mercosul (ABC1D23); salvar em maiúsculas sem hífen; única entre não arquivados |
| marca | texto | obrigatório |
| modelo | texto | obrigatório (ex.: "Gol 1.0 MPI") |
| ano_fabricacao | inteiro | obrigatório |
| ano_modelo | inteiro | obrigatório |
| cor | texto | obrigatório |
| km | inteiro | opcional |
| combustivel | escolha: flex, gasolina, etanol, diesel, elétrico, híbrido, GNV | opcional |
| cambio | escolha: manual, automático | opcional |
| chassi | texto | opcional; se preenchido, 17 caracteres, sem as letras I, O, Q; obrigatório para contrato |
| renavam | texto | opcional; se preenchido, 11 dígitos; obrigatório para contrato |
| situacao | escolha: proprio, consignado, terceiro | `proprio` = da loja; `consignado` = de particular, exposto na loja; `terceiro` = só aparece num negócio intermediado, nunca no estoque |
| proprietario | FK Pessoa | obrigatório quando `consignado` ou `terceiro`; vazio quando `proprio` |
| proprietario_registral | texto | nome de quem consta no documento do veículo, se diferente do proprietário |
| documento_autorizacao | FK Documento | procuração ou autorização do proprietário registral, quando aplicável |
| alienado | bool | tem financiamento ativo |
| credor_alienacao, saldo_devedor, parcelas_restantes, valor_parcela, dia_vencimento, parcelas_vencidas | vários | obrigatórios quando `alienado` |
| tem_chave_reserva | bool | opcional |
| avarias_declaradas | texto longo | opcional; entra no contrato |
| sinistro_declarado, sinistro_descricao | bool, texto | opcional; entra no contrato |
| valor_compra | decimal | só para `proprio`; preenchido pelo negócio de entrada, editável |
| valor_anunciado | decimal | opcional |
| status | escolha: em_estoque, reservado, vendido, devolvido | controlado pelos negócios e consignações (ver 3.5); "reservado" é manual; "devolvido" = consignado retirado pelo dono |
| observacoes | texto longo | opcional, não entra no contrato |

### 3.3 FotoVeiculo

- FK para Veiculo, arquivo de imagem, ordem, `capa` (bool, só uma por veículo).
- Redimensionar no upload para no máximo 1600px no maior lado e gerar miniatura. Fotos de celular são pesadas.

### 3.4 Negocio, ParteNegocio e Consignacao

A loja trabalha de dois jeitos: às vezes é dona do carro, às vezes só intermedia. Isso é o campo `modalidade`.

**Negocio**

| Campo | Tipo | Regras |
|---|---|---|
| tipo | escolha: compra, venda, troca | obrigatório |
| modalidade | escolha: propria, intermediacao | `propria` = loja é parte e dona; `intermediacao` = negócio entre particulares (inclui venda de consignado) |
| numero_contrato | inteiro | sequencial único, gerado ao concluir |
| data | data | obrigatório, padrão hoje |
| data_hora_entrega | data e hora | obrigatório para gerar contrato (define responsabilidade por multas) |
| local_entrega | texto | padrão: endereço da loja |
| valor_total | decimal | calculado (ver regras) |
| forma_pagamento | escolha: à vista, financiado, parcelado na loja, misto | opcional |
| detalhes_pagamento | texto longo | opcional |
| comissao_valor | decimal | só `intermediacao` |
| comissao_pagador | FK Pessoa | só `intermediacao` |
| consignacao | FK Consignacao | preenchido quando é venda de carro consignado |
| observacoes | texto longo | opcional, não entra no contrato |
| status | escolha: rascunho, concluido, cancelado | padrão concluido |

**ParteNegocio** (substitui o antigo campo `pessoa` do Negocio)

| Campo | Tipo | Regras |
|---|---|---|
| negocio | FK Negocio | obrigatório |
| pessoa | FK Pessoa | obrigatório |
| papel | escolha: vendedor, comprador, permutante, anuente | `anuente` = proprietário registral que assina concordando |

A loja nunca é cadastrada como Pessoa. Ela é parte implícita quando `modalidade = propria` e interveniente quando `modalidade = intermediacao`. Dados da loja ficam em configuração (seção 5).

**Consignacao**

| Campo | Tipo | Regras |
|---|---|---|
| veiculo | FK Veiculo | obrigatório; veículo com `situacao = consignado` |
| proprietario | FK Pessoa | obrigatório |
| numero_contrato | inteiro | sequencial único |
| data_entrada | data | obrigatório |
| valor_liquido_minimo | decimal | obrigatório |
| comissao_tipo | escolha: percentual, fixa, sobrepreco | obrigatório |
| comissao_valor | decimal | obrigatório exceto `sobrepreco` |
| prazo_dias, aviso_dias, prazo_repasse_dias | inteiro | padrões configuráveis |
| documentos_entregues | texto | o que o dono deixou na loja |
| status | escolha: ativa, vendida, encerrada | |
| repasse_feito_em | data | preenchido quando a loja paga o dono |

### 3.5 ItemNegocio

Liga veículos a um negócio e diz quem entrega para quem.

| Campo | Tipo | Regras |
|---|---|---|
| negocio | FK Negocio | obrigatório |
| veiculo | FK Veiculo | obrigatório |
| de_pessoa | FK Pessoa | quem entrega; vazio = a loja |
| para_pessoa | FK Pessoa | quem recebe; vazio = a loja |
| valor | decimal | valor atribuído a esse carro no negócio |
| km_entrega | inteiro | obrigatório para gerar contrato |

Regras de negócio, modalidade própria:

- **Compra**: 1 item de particular para a loja. Ao concluir, veículo vira `proprio`, `em_estoque`, e `valor_compra` recebe o valor do item.
- **Venda**: 1 item da loja para o cliente. O veículo precisa ser `proprio` e estar `em_estoque` ou `reservado`. Ao concluir, vira `vendido`.
- **Troca**: 1 item da loja para o cliente e 1 ou mais do cliente para a loja. Ao concluir, o que saiu vira `vendido` e os que entraram viram `proprio`, `em_estoque`, com `valor_compra`. **[SUPOSIÇÃO]** no máximo um carro da loja sai por troca.
- Diferença da troca = valor que sai da loja menos soma do que entra. Exibir: "Cliente paga R$ X" ou "Loja paga R$ X".

Regras de negócio, intermediação:

- Nenhum item tem a loja como origem ou destino. Todos os itens vão de uma pessoa para outra.
- **Venda de consignado**: o veículo precisa ser `consignado` e ter Consignacao `ativa`. Ao concluir, veículo vira `vendido`, consignação vira `vendida`, e aparece pendência de repasse ao dono.
- **Negócio entre particulares** (como uma troca que a loja só aproximou): os veículos são cadastrados com `situacao = terceiro` e não entram no estoque.
- O lucro da loja é a comissão, não a diferença entre compra e venda.
- Uma operação pode misturar as duas modalidades (cliente dá o carro dele como entrada de um consignado). O fluxo pergunta "O carro que o cliente deu fica com quem?" e gera dois negócios ligados (campo `negocio_relacionado`).

Regras gerais:

- Se o proprietário registral de um veículo for diferente de quem entrega, o negócio exige um anuente em ParteNegocio ou um `documento_autorizacao`. Sem isso, o contrato não é gerado e a tela explica o motivo.
- Se o veículo for `alienado`, o fluxo obriga a escolher como fica a quitação (ver CONTRATOS.md, bloco B5).
- **Cancelar** um negócio concluído desfaz as mudanças de status dos veículos e da consignação, com confirmação clara, e registra no histórico. Nunca apagar.
- Toda mudança de status acontece dentro de transação (`transaction.atomic`) junto com o negócio.

### 3.6 Documento

| Campo | Tipo | Regras |
|---|---|---|
| negocio | FK Negocio | opcional; um dos dois (negocio ou consignacao) é obrigatório |
| consignacao | FK Consignacao | opcional |
| tipo | escolha: contrato, termo de vistoria, recibo, consulta de situação do veículo, procuração/autorização, documento do veículo (CRV/CRLV), documento pessoal, outro | obrigatório |
| arquivo | arquivo | PDF ou imagem; limite configurável (padrão 20 MB) |
| gerado_pelo_sistema | bool | true quando o PDF foi gerado pelo sistema |
| descricao | texto | opcional |

Aceitar várias imagens de uma vez (contrato fotografado em várias páginas). **[SUPOSIÇÃO]** juntar as fotos de um mesmo envio em um único PDF é desejável; implemente como opção na fase de documentos se não for complexo, senão anote como sugestão.

### 3.7 Histórico

Registrar toda criação, edição, arquivamento e cancelamento: quem, quando, qual objeto, o que mudou (antes e depois). Pode usar django-simple-history ou implementação própria. Tela de histórico visível no detalhe de veículo e de negócio, em linguagem simples ("Karine alterou o valor anunciado de R$ 30.000 para R$ 28.500 em 05/10/2026").

## 4. Telas

Todas as telas são **mobile first**. Teste em largura de 375px antes de pensar em desktop.

### 4.1 Início

- Barra de busca grande no topo, com foco automático no desktop.
- Abaixo, 4 botões grandes: **Cadastrar carro que entrou**, **Registrar venda**, **Registrar troca**, **Carro deixado para vender** (consignação).
- Resumo simples: quantos carros na loja (próprios e consignados), quantas vendas no mês, repasses pendentes a donos de consignados.
- Últimos 5 negócios registrados.

### 4.2 Busca (o recurso mais importante)

- Um único campo que busca ao digitar (HTMX, debounce de ~300ms) em: placa, modelo, marca, nome da pessoa, CPF/CNPJ, telefone.
- Busca tolerante: ignorar maiúsculas, acentos, hífens e espaços na placa e pontuação no CPF. Use `unaccent` e `pg_trgm` do Postgres.
- Resultados agrupados: **Carros** e **Pessoas**, com foto/miniatura e status.
- Tocar em um carro abre o detalhe do carro. Tocar em uma pessoa abre o detalhe da pessoa.

### 4.3 Estoque

- Lista em cards: foto de capa, modelo, ano, cor, placa, valor anunciado, status com cor, e uma etiqueta discreta **Consignado** quando o carro não é da loja.
- Filtro simples por status (abas: Na loja, Reservados, Vendidos). Padrão: Na loja. Filtro secundário: Todos, Da loja, Consignados.
- Veículos com `situacao = terceiro` nunca aparecem no estoque.
- Ordenar por: mais recentes, mais antigos na loja.
- Mostrar há quantos dias o carro está na loja.

### 4.4 Detalhe do veículo

- Galeria de fotos (adicionar foto direto pela câmera: `accept="image/*" capture="environment"`).
- Dados do carro, editáveis.
- **Linha do tempo de negócios** desse carro (comprado de quem, vendido para quem), cada um com acesso direto aos documentos.
- Se consignado: dono, valor mínimo, comissão, dias restantes da consignação, botão "Dono retirou o carro".
- Se alienado: credor e saldo devedor em destaque.
- Lucro bruto quando vendido (próprio: venda menos compra; consignado: comissão), visível só para administrador.

### 4.5 Fluxos de negócio (compra, venda, troca)

Formulários em passos curtos, um assunto por tela:

1. **De quem é o carro?** Pergunta em linguagem simples: "O carro é da loja" ou "A loja só está ajudando a vender". Isso define a modalidade. Se escolher um carro consignado do estoque, a modalidade é definida automaticamente.
2. **Quem?** Buscar pessoa existente ou cadastrar rápido (só nome e telefone; resto depois). Na intermediação, as duas pessoas.
3. **Qual carro?** Venda: escolher do estoque. Compra: cadastrar o carro ali mesmo. Troca: os dois.
4. **Financiamento?** Para cada carro: "Esse carro ainda tem parcela de banco?" Se sim, dados do financiamento e como fica a quitação.
5. **Valores, pagamento e entrega** (data, hora e km).
6. **Contrato**: gerar pelo sistema (modelo escolhido automaticamente, ver CONTRATOS.md) e depois tirar foto do contrato assinado.
7. **Revisão**: resumo em linguagem simples ("Você está vendendo o Gol prata ABC1D23 para João Silva por R$ 32.000. Confirmar?").

Permitir salvar como rascunho em qualquer passo.

### 4.6 Detalhe do negócio

- Resumo, veículos, valores, pessoa, documentos (abrir, baixar, compartilhar pelo WhatsApp via link de compartilhamento nativo do celular).
- Botão para gerar contrato em PDF.
- Botão para cancelar o negócio (com confirmação em duas etapas).

### 4.7 Pessoas

- Lista com busca.
- Detalhe: dados, e todos os negócios dessa pessoa com seus documentos.

### 4.8 Vendas

- Lista de negócios filtrável por tipo e por mês.
- Total vendido no mês e lucro bruto do mês (só administrador).

## 5. Geração de contrato

- **O texto dos contratos, os blocos e a regra de qual modelo usar estão em `CONTRATOS.md`.** Leia antes da Fase 5.
- Cinco modelos: A (compra pela loja), B (venda pela loja), C (troca com a loja), D (consignação), E (intermediação). O sistema escolhe o modelo a partir de `tipo`, `modalidade` e da existência de consignação. O usuário não escolhe modelo.
- Templates HTML com blocos comuns em `partials/`, renderizados para PDF com WeasyPrint.
- Gerar também, sempre que houver entrega de veículo, o **termo de vistoria e entrega** (anexo 1 do CONTRATOS.md), com as fotos tiradas na hora.
- Configuração da loja (tela só do administrador): razão social, CNPJ, endereço, representante, multa contratual, regra de IPVA, prazos padrão, número de vias. Sem essa configuração completa, nenhum contrato é gerado.
- O texto jurídico dos templates é um **modelo provisório**. Marque cada cláusula com o comentário `<!-- REVISAR COM ADVOGADO -->` e deixe na tela de configuração um aviso de que o modelo precisa ser revisado. Não apresente o texto como juridicamente válido.
- Se faltar dado obrigatório para o contrato (ex.: CPF), mostrar exatamente o que falta com link para preencher, em vez de erro genérico.
- O PDF gerado é salvo automaticamente como Documento do negócio (ou da consignação).
- Gerar contrato não muda nada no negócio. Regerar cria nova versão e mantém a anterior.

## 6. Design visual

O sistema **não pode parecer feito por IA** nem parecer painel administrativo genérico. Diretrizes:

- Proibido: gradientes roxo/azul, emojis na interface, ícones de brilho/estrela, glassmorphism, sombras exageradas, cantos excessivamente arredondados em tudo, textos de marketing ("Gerencie seu estoque de forma inteligente!").
- Paleta sóbria e quente: fundo off-white, texto quase preto, uma cor de destaque só (azul-petróleo), cores de status discretas (verde, âmbar, cinza).
- Tipografia: Inter, corpo mínimo 17px no celular, títulos claros.
- Botões grandes (altura mínima 48px), sempre com texto. Ícone só como apoio ao texto.
- Contraste mínimo WCAG AA.
- Textos da interface em português simples, como uma pessoa falaria: "Salvar", "Voltar", "Carro vendido", "Foto do contrato". Nunca: "Registro", "Entidade", "Submeter", "Instância", "Erro 500".
- Mensagens de erro dizem o que fazer: "Essa placa já está cadastrada. Toque aqui para ver o carro."
- Toda ação importante mostra confirmação visível ("Venda salva").
- Valores sempre em formato brasileiro (R$ 32.000,00), datas em dd/mm/aaaa, placa formatada (ABC-1234 ou ABC1D23).
- Campos com máscara e teclado certo no celular (`inputmode="numeric"` para km, CPF, valores).

## 7. Usuários e segurança

- Login com usuário e senha (auth do Django). Sessão longa no celular para ele não precisar logar todo dia.
- Dois papéis: **administrador** (vê tudo, inclusive valores de compra e lucro) e **vendedor** (não vê valor de compra nem lucro). **[SUPOSIÇÃO]** pode haver funcionário usando junto.
- Os dados incluem CPF, endereço e documentos pessoais (LGPD): acesso só autenticado, arquivos servidos por URL assinada com expiração, nunca públicos.
- HTTPS obrigatório em produção, configurações de segurança do Django ativadas (`SECURE_*`, `CSRF`, `SESSION_COOKIE_SECURE`).
- O Django admin fica habilitado só para mim (superusuário), em URL não óbvia. Não é interface do usuário final.

## 8. Backup e proteção dos dados

- Script de backup diário: `pg_dump` compactado, enviado para um bucket diferente do de produção, retenção de 30 diários e 12 mensais.
- Arquivos de mídia com versionamento ativado no bucket (ou cópia para bucket de backup).
- Script de **restauração** documentado e testado (`make restore` ou equivalente). Backup que nunca foi restaurado não conta.
- Exportação manual: botão (só administrador) que gera planilha Excel com veículos, pessoas e negócios, para ele ter uma cópia própria.

## 9. Fases

Cada fase termina com testes passando, ruff limpo e uma demonstração curta do que mudou.

**Fase 1: Fundação**
Projeto Django, Docker Compose com Postgres, settings por ambiente, Tailwind configurado, layout base mobile, login, modelo base com arquivamento e histórico, ruff e pytest rodando.
Aceite: consigo logar no celular e ver a tela inicial vazia com o layout final.

**Fase 2: Veículos e estoque**
Modelos Veiculo e FotoVeiculo, validações (placa, chassi, renavam), cadastro, edição, arquivamento, upload de foto pela câmera, tela de estoque e detalhe.
Aceite: cadastro um carro pelo celular com 3 fotos e ele aparece no estoque.

**Fase 3: Pessoas**
Modelo Pessoa, validação de CPF/CNPJ, cadastro rápido e completo, lista e detalhe.

**Fase 4: Negócios e consignação**
Negocio, ParteNegocio, ItemNegocio e Consignacao, fluxos em passos para as duas modalidades, regras de status com transação, cancelamento, repasse ao dono do consignado, linha do tempo no veículo e na pessoa.
Aceite: testes cobrindo todas as regras das seções 3.4 e 3.5, incluindo: troca própria, venda de consignado, troca entre particulares, carro alienado, proprietário registral diferente sem autorização (deve bloquear) e cancelamento de cada caso.

**Fase 5: Documentos e contratos**
Configuração da loja, os cinco modelos do CONTRATOS.md, termo de vistoria, filtro `extenso`, checagem de campos faltantes, upload de documentos (várias imagens), compartilhamento.
Aceite: gero um contrato de cada modelo com dados fictícios e reviso o PDF; registro uma venda, fotografo o contrato assinado e acho os dois pela busca da placa.

**Fase 6: Busca**
Busca unificada com pg_trgm e unaccent, resultados agrupados, HTMX.
Aceite: buscar "abc1d23", "ABC-1D23", "joao" e "123.456" encontra o que deve.

**Fase 7: Vendas, papéis e exportação**
Tela de vendas, papéis administrador/vendedor, exportação Excel.

**Fase 8: Produção**
Dockerfile de produção, gunicorn, storage S3, backups, restauração testada, README de deploy.

## 10. Fora do escopo do MVP

Não implementar: financeiro/contas a pagar, emissão de nota fiscal, integração com Detran ou consulta de placa, tabela FIPE, comissão de vendedor, anúncio em sites/marketplaces, agente de IA ou servidor MCP, app nativo. Se achar que algum é essencial, sugira, não implemente.

## 11. Qualidade de código

- Lógica de negócio em `services.py` de cada app, não em views nem em templates.
- Views finas, templates parciais para HTMX em pasta `partials/`.
- Testes obrigatórios para: validações, regras de status de negócio, cancelamento, permissões de papel, busca.
- Nomes de modelos, campos e variáveis em português, consistentes com esta especificação.
- README com: como rodar local, como rodar testes, como fazer deploy, como fazer backup e restaurar.

## 12. Em aberto (confirmar com o usuário final)

- Como ele registra hoje (papel, caderno, Excel). Se houver Excel, criar importação na Fase 7.
- Se ele usa mais celular ou computador.
- Se tem funcionário que vai usar o sistema.
- Volume aproximado de carros por mês.
- Texto definitivo dos contratos e valores padrão (multa, IPVA, prazos): advogado.
- Dados da loja para o cabeçalho do contrato (razão social, CNPJ, endereço).
- Comissão padrão de consignação e de intermediação.

Já confirmado: a loja trabalha das duas formas, às vezes dona do carro, às vezes intermediando.
