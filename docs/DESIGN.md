# DESIGN.md — MoneyFinder

The visual contract for anything built in this repo. Every value below was read out of shipped code
(`style.css`, `ui/index.html`, `ui/composer/app/globals.css`) — not invented. If you change a token,
change it here in the same PR.

**Verified:** 2026-10-26 against `feat/agent-composer` @ `2e557f5`.

---

## 0. Pick a system before you draw anything

This repo currently carries **two** complete design systems, because the product app and the prototypes
were built in different seasons. They do not share a palette. Do not blend them on one screen.

| | **System A — Product app** | **System B — Track / prototype** |
|---|---|---|
| Source of truth | `research/business/src/business_research/web/static/style.css` + Jinja templates | `ui/index.html`, `ui/domain.html`, `ui/composer/app/globals.css` |
| Runs on | Flask, server-rendered (`make demo` → :8000) | static HTML; Next 16 composer |
| Feel | calm, institutional, green | bolder, navy + gold, big type |
| Type | `system-ui` stack, 15px/1.55 | Bricolage Grotesque + Instrument Sans |
| Where it ships | `/`, `/live`, `/businesses/*`, `/companies/*`, `/credits`, `/dossier`, `/wallet/*`, `/track` | prototypes only (navy Track flow, agent composer) |

**Rule:** new screens inside the Flask app use **System A**. Standalone one-pagers, decks and
prototypes use **System B**. A one-pager never gets shipped inside the Flask templates, and navy never
appears on a Flask screen.

**Open decision (needs an owner, not an agent):** the two systems should collapse into one. Until they
do, state which system you are building in at the top of the PR.

---

## 1. System A — product app (green)

### Tokens

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#F5F7F4` | `#0E1411` | page |
| `--fg` | `#14211B` | `#E6ECE8` | text |
| `--muted` | `#5F6B65` | `#94A19A` | secondary text, labels, captions |
| `--card` | `#FFFFFF` | `#151C18` | cards, inputs, header |
| `--line` | `#E1E6E0` | `#253029` | hairlines, borders |
| `--accent` | `#0F7B55` | `#4CC38A` | primary action, links, status |
| `--accent-hover` | `#0B6646` | `#63D19B` | hover |
| `--accent-fg` | `#FFFFFF` | `#062014` | label on accent |
| `--accent-soft` | `#E3F2EA` | `#143225` | tints, chips, progress bg |
| `--danger` | `#B42318` | `#F2877C` | errors, destructive |
| `--err-bg` | `#FDECEA` | `#3D1B18` | error flash |
| `--warn` | `#A15C07` | `#F0B45A` | queued / attention |
| `--warn-bg` | `#FFF3E0` | `#3A2B12` | warn tint |
| `--shadow` | `0 1px 2px rgb(20 33 27 / .04), 0 4px 16px rgb(20 33 27 / .04)` | `none` | cards only |

Dark mode is driven by `prefers-color-scheme` — no toggle.

### Type & layout

- Body `15px/1.55 system-ui`; `code` `13px ui-monospace`.
- `h1` 24px / 1.25 / −0.015em — `.hero h1` **clamp(28px, 5vw, 42px)** / −0.025em.
- `h2` 16px · `h3` 14px · `.lead` 16px muted, max 680px · `.small` 13px · `.fine` 13px muted.
- `.eyebrow`: 13px/700, uppercase, `+0.06em`, accent.
- Container `max-width: 1000px`, `main` padding `28px 16px 48px`; header/footer full-bleed.
- Radii: card **14px**, inner panels/rows **11–12px**, button/input **9px**, pill **999px**.
- Gaps in use: 6, 8, 10, 12, 14, 16, 18, 22, 28, 32.

### Components

| Component | Spec |
|---|---|
| `.top` header | flex, wrap, `16px 24px`, bottom hairline, white bg. `.brand` 17px/750 with `.mark` 26px accent square, radius 7px. `.tagline` 13px muted. `.nav` right-aligned, 14px/600. |
| `.card` | white, 1px line, radius 14, padding 22, `--shadow`, `margin-bottom: 18px`. Variants `.narrow` (640px), `.center`. |
| `.primary` | accent bg, white label, 9px radius, 600, `9px 16px`. Disabled = 60% opacity. |
| `.gsi` | Google sign-in: white, `#DADCE0` border, 10px radius, real multicolour G logo (from `_macros.google_logo()`). |
| `.steps` | inline progress: 22px numbered dots, done = accent fill, current = accent ring + `--fg` 650. Always `aria-current="step"`. |
| `.how` | 3-up auto-fit grid (min 220px) of white cards with 26px `--accent-soft` number dot. |
| `.status` / `.conf` / `.pill` / `.tag` | 999px tints. `done`/`high` = accent-soft; `queued`/`running`/`medium` = warn-bg; `failed`/`low` = err or line. `.tag.rare` = warn. |
| `.fact` + `.glance` | auto-fill grid (min 220px): uppercase 12px label, 600 value, then `.meta` row with `.conf` + `.source` links. This is the provenance pattern — every fact carries its source. |
| `.src` | source-checked chip: 8px dot (`found` accent / `failed` danger / `empty` grey) + label. |
| `.credit` | credit card: `.credit-head` (name + `.tag`), `.why` bullet list of reasons, `.credit-links` row of `.small-btn`. |
| `.table-wrap` / `table` | 9px 8px cells, header 13px muted/600, row hairlines, `nowrap` except `.profile`. |
| `.timeline` | left 3px accent rule, 12px inset. `.mem` = 2px accent rule for agent memory. |
| `.log` / `pre#log` | mono 13px on `--bg`, pre-wrap, 480px max height. The live-run activity feed. |
| `.spinner` / `.bar` | 14px accent ring (800ms); 4px indeterminate bar (1.4s). Both stop under `prefers-reduced-motion`. |
| `.flash` | 10px 14px, radius 10; `.ok` = ok-bg, `.error` = err-bg. |
| `.opp` / `.field-table` | wallet opportunity row; editable field table where `tr.needs` = warn-bg row. |

### Page compositions

- **`/` landing:** `.hero` (eyebrow → clamp h1 → `.lead` → `.gsi` + `.fine`) → `.how` 3-step grid →
  optional *Company profiles* `.biz-list` → optional *Connected businesses* `.biz-list`.
- **`/live` one-page run:** h1 → email form → `#steps` ordered list → *Activity* `pre#log` →
  hidden-until-done sections: filled PDF (`<iframe height=900>`), agentic browser
  (`<iframe height=560>`), data tables, screenshot.
- **Company / business:** `.company-head` → `.steps` → `.glance` facts → `.signals` → `.sources-row` →
  `.credit-list` → `.table-wrap` → `.danger-zone`.
- **Wallet:** `.wallet-hero` → `.wallet-search` → `.opp-list` → `.field-table` → `.timeline` → `.mem`.

---

## 2. System B — Track prototype (navy + gold)

### Tokens

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#EEF3F8` | `#061326` | page |
| `--card` | `#FFFFFF` | `#0F2441` | surfaces |
| `--ink` | `#0B2545` | `#EAF1F8` | text |
| `--mut` | `#5B6F88` | `#9DB1C8` | secondary |
| `--line` | `#D5E0EC` | `#1D3658` | borders |
| `--gold` | `#FFC53D` | same | **primary action** |
| `--sea` | `#14A98A` | `#3DD6B5` | positive, money |
| `--sea-soft` | `#DDF5EE` | `#0E3A34` | positive tint |
| `--coral` | `#E8553F` | same | conflict, destructive |
| `--coral-soft` | `#FDE6E1` | `#42201C` | conflict tint |
| `--hero` | `#0B2545` | `#0F2441` | dark hero panel |
| `--hero-ink` | `#F4F8FC` | same | text on hero |
| `--doc` | `#FFFDF6` | `#14213A` | "paper" form surface |
| `--sidebar` | `#061326` | `#040B16` | domain page rail |
| `--wait` | `#C99200` | same | pending |

Composer adds `--shadow: 0 18px 40px rgb(11 37 69 / 10%)` (dark: `rgb(0 0 0 / 35%)`).

### Type

- Display: **Bricolage Grotesque** 500/700/800, `-0.02em`, `line-height: 1.05`.
- Body: **Instrument Sans** 400/500/600.
- Hero: `clamp(36px, 6vw, 64px)`, max 14ch (index) · `clamp(30px, 5vw, 52px)`, max 18ch (composer).
- `.sub`/`.note` 13–14px `--mut`; `.t` 28px/800; numerals 36–48px 800 in `--sea`.

### Shape & space

- Container **1040px** (index) / **1080px** (composer), 20px gutters.
- Radius: hero **32px** (30 composer), shell **24px**, card **20px** (composer `.mf-card` 14px),
  input **14–16px**, button **16px** (composer 11–12px), pill **999px**, brandmark **10px**.
- Motion: screen enter `0.25s ease` (opacity + 6px rise); spinner 800ms; nothing over 250ms.
- Breakpoints: 640 (compact), 900 (single column).

### Components

| Component | Spec |
|---|---|
| `.mf-topbar` | brand + meta, 18px vertical. `.mf-brandmark` 32px `--hero` square radius 10, gold glyph. |
| `.mf-pill` | 11px/700, 5px 11px, 999px. `.is-live` sea-soft / `#0C6B56`; `.is-offline` coral-soft / `#9A3F2D`. |
| `.mf-hero` / `.hero` | `--hero` panel, radius 30–32, padding `clamp(28px,4.4vw,46px)`; body copy `#B9CBE0`; `.mf-hero__sun` = 150px gold glyph at 18% opacity. |
| `.chips` / `.mf-hero__chips` | 999px, 11.5px/600, hairline + 10% white fill. |
| `.card` / `.mf-card` | `.card` = white, 18px radius, 14px pad, checkbox rows (`.item`) with 22px check. `.mf-card` = 14px radius, `#FBFDFF`, title 13px/700 + `.mf-tag`. |
| `.mf-tag` | 9px/800 uppercase, `+0.1em`. Default `#4A6CF0`/`#EEF2FF`; `--tool` `#9A6B00`/`#FFF5D6`; `--result` `#0C6B56`/sea-soft; `--guard` `#8F3A28`/coral-soft. |
| `.btn` / `.mf-btn` | `.btn` = gold, 16px radius, 14px 20px, 600; `.ghost` = hairline; `.r` = coral-soft. `.mf-btn` = hero bg, 11px radius, 1.5px border; `--ghost` transparent. |
| `.mf-composer` | white shell, 24px radius, `--shadow`, 16–24px pad; `.mf-composer__eyebrow` 10.5px/800 uppercase `+0.16em`. |
| `.mf-quick` | pill chips, 12.5px/600; hover = gold border + `#FFF8E1`. |
| `.mf-input` | 16px radius, `#FBFDFF`, textarea 15px auto-grow, `.mf-send` 40px gold square radius 12. |
| `.mf-reply` / `.mf-user` | bubbles: reply = hero navy, radius `18 18 18 6`; user = gold, radius `18 18 6 18`. |
| `.mf-approval` | `--doc` surface, 1.5px hero border, 16px radius. **The approval gate is the point of the composer — never auto-dismiss it.** |
| `.paper` | claim-form preview: `--doc`, 12px radius, 20px pad, `0 10px 30px rgb(11 37 69/.12)`; labels 12px muted with source `em`; `.flag` inputs get coral border + tint. |
| `.log` | hero bg, `#CFE0F2` mono 13px/1.7, `min-height: 180px`, `<em>` in gold. |
| `.tag` / `.chip` / `.mini` | `.tag` 12px tint (`.w` coral, `.d` line); `.chip` 13px/600 pill; `.mini` 99px pill, 13px/700, `--ink` on `--bg`. |
| `.toast` | fixed bottom 28px, `--ink` bg, `--bg` text, 99px radius. |
| `.bar` + `.bar i` | 10px track, sea fill. Accuracy bars on the trace screen. |
| `.acct` | hero navy panel, 44px number, radius 22. |

### Page compositions

- **Track landing (`ui/index.html`):** header (brand + *Start business search*) → hero → 3 `.stat`
  cards (B2B / Proof / $0) → "How money status works" 3 steps (Match → Approve & submit → Evidence) →
  disclaimer `.note`.
- **Claim path:** profile form → scanning steps (`.tick` spinner → ✓) → matches with `.amt` and
  confidence tag → form review (conflict must be cleared before *Send*) → sandbox submit `.log` →
  evidence timeline (`.acct` + `.act` rows) → accuracy `.bar`s.
- **Composer (`ui/composer`):** topbar → `.mf-hero` → `.mf-composer` (eyebrow, quick prompts, input,
  hint) → stream (user bubble → event cards → reply → approval → citations) → `.mf-foot`.
- **Domain research (`ui/domain.html`):** `.sidebar` rail + main column, progress bars, claim detail.

---

## 3. Rules that apply to both systems

**Money semantics — non-negotiable.** An estimate is never "money". An agency receipt is never a
payment. Only a matched bank row is money arrived, and in the demo it is labelled **demo deposit**.
Every number on a page carries its badge: `Estimate`, `Found`, `Approved`, `Paid`, `Demo`.

**Copy.** Second person, sentence case, no hype. "Possible funds", not "your money". Sign-in is
described as *read-only* and *disconnect deletes everything* wherever it appears.

**Accessibility.** Visible focus ring (2px accent, or `--focus #FFC53D` on dark). Body ≥15px, contrast
AA. Status is never colour-only — always a text label. `prefers-reduced-motion: reduce` kills spinners,
bar slides and screen transitions. Real `<button>`/`<a>`; iframes get a `title`.

**Dark mode.** Both systems have one via `prefers-color-scheme`. Test on it — the Flask app has no
toggle, so a screen that assumes white will ship broken.

**Never.** No stock photos of handshakes. No invented dollar totals. No "guaranteed". No emoji as
iconography in System A. No purple-gradient SaaS template.

---

## 4. If you are building the one-pager

Use **System B**. Single page, in this order — every section maps to a class above:

1. **Header** — `.mf-topbar`: wordmark + one pill (`is-live` = "synthetic demo") + primary CTA.
2. **Hero** — `.mf-hero`: real headline (`Find the tax credits and grants your business is leaving on
   the table.`), 2-line subhead, chips (`public data only` · `every fact sourced` · `approval before
   filing`), one gold CTA. No illustration.
3. **How it works** — three numbered cards: *Connect Gmail → Add your domain → Get a sourced profile*.
   Copy from `templates/index.html`; it is already written and sourced.
4. **Proof** — a `.fact`-style grid showing one real claim with `.source` links and a `.conf` badge.
   This is the differentiator; do not replace it with a logo wall.
5. **Sample output** — `.paper` (filled form preview) or `.log` (agent run). Show the artifact.
6. **Evidence / accuracy** — `.bar` rows, labelled *sample — replace with live Arize*.
7. **Close** — CTA + the disclaimer: *Synthetic demo. Not tax or legal advice. Estimates are not money
   received.*
8. **Footer** — 3 items, matching `base.html`: read-only Gmail · data stays on this machine ·
   disconnect deletes everything.

Requirements: works at 390px and 1440px, one accent action above the fold, no scroll-jacking, real
links, `prefers-reduced-motion` respected, and no component that implies money has been received.

---

## 5. Known drift (fix or ignore, but know it)

- `docs/CONTRACT.md` §design tokens points at `ui/static/css/design.css` — **that file does not exist**.
  The tokens live in the two stylesheets cited at the top of this document.
- `ui/index.html` labels a screen "Arize-style accuracy" with hardcoded 96/100/100 bars; the card itself
  says *replace with live Arize*.
- `ui/index.html`'s demo force-injects a ZIP conflict (`11202`) on the first form so the conflict UI is
  always visible. Do not copy that into production code.

## 6. Provenance

Read from: `research/business/src/business_research/web/static/style.css` (313 lines),
`templates/{base,index,live}.html`, `_macros.html`, `ui/index.html` (272), `ui/domain.html` (1181),
`ui/composer/app/globals.css` (152), `ui/composer/app/page.tsx` (229), `ui/composer/app/layout.tsx`,
`docs/UI_SPEC.md` (95). Token values were lifted verbatim; nothing here is a guess about intent.

The separated `hackathon-lab` spec (Finix-derived, navy/Manrope, Claims Desk wording) is kept at
[`docs/reference/DESIGN-hackathon-lab.md`](reference/DESIGN-hackathon-lab.md) for comparison only. It is
**not** this repo's design system and its labels ("Find my benefits") do not match this product.
