> **Reference only — not this repo's design system.** Copied verbatim from [`muen-dev/hackathon-lab` → DESIGN.md](https://github.com/muen-dev/hackathon-lab/blob/main/DESIGN.md) (commit `68dd7fcf`, 2026-10-17), the project that split off from this repo. The live spec is [`docs/DESIGN.md`](../DESIGN.md). This file is kept because it shows a different direction (Manrope, Finix-derived, black/white + pastel) and a landing-page composition worth comparing against. Its reference screenshots (`docs/proofs/finix-hero.jpg`, `docs/proofs/finix-full.jpg`) stay in `hackathon-lab` and are not in this repo. Its labels come from the MONEY TALKS 2 **Claims Desk** concept ("Find my benefits") and do not match this repo's tax-credit product.

# DESIGN.md — MoneyFinder Claims Desk

**Reference:** [Finix — Fintech, Banking & Finance Framer template](https://finix-template.framer.website/)
**Role of the reference:** visual DNA only (type, color, spacing, component shapes). This is not a pixel-for-pixel clone of Finix, and its content/brand is not reused.

## 1. Direction

Calm, confident fintech. White canvas, near-black type, soft pastel light, oversized Manrope headlines, pill actions, and flat 16px cards. Generous vertical rhythm. No shadows, no glossy gradients, no nested cards, no emoji.

| Token | Value | Use |
|---|---|---|
| `--ink` | `#0E0E0E` | headings, primary text, primary buttons |
| `--ink-2` | `#3A3A3A` | secondary text |
| `--muted` | `#6F6F6F` | captions, labels |
| `--line` | `#E8E6E1` | hairlines, input borders |
| `--paper` | `#FFFFFF` | page background |
| `--wash` | `#FAF9F6` | alternate section background |
| `--lavender` | `#FAF7FF` | card tint |
| `--lavender-strong` | `#D5C9F8` | gradient blob |
| `--peach` | `#FFF6F1` | card tint |
| `--peach-strong` | `#FFD5BF` | gradient blob |
| `--mint` | `#F2FBF8` | card tint |
| `--mint-strong` | `#CCF6EA` | gradient blob |
| `--success` | `#1F6B4A` | approved / paid-confirmed |
| `--warning` | `#8A5B00` | pending / attention |
| `--danger` | `#A83E2C` | missing / conflict |

**Type:** Manrope (Google Fonts), fallback Inter/system.
- `display`: 96–100px / 0.95 / 600 / -3px (hero)
- `h1`: 56px / 1.05 / 600 / -2px
- `h2`: 40px / 1.2 / 600 / -1px
- `h3`: 27px / 1.2 / 600
- `body`: 16px / 1.55 / 400
- `small`: 14px; `caption`: 12px / 600 / uppercase tracking .08em

**Spacing:** 4, 8, 12, 16, 24, 32, 48, 64, 96, 130. Section padding 96–130px desktop, 64px mobile. Container max 1200px, 24px gutters.

**Radii:** pill 999px (buttons), card 16px, input 12px, chip 999px.
**Borders:** 1px `--line`; no shadows. Dark sections are `#0E0E0E` with white text.
**Motion:** 180–240ms ease-out; opacity + 8px rise; respect `prefers-reduced-motion`.

## 2. Components

### `public-nav` (landing/auth)
- Logo left (black wordmark, no badge), links centered (16px Manrope 600, `--ink`), CTA right.
- Sticky, white, no border until scroll; height 76px.

### `primary-button`
Pill, `--ink` background, white label, 16px/600, padding 14px 24px, radius 999px. Hover: `#2A2A2A`. Disabled: 40% opacity.
```html
<a class="btn primary">Find my benefits</a>
```

### `ghost-button`
Pill, transparent, 1px `--line`, `--ink` label. Hover: `--wash`.

### `gradient-hero`
White canvas with three absolutely-positioned radial blobs:
- lavender `rgba(213,201,248,.8)` top-right
- peach `rgba(255,213,191,.75)` left
- mint `rgba(204,246,234,.8)` bottom-right
Blur 0 (the gradient is already soft), `border-radius: 50%`, `pointer-events: none`.
Content: eyebrow, 96px display headline (max 14ch), 18px subhead, action row (primary + ghost), trust line.

### `mock-panel`
White 16px card with a thin `--line` border, 24px padding, containing a compact UI preview (claims pipeline / stats). Used in hero and feature sections. No drop shadow.

### `feature-card`
16px radius, tinted background (`--lavender` / `--peach` / `--mint`), 30px padding, 12px icon-free label, `h3` 27px, 16px body. One idea per card.

### `stat-card`
White or tinted, 16px radius, 24px padding: caption label, 40px number, 14px note. Used for $ identified / in process / approved / paid.

### `benefit-card`
White 16px card, 24px padding, 1px border. Top row: program name + fit score pill. Body: agency, description, “Why this fits you” with a mint/lavender highlight, estimated amount, deadline, source link. Footer: `primary-button` “Fill this form”.
Hover: translateY(-2px), border `#CFC8BC`, 180ms.

### `form-preview`
Left: a paper-like panel (white, 1px border, 16px radius) with agency/form header and a list of `form-row`s. Right: approval card.
`form-row`: label 12px caption; value 16px; source chip 11px; confidence; missing rows have `--danger` left rule and a “Needs you” chip.

### `wizard-steps`
Three-step progress: numbered dots (24px) connected by 1px line; active dot `--ink`, complete dot `--success`, upcoming `#D9D6D0`. Label under each: “Inbox”, “Benefits”, “Form & submit”.

### `spinner`
24px ring, 2px `--line` track, `--ink` head, 800ms linear; plus an agent log (three lines max) that updates. Reduced motion: static text.

### `status-chip`
Pill 11px/700 uppercase; variants: found (`#F2F1EF`), in-process (lavender), approved (mint + success), paid (ink + white), missing (`--peach` + danger), expired (gray).

### `progress-card`
Mint-tinted 16px card with 48px check circle, 27px “Submitted”, confirmation id in mono, vertical step list with completed dots, next check, and `primary-button` “Go to dashboard”.

### `banner`
Slim top strip, `--lavender` background, 12px/700 ink text: “Synthetic demo — not tax advice. Estimates are not money received.”

## 3. Page compositions

- **Landing:** public-nav → gradient hero with mock claims panel → 3 feature cards (Connect inbox / Find benefits / Approve & track) → dark band with the money-semantics statement → CTA band → footer.
- **Auth:** gradient-hero background, centered 420px white card, email input, primary button, tiny demo note.
- **Onboarding:** top wizard bar + step dots; centered 720px column for consent/loading; 960px for profile/benefits/form; persistent banner.
- **Dashboard:** existing Claims Desk restyled with the same tokens (white topbar, Manrope, pill buttons, tinted stat cards, 16px pipeline cards).

## 4. Accessibility & rules

- Body text ≥16px, contrast AA. Never rely on color alone: status chips include text.
- Focus ring: 2px `--ink` offset 2px.
- All buttons are real `<button>`/`<a>`; no decorative buttons.
- Mobile: single column < 900px, 24px gutters, display 56px, h2 32px.
- `prefers-reduced-motion`: no transforms, no spinner rotation (static “Working…” text).
- Do not copy Finix copy, logo, illustrations or layout 1:1; use only the visual language above.

## 5. Provenance

Reference captured 2026-10-17 at 1728px: Manrope, hero 100px/600/-3px, h2 40px, h3 27px, body 16px, `#0E0E0E`, radial gradient blobs `rgba(213,201,248,.8)`, `rgba(255,213,191,.75)`, `rgba(204,246,234,.8)`, cards 16px radius / 30px padding, pills 50px radius, sections 130px padding. Screenshots: `docs/proofs/finix-hero.jpg`, `docs/proofs/finix-full.jpg` (compressed references).
