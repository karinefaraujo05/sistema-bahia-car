# Prompts de implementação — Sistema Bahia Car

Um prompt por Onda, prontos pra colar no agente de código **dentro do repo**. Baseados em `LEVANTAMENTO.md` e na auditoria estratégica de 26/10/2026.

**Decisões fechadas:**
- Onda 1 — API paga de placa: **implementar como adapter plugável** (busca interna + FIPE já; provedor pago opcional via env). Recomendados: APIBrasil (traz FIPE) ou SimplesAPI (~R$ 0,10/consulta). Credify só se precisar de dados do proprietário.
- Onda 2 — cadastro rápido de pessoa: **CPF obrigatório** (com validação de dígito + busca de duplicata).
- Onda 4 — hospedagem: **migrar** (Render → Hetzner/Dokploy; doc já existe em `MIGRAR-BANCO.md`/`PUBLICAR.md`).

**Regras gerais pra todos os prompts (não repetir dentro de cada um, mas valem sempre):**
- Não quebrar o padrão existente: `ModeloBase` (arquivar, não apagar), multi-tenant por empresa, managers `objetos`/`todos`, transações `@transaction.atomic` nos serviços.
- Manter mobile-first (Tailwind, cards, alvos de toque ≥ 44px). Nada de tabela larga.
- Preservar `select_related`/`prefetch_related` já corretos. Não introduzir N+1.
- Escrever/ajustar testes (`pytest`, `tests.py` de cada app) e rodar `ruff`.
- Textos de interface em português, linguagem simples (usuário leigo).

---

## ONDA 1 — Cadastro de carro: placa primeiro, FIPE como caminho principal, progressivo

```
Contexto: o cadastro de carro hoje é 1 tela com ~28 campos (VeiculoForm em veiculos/forms.py,
template templates/veiculos/form.html, view veiculos/views.py:novo/editar). A FIPE é só ajuda
opcional no topo (core/fipe.py + JS em form.html) e marca/modelo ainda são texto livre. Objetivo:
cortar a fricção de entrada mantendo a completude pro contrato.

Faça, nesta ordem:

1. PLACA PRIMEIRO + BUSCA INTERNA. Mover o campo placa pro topo do formulário. Ao preencher a
   placa (evento blur/htmx), consultar o próprio banco pelo manager `Veiculo.todos` (incluindo
   arquivados) na empresa atual. Se o carro já existe:
   - se ativo: avisar "esse carro já está cadastrado" com link pro detalhe;
   - se arquivado: oferecer "esse carro já passou pela loja" e pré-preencher o formulário com os
     dados dele (desarquivar no save).

2. FIPE COMO CAMINHO PRINCIPAL. Inverter a lógica: os selects encadeados tipo → marca → modelo →
   ano passam a ser o jeito padrão de preencher. marca, modelo, combustivel e ano_modelo viram
   campos preenchidos pela FIPE e readonly. Um link "não achei na FIPE" destrava esses campos como
   texto livre (mantém o comportamento atual como fallback). Reaproveitar core/fipe.py.

3. CADASTRO EM DUAS CAMADAS ("entra no estoque" vs "completa depois").
   - Campos pra salvar o carro (seção principal, sempre visível): placa, marca, modelo,
     ano_fabricacao, ano_modelo, cor, km, valor_anunciado. (~8 campos)
   - Seção colapsada "Documentação e condição": chassi, renavam, situacao,
     proprietario_registral, alienado (+ campos de alienação), tem_chave_reserva,
     avarias_declaradas, sinistro_declarado (+ descrição), valor_compra, observacoes.
   - O VeiculoForm deve permitir salvar sem chassi/renavam (já são blank=True no modelo — conferir
     que nenhuma validação nova os torna obrigatórios aqui).

4. AVISO DE PENDÊNCIA NO DETALHE. No template veiculos/detalhe.html, mostrar um aviso quando
   faltarem campos exigidos pelo contrato (ex.: "faltam chassi e renavam pro contrato", com link
   pra editar). Reaproveitar a lógica de ConfiguracaoLoja.campos_faltando()/campos_faltando_contrato
   (core/models.py:83-90, contratos/geracao.py:64-94): criar um método análogo em Veiculo, ex.
   `campos_faltando_contrato()`, e usá-lo tanto aqui quanto na checagem de geração de contrato.

5. CAMPOS CONDICIONAIS. Os 6 campos de alienação (credor_alienacao, saldo_devedor,
   parcelas_restantes, valor_parcela, dia_vencimento, parcelas_vencidas) só aparecem quando
   `alienado` está marcado; sinistro_descricao só quando sinistro_declarado. Fazer por JS
   progressivo (sem exigir JS pra salvar).

6. CONSULTA DE PLACA EXTERNA — ADAPTER PLUGÁVEL (opcional, desligado por padrão).
   Criar veiculos/consulta_placa.py com uma interface única `consultar_placa(placa) -> dict | None`
   e um provedor selecionável por env (ex.: CONSULTA_PLACA_PROVIDER = none|apibrasil|simplesapi).
   - Provedor "none" (default): não faz nada, retorna None.
   - Implementar apibrasil e simplesapi (REST/JSON, chave por env CONSULTA_PLACA_TOKEN), retornando
     marca/modelo/ano/cor/combustível/chassi quando disponíveis.
   - Expor no mesmo campo de placa: botão "buscar dados da placa" que, se houver provedor
     configurado, preenche os campos (sem sobrescrever o que o usuário já digitou).
   - SEMPRE com tratamento de erro: se a API falhar/timeout, mostrar "não consegui consultar,
     preencha à mão" e seguir — nunca quebrar o cadastro.
   - Documentar as envs novas em .env.example.

Aceitação: dá pra cadastrar um carro preenchendo ~8 campos; o resto fica numa seção colapsada; o
detalhe avisa o que falta pro contrato; a FIPE preenche e trava marca/modelo com escape manual; a
placa busca no próprio banco; alienação/sinistro só aparecem quando marcados; o adapter de placa
externo existe, está desligado por padrão e falha graciosamente. Testes + ruff.
```

---

## ONDA 2 — Wizards de negócio e cadastro de pessoa

```
Contexto: wizard em negocios/views.py (+ negocios/forms.py). Troca tem 5 telas e redigita valores
(troca_carro_loja → troca_valores). Passo "quem" usa EscolherPessoaForm/PessoaRapidaForm. PessoaForm
marca CEP como required (pessoas/forms.py:58) embora o modelo só exija nome. A checagem do que falta
pra pessoa no contrato só aparece ao gerar o contrato (contratos/geracao.py:_faltando_pessoa), depois
do negócio concluído.

Faça:

1. TROCA SEM REDIGITAÇÃO.
   - No passo troca_carro_loja, ao escolher o carro da loja, pré-preencher valor_loja com o
     valor_anunciado dele.
   - Trazer o valor do carro do cliente (valor_cliente) já pro passo 3 (troca_carro_cliente, junto
     do cadastro do carro), e pré-preencher valor_cliente no passo 4 (troca_valores).
   - Com isso, troca_valores vira uma tela de CONFIRMAÇÃO (campos já preenchidos, editáveis), não de
     digitação do zero. Ajustar TrocaValoresForm (negocios/forms.py:93) e as views troca_*.

2. PASSO "CARRO" MAIS CURTO. Compra e troca cadastram carro novo com o VeiculoForm completo. Depois
   da Onda 1, garantir que esse passo use a MESMA versão enxuta (placa+FIPE+essenciais, resto
   colapsado). Não duplicar o form — reusar o VeiculoForm já ajustado na Onda 1.

3. PASSO "QUEM": COMPLETAR PESSOA NA HORA. Quando a pessoa é escolhida no passo_pessoa, mostrar ali
   mesmo o que falta nela pro contrato (RG, endereço, estado civil, etc.) com botão "completar
   agora" (abre edição inline ou leva pra pessoas:editar e volta). Reaproveitar
   contratos/geracao.py:_faltando_pessoa como fonte única da verdade (extrair pra função reutilizável
   se preciso). Objetivo: resolver a pendência enquanto o cliente ainda está na loja.

4. CADASTRO RÁPIDO DE PESSOA COM CPF OBRIGATÓRIO.
   - PessoaRapidaForm (pessoas/forms.py:22) passa a incluir cpf_cnpj como OBRIGATÓRIO, com validação
     de dígito verificador (validar_cpf_cnpj já existe) e coerência tipo×documento.
   - Ao digitar o CPF, buscar duplicata (Pessoa.objetos na empresa) e, se já existir, carregar a
     pessoa existente em vez de criar outra (evita duplicata e adianta o contrato).
   - Campos finais do rápido: tipo, nome, cpf_cnpj, telefone.

5. PESSOA COMPLETA: SÓ NOME E CPF OBRIGATÓRIOS.
   - Tirar o required do CEP em PessoaForm (pessoas/forms.py:58) e de tudo que não for nome e
     cpf_cnpj. Deixar a cobrança de completude pro momento do contrato (que já existe).
   - Colocar cpf_cnpj como primeiro campo, com a mesma busca de duplicata do item 4.

Aceitação: troca não pede o mesmo valor duas vezes (passo final é confirmação); cadastro de carro no
wizard é o enxuto da Onda 1; ao escolher a pessoa o sistema mostra e deixa completar o que falta pro
contrato; cadastro rápido exige CPF válido e dedupe carrega pessoa existente; form completo de pessoa
só obriga nome e CPF. Testes cobrindo dedupe de CPF e pré-preenchimento da troca + ruff.
```

---

## ONDA 3 — Contrato: WhatsApp com anexo e editor no celular

```
Contexto: contratos/views.py. enviar_whatsapp só abre wa.me com texto (NÃO anexa o PDF). O editor de
contrato (templates/contratos/editar.html) usa textarea rows=16 em fonte monoespaçada. A tela de
"faltando" (contratos/faltando.html) já é boa.

Faça:

1. WHATSAPP COM O PDF ANEXADO (progressive enhancement).
   - No celular (PWA), usar a Web Share API com arquivo: navigator.share({ files: [pdf], title, text })
     pra abrir o WhatsApp já com o PDF anexado. Precisa de HTTPS (produção já tem) e do arquivo
     disponível pro JS (servir o PDF do contrato via a view baixar_pdf com ?inline, ou gerar um blob).
   - No desktop / navegador sem suporte a share de arquivo: manter o comportamento atual (link wa.me
     com mensagem de texto). Detectar suporte via navigator.canShare({ files }).
   - Não remover o fluxo atual; é o fallback. Testar no celular do dono (anotar no PR que precisa
     teste real em Android/iOS).

2. EDITOR DE CONTRATO AMIGÁVEL NO CELULAR.
   - Esconder o editor de texto atrás de um "editar texto" (details/summary já existe no template —
     garantir que venha fechado por padrão), já que o caso comum é só gerar e imprimir.
   - Trocar a fonte monoespaçada por fonte normal e deixar a altura automática (auto-grow) em vez de
     rows=16 fixo.

3. Manter a tela de "faltando" com links como está (com a Onda 2 ela quase não deve aparecer).

Aceitação: no celular, enviar por WhatsApp abre o app com o PDF anexado; no desktop continua como
hoje; o editor vem fechado, em fonte legível e altura automática. Testes do que for testável sem
navegador + ruff. No PR, instruções pra teste manual no celular.
```

---

## ONDA 4 — Lentidão, robustez e migração de hospedagem

```
Contexto: a lentidão sentida é provavelmente Render starter + Neon dormindo, mais do que código
(estimativa, não medido). A migração de hospedagem foi decidida como prioridade. Há também correções
de código baratas.

PRIORIDADE A — MIGRAÇÃO DE HOSPEDAGEM (Render → Hetzner/Dokploy).
- Seguir a documentação já existente no repo (MIGRAR-BANCO.md, PUBLICAR.md). Verificar o que está
  pendente: provisionar servidor Hetzner + Dokploy, mover o banco Neon pra perto (ou pra Postgres no
  próprio Dokploy), configurar bucket R2, ajustar envs e domínio.
- Validar que o Dockerfile/start.sh atuais rodam no Dokploy sem mudança (ou ajustar o mínimo).
- Checklist de corte: backup antes (view /backup/ já gera dump+mídia), DNS, HTTPS, variáveis de
  ambiente, smoke test de login/estoque/gerar contrato.
- NÃO apagar o Render até o novo ambiente estar validado.

PRIORIDADE B — CORREÇÕES DE CÓDIGO BARATAS (podem ir junto ou depois):
1. lembretes() roda 2x no painel inicial (core/views.py:122 chama lembretes, e
   core/context_processors.py também). Calcular uma vez por request (guardar em request) ou cachear
   por ~60s. Não divergir os números.
2. _vendas_por_mes (core/views.py:48-72) faz 6 counts. Trocar por 1 query com TruncMonth + annotate(
   Count) agrupando os últimos 6 meses.
3. Carros parados (core/views.py:_carros_parados:25-33 e core/agenda.py): hoje carrega todos os
   próprios em estoque e filtra em Python por dias_na_loja. Filtrar no banco:
   criado_em__date__lte = hoje - timedelta(days=DIAS_CARRO_PARADO).
4. Fotos (veiculos/services.py:21-48): validar tipo (MIME/extensão) e tamanho ANTES de abrir com
   PIL, e tratar exceção (arquivo corrompido não pode dar 500). Além disso, redimensionar no cliente
   antes do upload (canvas no JS do form) pra evitar timeout com foto grande de celular — mantendo o
   redimensionamento no servidor como garantia.
5. consignar (negocios/views.py): envolver a chamada a criar_consignacao() em try/except
   RegraNegocioError, mostrando mensagem amigável em vez de 500 (confirmar a linha exata).
6. Integrações externas sem fallback (core/fipe.py, consulta_cnpj em core/views.py, ViaCEP no JS):
   no mínimo mostrar "não consegui consultar agora, preencha à mão" em vez de falhar calado.

Aceitação: sistema rodando no novo host com smoke test passando e Render ainda de pé como rollback;
painel faz menos queries (lembretes 1x, vendas por mês em 1 query, carros parados filtrados no banco);
upload de foto valida e não derruba o request; consignar e as consultas externas falham com mensagem
amigável. Testes + ruff.
```

---

## Ordem sugerida de execução

1. **Onda 1** (maior ganho de fricção, isolada).
2. **Onda 2** (depende do VeiculoForm enxuto da Onda 1).
3. **Onda 4 Prioridade A** (migração) — pode rodar em paralelo, é operacional.
4. **Onda 3** e **Onda 4 Prioridade B** (polimento) por último.

Rodar um prompt por vez, revisar o diff (ou usar `/code-review`) antes de seguir pro próximo.
</content>
