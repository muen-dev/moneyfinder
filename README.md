# MoneyFinder

B2B agent that helps NYC businesses find **New York State unclaimed funds**, prepare accurate claim forms, require authorized approval, submit through a sandbox/mock portal, and track **evidence** for agency approval vs bank deposit.

> Demo uses **synthetic** data. Not legal or tax advice. Claiming NY unclaimed funds is free via the state.

## What this team owns

1. **How we handle money status** — agency evidence ≠ bank confirmation  
2. **Agentic form accuracy** — provenance, conflicts, approval, Daytona read-back  

Other developers may supply richer datasets; this repo owns the agent memory, pipelines, and UI for the claim path.

## Quick start

```bash
cp .env.example .env
# fill secrets locally — never commit .env

python3 tests/test_pipeline.py
python3 evals/run_evals.py

# run the domain-first UI + local API
python3 -m src.server
# then open http://localhost:4173

# legacy static demo UI
open ui/index.html
# mock portal for Daytona
open mock_portal/index.html
```

## Architecture

See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md), plus:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/STATUS_MODEL.md](docs/STATUS_MODEL.md)
- [docs/EVIDENCE_MODEL.md](docs/EVIDENCE_MODEL.md)
- [docs/DEMO_SLICE.md](docs/DEMO_SLICE.md)
- [docs/MONEY_PATH.md](docs/MONEY_PATH.md)
- [docs/AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md)
- [docs/UI_SPEC.md](docs/UI_SPEC.md)
- [docs/NY_DATA_IMPORT.md](docs/NY_DATA_IMPORT.md)

```text
Business UI → Agent tools → Bedrock (reasoning)
                ↓
         SurrealDB events + dates
                ↓
    Mock NY search → Form review → Daytona mock portal
                ↓
   AgencyStatusProvider → BankTransactionProvider (mock)
                ↓
              Arize evals
```

**Anchor is not used for NY search.** Plaid/SimpleFIN are optional future bank adapters.

## Repo layout

| Path | Purpose |
|------|---------|
| `docs/` | Team plan, money path, agent, UI, GitHub workflow |
| `contracts/` | B2B input JSON schema |
| `schemas/surreal/` | SurrealDB schema with datetime events |
| `src/` | Search, forms, pipeline, providers, agent tools |
| `ui/` | B2B product UI |
| `mock_portal/` | Synthetic NY claim portal |
| `evals/` | Synthetic profile evaluations |
| `tests/` | End-to-end pipeline checks |

## Collaboration

- Branch: never push straight to `main`  
- Details: [docs/GITHUB_WORKFLOW.md](docs/GITHUB_WORKFLOW.md)  
- Ownership: [docs/TEAM_OWNERSHIP.md](docs/TEAM_OWNERSHIP.md)

## Environment

Copy [.env.example](.env.example). Required for full demo:

- AWS Bedrock (`AWS_BEDROCK_MODEL_ID`, region, temporary credentials)
- SurrealDB (`SURREAL_WS_URL`, `SURREAL_NAMESPACE=moneyfinder`, `SURREAL_DATABASE=main`, **database JWT**)
- Daytona API key
- Arize API key + **ARIZE_SPACE_ID** from the Arize dashboard
- `ARIZE_PROJECT_NAME=moneyfinder` (chosen name; created on first export)
- ElevenLabs optional (voice data entry only)
- Company research providers: `TAVILY_API_KEY`, `FIRECRAWL_API_KEY`, `NIMBLE_API_KEY`

Company research loads `research/company/.env.local` first and falls back to
the root `.env`, so provider secrets do not need to be duplicated.

Verify Arize credentials via OTLP (not GraphQL):

```bash
python3 -m pip install -r requirements.txt
python3 scripts/arize_smoke_test.py
```

Then check Arize AX → Space → project `moneyfinder` for the smoke span.

## Status vocabulary (do not invent new meanings)

`MATCH_FOUND` → `FORM_READY` → `USER_APPROVED` → `SUBMITTED` → `CLAIM_RECEIVED` → `PROCESSING` → `APPROVED` → `PAYMENT_ISSUED` → `PAYMENT_CONFIRMED`
