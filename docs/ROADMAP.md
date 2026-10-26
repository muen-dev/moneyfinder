# Roadmap — from demo to a real business

Ordered by dependency, not by ambition. No dates: a three-person team that publishes dates it cannot
keep loses the only thing it has. Each item names an owner and a **done test** so "done" is checkable.

The demo is real code and synthetic data. Everything below is the gap between that and charging a
business money to run it.

---

## Phase 0 — One repo, one surface (in progress)

| # | Item | Owner | Done when |
|---|---|---|---|
| 0.1 | Import `app/` from hackathon-lab with provenance | Thuy | `make test` green on moneyfinder with `app/` present |
| 0.2 | Retire hackathon-lab (archive, not delete) | Thuy | archived banner live; `archive/2026-10-26` tag pushed |
| 0.3 | Collapse the two Flask surfaces (`app/` + `research/business/.../web/`) | Richard | one process serves `/`, `/live`, `/dashboard`; the other deleted |
| 0.4 | Real founder access: Kenan on moneyfinder, CODEOWNERS live | Thuy | all three push a branch the same day without asking |

## Phase 1 — Identity and tenancy (blocks everything customer-facing)

| # | Item | Owner | Done when |
|---|---|---|---|
| 1.1 | Real sign-in (Google OAuth already exists for Gmail; the product uses demo auth) | Kenan | a new user signs in, gets their own business, sees only their data |
| 1.2 | Tenant isolation on every query and every export | Richard | a test proves business A cannot read business B's dossier, ledger or packet |
| 1.3 | Session/secret handling: no secrets in fixtures, tokens revocable | Richard | `git grep` finds no credential; disconnect revokes at Google and deletes locally |

## Phase 2 — Real data instead of fixtures

| # | Item | Owner | Done when |
|---|---|---|---|
| 2.1 | Real NY unclaimed-funds ingest (see `docs/NY_DATA_IMPORT.md`) replacing `src/search/adapter.py` synthetic hits | Richard | a real name search returns real records with `as_of` |
| 2.2 | Real credit eligibility, cited: each program carries source URL + `as_of` (pattern already in `app/services/eligibility.py` and `fixtures/programs.json`) | Thuy | every program card links an official page fetched this run |
| 2.3 | Real form fill: official blanks, typed values, read-back verification (partly exists: `pdf_fill`, `fixtures/forms/*.pdf`) | Kenan | a filled IT-636 is byte-verified against the approved field set |
| 2.4 | Replace the Harbor Studio / Gowanus fixtures with one demo business named consistently | Thuy | one synthetic business, one name, everywhere |

## Phase 3 — Money semantics and compliance (blocks launch)

| # | Item | Owner | Done when |
|---|---|---|---|
| 3.1 | Status machine frozen and versioned (`docs/MONEY_PATH.md`, `docs/STATUS_MODEL.md`) | Richard | every screen renders only these states; a contract test fails on a new string |
| 3.2 | Evidence rails: estimate / found / approved / paid / demo, impossible to conflate in the UI | Thuy | an adversarial review cannot find one screen that implies received money |
| 3.3 | Privacy policy, terms, data-retention actually implemented (not just claimed in a footer) | Thuy + Richard | "disconnect deletes everything" is testable and tested |
| 3.4 | Legal review of the claim we make (filing on a business's behalf, agency submission) | 👤 founders | written opinion on file |

## Phase 4 — Operate it

| # | Item | Owner | Done when |
|---|---|---|---|
| 4.1 | Durable database (SurrealDB is already the pipeline's store; the demo uses JSON + a Redis shim) | Richard | server restart loses nothing |
| 4.2 | Backups + restore drill | Richard | restore from last night's backup, timed, in a doc |
| 4.3 | CI: `make test` on every PR, no CI today | Thuy | red CI blocks merge |
| 4.4 | Monitoring: PRISM traces already emit; add error alerting and a daily job check | Richard | a broken run pages someone within 15 minutes |
| 4.5 | One deployment story (the hackathon used Vercel + Redis; `Procfile`/`render.yaml` are shims) | Richard | `make deploy` or equivalent, documented, reproducible |

## Phase 5 — Business decisions (no code)

Founders only, not an agent's call: pricing and who pays, what we legally are (entity), what we promise
in writing, and whether we submit filings ourselves or hand the packet to the business. Record each in
`docs/DECISIONS.md` when it lands.

---

## Deliberately not on this list

- More screens. The 33 that exist are more than enough to prove the product.
- A second design system. There are already two; collapsing them is Phase 0.3.
- New agents or models before Phase 2 — the bottleneck is data truth, not model capability.
