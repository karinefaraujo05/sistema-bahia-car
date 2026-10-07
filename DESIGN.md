---
name: Sistema Bahia Car
description: Calm, honest dealership software — cool paper, one steady petrol accent, nothing gets lost.
colors:
  fundo: "#f4f6f8"
  superficie: "#ffffff"
  borda: "#e6eaee"
  tinta: "#101828"
  tinta-suave: "#5b6675"
  petroleo-50: "#ecf6f7"
  petroleo-100: "#d2eaec"
  petroleo-200: "#a7d6da"
  petroleo-300: "#73b9bf"
  petroleo-400: "#43969f"
  petroleo-500: "#277a83"
  petroleo-600: "#1a6670"
  petroleo-700: "#16525c"
  petroleo-800: "#15424b"
  petroleo-900: "#12343c"
  sidebar: "#10303a"
  verde: "#2f7d46"
  verde-fundo: "#e7f3ea"
  ambar: "#9a5b00"
  ambar-fundo: "#f7eeda"
  cinza: "#64748b"
  cinza-fundo: "#eef1f4"
typography:
  display:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "normal"
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  pill: "9999px"
  field: "0.625rem"
  button: "0.75rem"
  panel: "0.875rem"
  card: "1rem"
spacing:
  xs: "0.5rem"
  sm: "0.75rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2rem"
components:
  button-primary:
    backgroundColor: "{colors.petroleo-600}"
    textColor: "{colors.superficie}"
    rounded: "{rounded.button}"
    padding: "0.75rem 1.375rem"
    height: "48px"
  button-primary-hover:
    backgroundColor: "{colors.petroleo-700}"
    textColor: "{colors.superficie}"
    rounded: "{rounded.button}"
  button-secondary:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.button}"
    padding: "0.75rem 1.375rem"
    height: "48px"
  button-secondary-hover:
    backgroundColor: "{colors.petroleo-50}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.button}"
  field:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.field}"
    padding: "0.625rem 0.875rem"
    height: "48px"
  card:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.card}"
  panel:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.panel}"
  action-card:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.panel}"
    padding: "1.125rem 1.375rem"
    height: "72px"
  sidebar-item:
    backgroundColor: "{colors.sidebar}"
    textColor: "#c3d1d4"
    rounded: "{rounded.field}"
    padding: "0.625rem 0.875rem"
    height: "44px"
  nav-link:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.tinta-suave}"
    rounded: "0.5rem"
    padding: "0.375rem 0.75rem"
    height: "44px"
  badge-success:
    backgroundColor: "{colors.verde-fundo}"
    textColor: "{colors.verde}"
    rounded: "{rounded.pill}"
    padding: "0.125rem 0.625rem"
  badge-warning:
    backgroundColor: "{colors.ambar-fundo}"
    textColor: "{colors.ambar}"
    rounded: "{rounded.pill}"
    padding: "0.125rem 0.625rem"
  badge-neutral:
    backgroundColor: "{colors.cinza-fundo}"
    textColor: "{colors.cinza}"
    rounded: "{rounded.pill}"
    padding: "0.125rem 0.625rem"
---

# Design System: Sistema Bahia Car

## Overview

**Creative North Star: "O Balcão de Confiança" (The Trust Counter)**

This is the unhurried dealership counter, rendered as software: the place where a non-technical shop owner handles real paperwork plainly and trusts that nothing he enters will ever get lost. The whole system is written to feel **calm, honest, and sure**. Cool paper-grey backdrops carry white surfaces that lift just enough to read as "a card you can pick up." A single deep petrol accent does all the pointing — it is the one voice in the room, never a chorus. There is no flash, no persuasion, no decoration that isn't doing a job; the brand lives in restraint and in the precision of small details (tabular figures, a hairline border, a shadow that deepens only when you reach for something).

Everything is sized for certainty over density. Body text starts at 17px, primary actions are at least 48px tall and always carry words, and color is used sparingly enough that when petrol *does* appear — on the active nav item, the primary button, a listed price — it means "this is the thing." The palette is sober and faintly warm; status is spoken in quiet green / amber / grey, never in alarm. The result reads as a well-kept ledger at a trusted counter, not a dashboard and emphatically not something generated by a machine.

This system has an explicit anti-reference, inherited as a binding brand commitment: it **must not look AI-made or like a generic admin panel.** Purple/blue gradients, emojis in the UI, sparkle/star icons, glassmorphism, exaggerated shadows, everything-over-rounded, and marketing copy are rejected outright.

**Key Characteristics:**
- Cool-paper canvas, white surfaces, one deep petrol accent used sparingly.
- Calm and literal: plain Brazilian-Portuguese labels, big sure buttons, generous text.
- Soft ambient shadow at rest; surfaces lift 1–2px only on hover.
- Status spoken quietly in green / amber / grey, never loud.
- Tabular numerals everywhere money and counts appear.
- A dark petrol sidebar frames a light, airy workspace.

## Colors

A sober, faintly-warm palette: cool neutral surfaces, near-black ink, one deep teal-petrol accent, and three muted status families.

### Primary
- **Deep Petrol** (`petroleo-600` #1a6670; hover `petroleo-700` #16525c): the single accent and the system's one voice. Primary buttons, listed prices, the user avatar, the active-tab fill, the mobile-menu toggle. A full 50→900 ramp exists, but the mid-to-deep steps carry the identity; **Petrol Mist** (`petroleo-50` #ecf6f7) is the near-white tint used for soft hover beds, the active-nav background, avatars, and info message panels.
- **Petrol Sidebar** (`sidebar` #10303a): the darkest, slightly desaturated petrol. Reserved exclusively for the left navigation rail — the one large dark field in the product, and also the browser `theme-color`.

### Neutral
- **Ink** (`tinta` #101828): primary text and headings — a deep cool near-black, never pure #000.
- **Soft Ink** (`tinta-suave` #5b6675): secondary text, metadata, captions, placeholder and inactive nav labels.
- **Cool Paper** (`fundo` #f4f6f8): the app background the white surfaces sit on.
- **Surface White** (`superficie` #ffffff): every card, panel, field, header, and the search dropdown.
- **Hairline** (`borda` #e6eaee): all borders and dividers — a cool, barely-there grey.

### Status (muted, never alarming)
- **Quiet Green** (`verde` #2f7d46 on `verde-fundo` #e7f3ea): healthy / in-stock / completed sales. The "Registrar venda" shortcut and the `em_estoque` badge.
- **Warm Amber** (`ambar` #9a5b00 on `ambar-fundo` #f7eeda): attention / pending — reserved pendente, consignação, repasses a pagar.
- **Neutral Grey** (`cinza` #64748b on `cinza-fundo` #eef1f4): inert / archival state and the discreet "Consignado" tag; also empty photo wells.

### Named Rules
**The One Voice Rule.** Deep petrol is the only accent in the system. It should touch well under ~10% of any screen — its rarity is what makes it read as "the thing to do." Never introduce a second accent hue; status colors are not accents and stay inside badges and icon chips.

**The No-Alarm Rule.** Status is informational, not emotional. Use the `*-fundo` tint as the field and the solid status color only for the text/icon on it. Never fill a large surface with a saturated status color.

## Typography

**Display / Body / Label Font:** Inter (with `ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial` fallback). One family does the whole job.

**Character:** Inter, kept quiet and professional. Headings are set at weight 650 with a gentle −0.015em tracking and balanced wrapping so they read as confident but never shouty; body is comfortable and generous. The defining typographic trait is **tabular numerals on by default** (`font-variant-numeric: tabular-nums`), so prices, plates, counts, and dates line up like a ledger.

### Hierarchy
- **Display** (650, 1.5rem/24px, lh 1.2, −0.015em): page titles (`h1.text-2xl`, e.g. "Início", "Estoque").
- **Headline** (650, ~1.125rem/18px, lh 1.2): section titles inside panels ("Vendas", "Últimos negócios").
- **Title** (600, 1rem/16px): card headings (vehicle make + model), list-row primary text.
- **Body** (400, 1.0625rem/17px, lh 1.6): the baseline everywhere — **17px minimum on mobile is a hard floor.** Form controls inherit this size.
- **Label** (500, 0.875rem/14px): metadata, captions, nav labels, badge text, chart axis labels; small supporting text drops to 0.75rem/12px for the quietest captions ("Há N dias na loja").

### Named Rules
**The Ledger Numeral Rule.** Tabular numerals stay on globally. Any money, plate, count, or date must align vertically across rows. Never switch a figure to proportional numerals.

**The Plain-Word Rule.** Type carries plain Brazilian Portuguese as a person would speak it ("Salvar", "Carro vendido", "Foto do contrato"). Never system/DB jargon ("Registro", "Entidade", "Submeter", "Erro 500"). This is a binding brand commitment, not a preference.

## Layout

A fixed **dark sidebar + fluid workspace** shell. On desktop (`md`+) the petrol sidebar is a static `16rem` (w-64) rail; below `md` it slides off-canvas behind a black 40%-opacity overlay, toggled from a sticky top header. The header is a `4rem` (h-16) sticky bar holding the global search field (max `36rem`) and the user identity cluster.

Content lives in a centered `main` capped at `max-w-6xl`, with responsive gutters (`px-4` → `sm:px-6` → `lg:px-8`) and `py-6` vertical padding. The spacing rhythm is an 8px-based scale expressed in rem (0.5 / 0.75 / 1 / 1.5 / 2rem); cards and panels sit on `gap-3` to `gap-6` grids. Grids are mobile-first single-column and step up by breakpoint (dashboard shortcuts `sm:grid-cols-2 lg:grid-cols-4`; estoque cards `sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`; dashboard body `lg:grid-cols-3` with a 2/1 split).

**Density is deliberately low.** Volume is small (a handful of cars a month) and the primary user is non-technical: prefer breathing room, few items per screen, and large targets over information density. Desktop is the primary surface, but every layout must still hold at 375px — mobile is a real, required surface (photographing contracts, quick lookups on the lot).

## Elevation & Depth

A **soft-shadow, reach-for-it** system. Surfaces are white cards resting on cool-paper with a gentle ambient shadow at rest; depth is calm, never dramatic. The single interaction grammar: on hover, an interactive surface **lifts 1–2px (`translateY`) and its shadow deepens from `sm` to `md`** — the UI responds to being reached for. Exaggerated shadows are explicitly banned.

### Shadow Vocabulary
- **Rest** (`--shadow-sm`: `0 1px 2px rgba(16,24,40,0.06), 0 1px 3px rgba(16,24,40,0.08)`): default elevation for cards, panels, fields, buttons, indicators — a quiet lift off the paper.
- **Raised** (`--shadow-md`: `0 2px 4px rgba(16,24,40,0.06), 0 8px 20px rgba(16,24,40,0.08)`): hover/active state for interactive surfaces and the open search dropdown.

### Named Rules
**The Reach Rule.** Elevation change is a response to intent. A surface deepens its shadow and lifts a pixel or two only on hover/focus; nothing floats dramatically at rest, and nothing animates elevation without a user gesture.

## Shapes

A soft-but-restrained radius language on a tiered scale: fields `0.625rem` (10px), buttons `0.75rem` (12px), panels / indicators / action-cards `0.875rem` (14px), content cards `1rem` (16px, rounded-2xl). Pills (`9999px`) are reserved for status badges, filter tabs, the "Consignado" tag, and avatars. Borders are a single hairline (`1px solid` Hairline #e6eaee) — every surface is defined by a thin cool border *plus* its soft shadow, never a heavy stroke. Icons are consistently Lucide-style line icons at `1.5px`–`2px` stroke, `currentColor`, sized 20–24px, always paired with a text label. **Nothing is over-rounded** (no fully-pill buttons or inputs); the tiered scale keeps corners gentle but legible as rectangles.

## Components

### Buttons
- **Shape:** gently rounded (0.75rem / 12px), `min-height: 48px`, inline-flex with centered content and a 0.5rem gap for an optional leading icon. Weight 600, always with a text label.
- **Primary (`.botao-primario`):** Deep Petrol (#1a6670) fill, white text, `shadow-sm`. **Hover:** darkens to `petroleo-700`, shadow → `md`, lifts 1px.
- **Secondary (`.botao-secundario`):** white fill, ink text, hairline border, `shadow-sm`. **Hover:** fills Petrol Mist (#ecf6f7), border shifts to `petroleo-200`.
- **Transitions:** 0.15s ease on background, box-shadow, border, transform.

### Fields (`.campo`)
- **Style:** white fill, hairline border, 0.625rem radius, `min-height: 48px`, inherits 17px body size. Search field adds a leading inline icon (`pl-10`).
- **Focus:** border shifts to `petroleo-500` with a 3px petrol glow ring (`box-shadow: 0 0 0 3px` petrol at 18%). A global `:focus-visible` adds a 2px petrol outline with 2px offset for keyboard users. Caret is petrol.

### Cards & Panels
- **Vehicle Card (`veiculos/partials/card.html`):** the signature content object. 1rem radius, white, hairline border, `shadow-sm`, overflow-hidden. A 16:9 cover photo (grey well + "Sem foto" fallback) sits above a 1rem body: title row (make + model) with a status badge, a metadata line (`ano/ano · cor · placa`), then a price row — **price set in Title size, bold, Deep Petrol (#16525c)** — with an optional grey "Consignado" pill, and a quiet "Há N dias na loja" caption. **Hover:** lifts 0.5px, shadow → md.
- **Panel (`.painel`):** generic content surface — white, hairline, 0.875rem radius, `shadow-sm`, typically `p-5`. Does not lift on hover (it's a container, not a target).
- **Action Card (`.cartao-acao`):** large dashboard shortcut — `min-height: 72px`, 0.875rem radius, leads with a rounded 2.75rem icon chip tinted to its meaning (petrol / green / amber). **Hover:** lifts 2px, border → `petroleo-200`, shadow → md.
- **Indicator (`.indicador`):** dashboard stat — white panel with a tinted square icon chip beside a bold 2xl figure and a soft-ink caption. Static (no hover lift).

### Badges & Chips
- **Status badge:** fully-pill, 0.875rem/14px medium text on a status tint — green (`em_estoque`), amber (`reservado`), grey (other). Tint field + solid-color text only.
- **Icon chip (`.chip` / `.indicador-icone`):** a rounded square (0.625–0.75rem) carrying a 20–24px line icon, background tinted to its status family. The recurring device for giving a row or stat a quiet color identity.
- **Avatar (`.avatar`):** circular initial, Petrol Mist field, `petroleo-700` text, weight 600.

### Navigation
- **Sidebar (`.sidebar-item`):** on the dark petrol rail — soft blue-grey labels (#c3d1d4) with a leading 20px line icon, 0.625rem radius. **Hover:** white text on a `white/8%` wash. **Active (`.sidebar-item-ativo`):** white text, `white/12%` wash, weight 600. Brand wordmark "Bahia Car" sits at the top in extrabold; "Sair" anchors the bottom above a `white/10` divider.
- **Top nav link (`.nav-link`):** soft-ink label, 0.5rem radius, ≥44px target. **Hover:** ink text on Petrol Mist. **Active (`.nav-link-ativo`):** `petroleo-700` text on Petrol Mist, weight 600.
- **Filter tabs (estoque):** pill-shaped. Selected = solid `petroleo-600` fill, white text; unselected = hairline border, white fill, ink text. A lighter secondary filter row uses Petrol-Mist-on-selected without borders.

### Alerts (`.aviso`) — status banners
- One component for every inline status banner, so radius and padding stay identical system-wide: 0.875rem radius, hairline tinted border, `0.75rem 1rem` padding, no shadow (banners are inline notices, not floating panels).
- **`.aviso-info`** (petrol): flash/confirmation messages ("Venda salva").
- **`.aviso-atencao`** (amber): attention/validation — provisional-contract warning, form errors, financing alerts, draft notices, the cancel-deal warning. Border softened to a light amber tint (not solid) to honor the No-Alarm Rule.
- **`.aviso-ok`** (green): success confirmations ("Dados completos para gerar contratos").

### Back-link (`.link-voltar`)
- The standard "voltar" affordance (shared partial `partials/voltar.html`): a drawn Lucide arrow-left (same 2px stroke as every other icon) + soft-ink label, darkening on hover. Replaces plain-text `←` arrows so the icon language stays consistent.

### File inputs (`.campo-arquivo`)
- Camera/document uploads: a styled `::file-selector-button` matching the secondary button (hairline, 0.625rem radius, petrol-mist hover) with a soft-ink filename. Always paired with a real `<label>` or `aria-label`.

### Search Dropdown (`.busca-dropdown`) — signature
- Empty by default (`:empty { display: none }`); when populated it becomes an absolutely-positioned white panel under the header search, 0.875rem radius, `shadow-md`, max-height 70vh scroll. The embodiment of the North Star's success test — find anything by typing a plate or a name — rendered as the product's most important interactive surface.

### Sales Chart (início) — signature
- A lightweight, dependency-free CSS bar chart: flex columns of `petroleo-500` bars with `rounded-t-md` tops, value label above, month label below. Honest and minimal — no chart library, no gridlines, no gradient fills.

## Do's and Don'ts

### Do:
- **Do** keep Deep Petrol as the only accent, under ~10% of any screen (The One Voice Rule). Use Petrol Mist (#ecf6f7) for soft hover beds and active-nav backgrounds.
- **Do** keep tabular numerals on for every figure — prices (R$ 32.000,00), plates, counts, dates (dd/mm/aaaa) must align across rows.
- **Do** make primary actions ≥48px tall and always carry a text label; icons only ever support text.
- **Do** define each surface with a hairline border *and* a soft `shadow-sm`, and lift it 1–2px to `shadow-md` only on hover (The Reach Rule).
- **Do** write every label and message in plain Brazilian Portuguese as a person would speak, and make errors say what to do ("Essa placa já está cadastrada. Toque aqui para ver o carro.").
- **Do** speak status quietly — status tint as field, solid status color for text/icon only.
- **Do** hold every layout at 375px; desktop is primary but mobile is a real surface.

### Don't:
- **Don't** use purple/blue gradients, emojis in the UI, sparkle/star icons, glassmorphism, or exaggerated shadows — these are binding brand rejections that make it look AI-made.
- **Don't** introduce a second accent color, or fill a large surface with a saturated status color (The No-Alarm Rule).
- **Don't** over-round: no fully-pill buttons or inputs. Pills are only for badges, filter tabs, and avatars.
- **Don't** drop body text below 17px on mobile, or ship an icon-only control without a text label.
- **Don't** use marketing copy ("Gerencie seu estoque de forma inteligente!") or technical jargon anywhere in the UI.
- **Don't** add drama to elevation — nothing floats dramatically at rest or animates its shadow without a user gesture.
