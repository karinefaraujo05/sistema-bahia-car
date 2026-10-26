# AUDITORIA — descobertas durante as melhorias

Arquivo de anotações do que foi descoberto fora do escopo do item atual.
Não é o relatório de análise (esse é o `ANALISE-SISTEMA.md`).

---

## Item 1.1 — Medição do cold start (2026-10-18)

- `render.yaml:7` confirma `plan: free`, runtime Docker.
- URL de produção: `https://bahia-car.onrender.com` (lida em `manter-acordado.yml`).
- Medições de `/saude/`:
  - **Cold start: 76,6 s** (TTFB) — dyno do Render + banco Neon acordando juntos.
  - Quente: 0,69 s e 2,26 s em chamadas seguidas.
  - Home `/` quente: 0,33 s (302 → login).

### Descoberta: o "manter-acordado" não está prevenindo o cold start
- Os 76,6 s foram medidos às **11h43 (America/Bahia)**, que está **dentro da janela**
  de ping do `manter-acordado.yml` (a cada 10 min, 06h30–22h59 Bahia).
- Logo, o serviço **dormiu mesmo com o robô ativo**. Causa provável: o agendador de
  cron do GitHub Actions atrasa ou pula execuções em horários de pico (comportamento
  documentado do GitHub — não há garantia de pontualidade no `schedule`).
- **Implicação:** o ping não é cura confiável para a lentidão. A solução de verdade é
  a migração para uma hospedagem que não dorme (Bloco 1). O `manter-acordado.yml` só
  deve ser desligado (item 1.4) depois que a nova hospedagem estiver estável.

---

## Item 1.3 — Descoberta: `.env` local aponta para o banco de PRODUÇÃO (2026-10-18)

- O `.env` local contém `DATABASE_URL` com a credencial **real do Neon de produção**
  (usuário `neondb_owner`), em texto puro.
- `config/settings/dev.py` herda de `base.py`, que lê o banco de `env.db("DATABASE_URL")`.
  Logo, rodar `pytest` (que usa `settings.dev`, `pyproject.toml`) nesta máquina
  **conectaria na produção** e tentaria criar um `test_neondb` no Neon.
- **Risco:** testes locais mexendo em infra de produção; credencial de dono do banco
  exposta em arquivo local.
- **Ação recomendada (pra depois, fora do item atual):** usar o Postgres local do
  `docker-compose.yml` para testes (`.env.docker` já tem `DATABASE_URL` local), e
  manter a credencial de produção fora do `.env` de desenvolvimento. O `.env` está no
  `.gitignore` (não foi/será commitado), mas continua exposto no disco.
- Por isso a suíte **não foi executada** no item 1.3 (mudança só de config de infra,
  nenhuma linha de código do app alterada).

---

## Item 1.3 — FECHADO: migração para Render Starter (2026-10-18)

- A dona pagou/cadastrou cartão no Render e confirmou no dashboard que o plano
  virou **Starter** (always-on). O `plan: starter` do `render.yaml` foi aplicado.
- Medição depois do Starter (16h49 Bahia): `/saude/` em **0,68–1,87 s**, home em **0,32 s**.
- Comparado ao cold start de **76,6 s** no plano Free → a lentidão/"tela de espera"
  acabou. Starter não dorme, então não há mais cold start.
- Ressalva honesta: as medições acima são "quentes" (seguidas). A garantia de
  "não dorme" vem do próprio plano Starter (confirmado no dashboard), não de um
  teste de 20 min ocioso (o robô manter-acordado ainda pinga e mascararia o ócio).
- **Pendente:** item 1.4 — desligar `manter-acordado.yml` após ~1 semana estável
  no Starter (aí o robô vira inútil).

---

## Item 2.4 — Divergência no limite de "carro parado": 60 vs 90 dias (2026-10-18)

- O item 2.4 pede destacar no painel "carros parados há mais de **60 dias**".
- Mas a **agenda** já usa **90 dias** (`core/agenda.py:19`, `DIAS_CARRO_PARADO = 90`)
  para o mesmo conceito de alerta de carro parado.
- Fiz o painel a **60 dias** (constante `DIAS_PARADO_PAINEL` em `core/views.py`),
  conforme pedido. Resultado: o painel avisa mais cedo (60) e a agenda mais tarde (90).
- **Pendente da usuária (em TAREFAS-PARA-VOCE.md):** decidir se quer unificar os dois
  no mesmo número (ambos 60, ambos 90, ou manter 60 no painel / 90 na agenda).

---

## Item 4.1 — Contagem de toques do fluxo "Vendi um carro" (2026-10-18)

Caminho medido: estoque → cliente **já cadastrado** → PDF gerado. Selects contam
como 2 toques (abrir + escolher). Campos opcionais do pagamento não contados.

| Passo | Toques |
|---|---|
| Home → "Vendi um carro" | 1 |
| Quem (select pessoa + Continuar) | 3 |
| Carro (select veículo + Continuar) | 3 |
| Pagamento (valor + select forma + Continuar) | 4 |
| Revisão → Confirmar | 1 |
| Detalhe → Gerar contrato | 1 |
| Abrir/editar + Baixar PDF | 2 |
| **TOTAL** | **~15** |

**Meta do item 4.5: menos de 10.** Onde dá pra cortar (itens 4.2–4.4):
- Quem: busca com sugestão enquanto digita (HTMX) em vez de select → ~1 toque.
- Pagamento: forma como botões grandes (1 toque) em vez de select (2).
- Revisão/PDF: botão "Gerar contrato e baixar PDF" direto da revisão pouparia 2–3 toques
  (hoje: Confirmar → Gerar contrato → Abrir/editar → Baixar PDF).

### Recontagem (item 4.5, 2026-10-18) — depois dos itens 4.2/4.3/4.4

| Passo | Antes (4.1) | Agora |
|---|---|---|
| Home → "Vendi" | 1 | 1 |
| Quem | 3 | 2 (busca HTMX: digita + toca sugestão, que já avança) |
| Carro | 3 | 3 (NÃO alterado no Bloco 4) |
| Pagamento | 4 | 3 (forma de pagamento virou botão) |
| Revisão → Confirmar | 1 | 1 |
| **Venda concluída** | **12** | **10** |
| Gerar contrato + pegar PDF | 3 | 2 |
| **Até o PDF** | **15** | **~12** |

**Meta "<10 até o PDF" NÃO batida ainda.** Faltam dois pontos fora do escopo dos
itens 4.2–4.4:
1. **Passo do carro** ainda é um `select` (3 toques). Aplicar a MESMA busca tap-to-pick
   da pessoa (clicar no carro já seleciona e avança) → ~1 toque. Economia: ~2.
2. **Cauda do PDF**: "Confirmar venda" poderia já gerar o contrato, e um "Baixar PDF"
   direto no detalhe (em vez de passar pelo editar) economizaria ~1–2 toques.

Com (1) e (2), o fluxo até o PDF cairia para **~8 toques** (meta batida). Recomendado
oferecer à usuária como um "4.6" rápido (mesmo padrão já pronto do passo 'quem').

### Recontagem FINAL (item 4.6 feito — passo do carro virou cards clicáveis)

| Passo | Toques |
|---|---|
| Home → "Vendi" | 1 |
| Quem (busca + toca sugestão) | 2 |
| Carro (toca no card) | 1 |
| Pagamento (valor + botão forma + Continuar) | 3 |
| Revisão → Confirmar venda | 1 |
| **VENDA CONCLUÍDA** | **8** ✅ (meta <10 batida) |
| Gerar contrato + pegar PDF | ~2 |
| **Até o PDF** | **~10** |

A **venda em si caiu de 12 → 8 toques** (meta <10 batida com folga). Até o PDF ~10
(a única cauda restante é gerar contrato + baixar; um "Baixar PDF" direto no detalhe
tiraria mais 1, mas é opcional). Item 4.6 não estava na lista original — feito com
autonomia por ser o que faltava pra cumprir a meta do 4.5, mesmo padrão já aprovado.
