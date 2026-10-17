# MoneyFinder

[Read the MoneyFinder problem and product overview](docs/assets/MoneyFinder_Problem_Slide.pdf)

[![Watch the MoneyFinder demo](docs/assets/moneyfinder-intro.jpg)](https://youtu.be/ltOwx898b8c)

**▶ [Watch the demo video on YouTube](https://youtu.be/ltOwx898b8c)**

> Your business is leaving tax credits on the table. MoneyFinder learns how you operate from your data, finds the
> niche NY credits you qualify for, and fills the forms for you.

Built for small and medium-sized businesses (New York first) that don't have a tax team watching for credits, not for
large companies that already pay tax professionals to do this.

## MVP demo

```bash
make setup          # once: uv sync for research/business, company, legal and kb
make demo-seed      # once: the synthetic demo business, Gowanus Kettle Brewing Co. (14 employees, Brooklyn)
make demo           # web app on http://localhost:8000 (PORT=... to change; Google sign-in expects 8000)
make fill           # Anchor cloud browser fills a claim form from the SurrealDB dossier (live view opens)
```

**One-page run:** http://localhost:8000/live. Enter the demo email (`marisol@gowanuskettle.example`), and the page
shows each step as it runs: Gmail linked, then the email agent (Claude on Bedrock) and the web research agents in
parallel, the dossier stored in SurrealDB, the Anchor browser filling the form (live view embedded), and the
matched forms with the data that goes on them. About 35 seconds to the filled form. The Anchor browser fills the
official NY IT-636 PDF (tax.ny.gov) and the filled PDF is shown at the end. **Ready to file**
(http://localhost:8000/live/filed) shows four filled official forms for the demo business (IT-636, IT-212,
IT-643, IRS 8846; regenerate with `uv run --no-project --with pypdf --with httpx python form-filling/demo_forms.py`).
Architecture diagram: [docs/architecture.svg](docs/architecture.svg) / `.png`. The demo mailbox and the
demo business's web research are stored synthetic data; everything else runs live.

1. **Connect the business.** Sign in with Google (read-only Gmail) and enter the company domain, or skip sign-in and
   open a stored profile under **Company profiles** on the home page (`gowanuskettle.example`, the synthetic demo
   business; `themaincapital.com`; add more with `make company-research DOMAIN=...`).
2. **Company profile.** Public-data research (website, BBB, LinkedIn, NY Department of State, NYC Open Data, news,
   an LLM summary), every fact with its sources and confidence. See `research/company/`.
3. **Matched NY credits.** "Credits you may qualify for" matches the profile's NAICS code, industry, products and
   hiring/R&D/expansion signals to the niches in `research/legal/catalog/niches.toml`. Niche credits come first,
   fewest claimants first (data.ny.gov claim counts), then credits most employers can claim. Each shows why it
   matched and links to the program page and the official form PDFs (tax.ny.gov, irs.gov).
   CLI: `make legal-match DOMAIN=gowanuskettle.example`.
4. **Send path (Opportunity Wallet).** On a connected business page, **Open Wallet** searches unclaimed-property
   matches and tax-credit leads, then opens Form review → approve snapshot → browser fill (never auto-submits).
5. **Track path.** Claim-path progress and agency vs bank evidence live in the blue Track UI at `/track/`
   (`ui/domain.html` + `/api/*` on the same Flask port). `/unclaimed/` redirects to `/track/`. Mock portal at
   `/mock-portal/`.

6. **Dossier in SurrealDB.** Each business gets one form-ready `dossier.json` (best value per field, every fact
   with provenance, matched credits and forms, `missing_info` to ask the user). Load it into SurrealDB Cloud
   (ns `moneyfinder`, db `main`) and read it back with `fn::business_dossier`:
   ```bash
   make kb-ping && make kb-init                     # connection check; schema (safe to re-run)
   make dossier DOMAIN=themaincapital.com           # build research/company/data/<domain>/dossier.json
   make dossier-push ID=themaincapital.com          # or ALL=1; idempotent
   make dossier-get SLUG=themaincapital-com         # RETURN fn::business_dossier('themaincapital-com')
   ```
   The web app pushes each dossier it builds automatically (`KB_AUTO_PUSH=0` turns this off). The form filler
   reads it; see [docs/FORM_FILLER_HANDOFF.md](docs/FORM_FILLER_HANDOFF.md).
7. **Agentic form filling.** `make fill` opens an Anchor Browser cloud session (the live view opens so you can
   watch), loads the business's dossier from SurrealDB, fills the mock claim portal field by field, reads every
   value back, and stops before submit for the user's OK. Fields with no source value are marked "Needs your
   input", never guessed. About 10 seconds; see `form-filling/`.

Sponsor tools: Anthropic Claude on AWS Bedrock (reasoning, email facts, profile summary), Anchor Browser (agentic
form filling), Daytona (sandboxed browser agents for the mock portal), Arize (tracing and evals), SurrealDB (`kb/`
dossiers, programs and forms).

Tests: `make test` (research packages + unclaimed-funds pipeline), `make evals`.

## Unclaimed funds agent

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

# Track path UI + local API (possible funds, claim path, money evidence)
python3 -m src.server
# then open http://localhost:4173
# or from the Flask shell: http://localhost:8000/track/

# mock portal for Daytona / Anchor fill
open mock_portal/index.html
```

**Send** is the green Gmail/Wallet shell (`make demo`). **Track** is the blue claim-path UI: research/onboarding → matches → conflict-gated forms → sandbox submit → dashboard tracker → agency vs bank evidence → agent-memory trail. Demo state is JSON-backed (`data/moneyfinder-events.json`) and Surreal-ready.

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
- SurrealDB (`SURREAL_WS_URL`, `SURREAL_NAMESPACE=moneyfinder`, `SURREAL_DATABASE=main`, and a database-level user
  `SURREAL_USER`/`SURREAL_PASS`, or a database JWT in `SURREAL_TOKEN`; `kb/` reads these, `kb/.env` overrides)
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
