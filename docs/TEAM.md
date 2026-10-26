# Team — three founders

MoneyFinder / FindMoney is worked by three people. This file is the authority on **who owns what**;
`CODEOWNERS` enforces the paths, this file explains the lanes.

| Person | GitHub | Lane | Owns in repo |
|---|---|---|---|
| **Thuy Pham** | [@thuyqpham](https://github.com/thuyqpham) | Design system, product surface, research + data, docs | `docs/`, `research/`, `ui/` design tokens, DESIGN.md, PRISM/observability copy |
| **Richard (Jeremiah)** | [@thetradingdoc](https://github.com/thetradingdoc) | Agent runtime, pipeline + status machine, persistence, infra | `src/`, `contracts/`, `schemas/`, `evals/`, `Makefile`, deploy |
| **Kenan** | [@kenwon22](https://github.com/kenwon22) | App UI, onboarding, books/run-history/settings, demo + pitch | `ui/`, `mock_portal/`, product screens, demo video |

**Every founder has push access to every repo path.** Ownership means "default reviewer and the person
who decides", not "only person allowed to touch".

## Decision rights

| Decision | Who decides | Who must agree |
|---|---|---|
| Visual language, tokens, copy tone | Thuy | — |
| Status machine, evidence rules, data contracts | Richard | — |
| Screen flow, interaction detail | Kenan | Thuy (design), Richard (states it consumes) |
| New dependency, new service, schema change | whoever needs it | one other founder in the PR |
| Anything that touches money semantics (estimate vs paid) | Thuy + Richard | both |
| Pricing, legal entity, contracts, hiring | all three | unanimous |

## Handoffs that have bitten us before

1. **Schema before durable events.** Richard merges a schema change before anyone writes code that
   persists against it.
2. **Status labels come from `docs/MONEY_PATH.md`.** A screen never invents a status string.
3. **Design tokens change in `docs/DESIGN.md` in the same PR** as the CSS change.
4. **One runtime on stage, one runtime in prod.** Do not demo from a second app.

## Access

All three need, on `muen-dev/moneyfinder`: push access, and PR review. Kenan's access previously existed
only on `muen-dev/hackathon-lab` (now retired) — **invite him before archiving that repo** or he loses
the only repo he could read.

```bash
gh api -X PUT repos/muen-dev/moneyfinder/collaborators/kenwon22  -f permission=push
gh api -X PUT repos/muen-dev/moneyfinder/collaborators/thetradingdoc -f permission=admin
gh api -X PUT repos/muen-dev/moneyfinder/collaborators/thuyqpham  -f permission=admin
```

## What is still demo-only

Until the roadmap items in [ROADMAP.md](ROADMAP.md) land: sign-in is a demo auth, data comes from
fixtures, and every money figure is synthetic. Nothing in this repo has touched a real agency portal or
a real dollar. Keep it that way until the compliance section of the roadmap is closed.
