# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary (and currently only) user: the **owner of a small used-car dealership** ("loja de seminovos e usados"). He is non-technical — he does not know technical terms, gets lost in screens with many options, and abandons anything that looks complicated. He works largely alone.

- **Primary device: desktop.** He mostly works from a computer at the shop. *(Confirmed 2026-10-06 — this corrects `ESPECIFICACAO.md` §4, which leads with "mobile-first, test at 375px first.")*
- **Secondary device: phone**, used on the lot — cadastrar a car, photograph a signed contract, look something up. Mobile remains a real, required surface, not an afterthought.
- A **salesperson (`vendedor`) role exists in code** but is **not exercised yet** — the owner is the only active user today. *(Confirmed 2026-10-06; `ESPECIFICACAO.md` marks staff usage as `[SUPOSIÇÃO]`.)* Treat multi-user as a future state the role split must keep supporting, not a present requirement.

## Product Purpose

A management system for a small used-car dealership covering the full lifecycle: **estoque** (inventory), **pessoas** (people), **negócios** (deals: compra / venda / troca), **consignação**, **contratos em PDF**, and **busca** (search).

Problems it exists to solve, in the owner's priority order:
1. **Don't lose data** — today, info on cars, clients, and contracts gets lost.
2. **Find contracts** — purchase, sale, and trade.
3. **Find sales** — what was sold, to whom, when, for how much.
4. **Control inventory** — which cars are in the shop, what they cost, what they're listed for.

**Success criterion (owner's own words, from the spec):** he can, on his own and from his phone, register a car, record a sale with a photo of the contract, and find that contract months later by typing just the plate or the client's name.

## Positioning

Not a generic admin panel and not a marketplace listing tool. The differentiating stance: a dealership system a **non-technical owner can actually operate alone**, in **plain Brazilian Portuguese**, that **never loses data** (nothing is ever hard-deleted) and that **generates the real paperwork** (contracts + inspection terms as PDFs) from the deal itself. The deal model encodes a genuine domain distinction most tools flatten: the shop sometimes **owns** the car (`modalidade = propria`) and sometimes only **brokers** between private parties (`modalidade = intermediacao`, including selling a consigned car) — and the system's profit logic, contracts, and inventory rules all branch on that.

## Operating Context

- Real-world workflow: a car enters (bought, consigned, or just brokered), sits in **estoque**, and leaves via a **negócio** (venda/troca) that must produce a **signed contract** and an **inspection/delivery term (termo de vistoria)**.
- Contracts are a core artifact, not a feature: five models — **A** (loja buys), **B** (loja sells), **C** (trade with loja), **D** (consignação), **E** (intermediação between private parties). The system picks the model automatically from `tipo` + `modalidade` + presence of a consignação; the user never chooses a model.
- Deals run as **short, one-topic-per-screen steps** (whose car → who → which car → financing → values/payment/delivery → contract → review), with "save as draft" at any step.
- Phone capture is part of the ritual: photos are taken with the device camera (`accept="image/*" capture="environment"`), and documents are shared via the phone's native share sheet (e.g. WhatsApp).
- Deployment: Django app on Render (free tier, hibernates after ~15 min idle), Neon Postgres, private S3-compatible bucket (R2/B2) for photos & documents served via **signed, expiring URLs**, daily `pg_dump` backups via GitHub Actions.

## Capabilities and Constraints

**Confirmed capabilities:** vehicle & photo management (estoque, detalhe, câmera upload); people (pessoas) with quick + full cadastro and CPF/CNPJ validation; deals in both modalidades with status transitions inside DB transactions, cancellation that reverses status, and consignação repasse tracking; unified tolerant search (plate, model, make, person name, CPF/CNPJ, phone) via Postgres `unaccent` + `pg_trgm`; PDF contract + inspection-term generation (WeasyPrint); per-vehicle and per-person deal timelines; sales screen; admin/vendedor roles; Excel export (admin only).

**Hard product rules:**
- **Nothing is ever truly deleted.** "Excluir" in the UI means **arquivar** (archive). No delete is ever exposed. Default manager hides archived; a `todos` manager includes them.
- **The loja is never a Pessoa.** It is an implicit party when `modalidade = propria` and an intervening party when `modalidade = intermediacao`; shop data lives in configuration.
- Vehicles with `situacao = terceiro` never appear in estoque.
- A deal cannot generate a contract while required data is missing (e.g. CPF, km de entrega, registered-owner consent / `anuente`); the screen must say **exactly what's missing with a link to fill it**, never a generic error.
- Contract legal text is **provisional** — every clause is marked `<!-- REVISAR COM ADVOGADO -->` and the config screen warns it must be reviewed. Never present it as legally valid.
- Volume is **low (under ~15 vehicles/month)** — a small lot. *(Confirmed 2026-10-06.)* Lists stay short; search matters more than heavy pagination/filtering.

**Terminology (preserve exactly — these are the real product vocabulary, in pt-BR):** Veículo, Pessoa, Negócio (compra/venda/troca), ParteNegocio (papéis: vendedor, comprador, permutante, anuente), ItemNegocio, Consignação, modalidade (própria / intermediação), situação (próprio / consignado / terceiro), status (em_estoque, reservado, vendido, devolvido), estoque, repasse, arquivar.

**Explicitly out of scope (MVP):** financeiro/contas a pagar, nota fiscal, Detran/plate lookup, tabela FIPE, seller commission, marketplace listing, AI agent / MCP server, native app. Do not add these even if they seem useful.

**Undecided / to confirm with the end user (from spec §12):** how he records today (paper/notebook/Excel — if Excel, import may be added later); definitive contract text and default values (multa, IPVA, prazos — needs a lawyer); the shop's own data for contract headers (razão social, CNPJ, endereço); default consignação/intermediação commission.

## Brand Commitments

- **Name:** Sistema Bahia Car.
- **Accent color (binding, from spec §2/§6):** azul-petróleo (teal/petrol blue) — **one** accent color only.
- **Typeface (binding, from spec):** Inter.
- **Voice (binding):** plain Brazilian Portuguese, the way a person would actually speak — "Salvar", "Voltar", "Carro vendido", "Foto do contrato". **Never** system/DB jargon ("Registro", "Entidade", "Submeter", "Instância", "Erro 500").
- **Explicit anti-references (spec §6):** must not look AI-made or like a generic admin panel. Banned: purple/blue gradients, emojis in the UI, sparkle/star icons, glassmorphism, exaggerated shadows, everything over-rounded, marketing copy ("Gerencie seu estoque de forma inteligente!").
- Error messages must say **what to do**: "Essa placa já está cadastrada. Toque aqui para ver o carro."
- Brazilian formatting is binding: currency R$ 32.000,00, dates dd/mm/aaaa, plates formatted (ABC-1234 or ABC1D23).

## Evidence on Hand

- `ESPECIFICACAO.md` — the project's authoritative MVP spec (data model, screens, rules, phases). Source of truth for business rules.
- `CONTRATOS.md` — full contract text, blocks, and model-selection rules.
- `README.md` — stack, run, deploy, backup/restore.
- A **working, deployed-capable implementation** already exists (Django 5.2 + HTMX + Tailwind via standalone CLI, no Node/SPA; Postgres; templates under `templates/`). Recent commits show an active visual pass (sidebar, dashboard/painel, estoque, vendas, pessoas).
- **Absences future work must not fabricate:** no real testimonials, customers, pricing, or benchmarks exist. The shop's own header data and final legal contract text are **not yet confirmed** — do not invent them.

## Product Principles

1. **A non-technical owner must be able to do it alone.** If a screen needs explaining, it's wrong. Plain words, few options per screen, big obvious actions.
2. **Never lose data, never hard-delete.** Archiving, history, and recoverability are load-bearing, not nice-to-haves.
3. **Search and findability are the product's heart.** "Find the contract months later by typing the plate" is the success test everything else serves.
4. **The paperwork is the point.** Correct, complete, auto-selected contracts and inspection terms generated from the deal — with honest "what's missing" guidance — are a core deliverable, not a side feature.
5. **Honor the own/broker distinction.** Every deal, contract, and profit figure branches on `modalidade`; never flatten it.

## Accessibility & Inclusion

- Minimum **WCAG AA** contrast (spec §6).
- Body text minimum **17px on mobile**; large touch targets (buttons ≥ 48px tall) with always-visible text labels (icons only ever support text, never replace it).
- Correct mobile keyboards/masks (`inputmode="numeric"` for km, CPF, currency).
- Built for a **non-technical user** as a first-class accessibility constraint: no jargon, actionable errors, visible confirmation of every important action ("Venda salva").
- LGPD: personal data (CPF, endereço, documentos) is authenticated-only; files served via signed expiring URLs, never public.
