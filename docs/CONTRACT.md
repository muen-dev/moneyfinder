# Interface Contract — MONEY TALKS 2

**Frozen at 12:55.** Changes require a team-thread announcement + a `CONTRACT.md` update + ack from both consumers. No silent shape changes after 13:00.

**Rule:** every UI screen must render from `fixtures/api/*.json`. The live API is an enhancement, not a prerequisite. `?fixture=1` forces fixture mode.

---

## 1. Run + steps (PRISM session mirror)

One back-office run = one `run_id` = one PRISM `session_id`.

```json
{
  "run_id": "backoffice-run-it643-001",
  "status": "running|done|failed",
  "steps": [
    {"name": "gmail_scan", "status": "pending|running|done|failed", "started_at": "ISO", "ended_at": "ISO"}
  ]
}
```

Demo step order (12):
`gmail_scan → extract_facts → extract_purchases → categorize_ledger → reconcile_ledger → program_candidates → agency_fetch → eligibility_extract → match_score → form_prep → human_approve → build_accountant_packet`

---

## 2. Endpoints

All JSON, `Content-Type: application/json`, served by the Flask app (`src/server.py`). `GET /api/health` returns `{ok:true}`.

| Method | Path | Request | Response | Owner |
|---|---|---|---|---|
| POST | `/api/run` | `{mode:"demo"}` | `{run_id}` | Richard |
| GET | `/api/run/{run_id}` | — | Run (above) | Richard |
| POST | `/api/demo/reset` | — | `{ok:true}` | Richard |
| GET | `/api/onboarding/profile` | — | ProfileBundle | Richard |
| GET | `/api/ledger?year=2025` | — | LedgerBundle | Richard |
| GET | `/api/ledger/exceptions` | — | Exceptions | Richard |
| POST | `/api/ledger/packet` | `{year:2025}` | Packet | Richard |
| GET | `/api/applications` | — | `{applications:[Application]}` | Richard |
| GET | `/api/applications/{id}` | — | `{application, events[], evidence[]}` | Richard |
| POST | `/api/applications/{id}/transition` | `{to_status, actor, note}` | `{application}` | Richard |
| GET | `/api/eligibility` | — | `{verdicts:[Verdict]}` | Richard |
| GET | `/api/voice/summary` | — | `{text}` | Richard/P1 |

Errors: `{"error": {"code": "...", "message": "..."}}` with a 4xx/5xx status; the UI shows a non-blocking toast and keeps the last fixture data.

---

## 3. Shapes

### ProfileBundle

```json
{
  "profile": {
    "id": "demo-gowanuskettle",
    "legal_name": "Gowanus Kettle Brewing Co. LLC",
    "entity_type": "LLC",
    "state": "NY",
    "naics": "312120",
    "headcount": 14,
    "address": {"street": "417 Sackett Street", "city": "Brooklyn", "state": "NY", "zip": "11231"},
    "tax_year": 2025,
    "consent": true
  },
  "facts": [
    {"key": "headcount", "value": "14", "source_kind": "email", "source_ref": "synthetic-gk-001",
     "quote": "12 employees paid … 14 employees at the end of 2025", "confidence": 0.95, "requires_confirmation": false}
  ],
  "conflicts": [
    {"field": "headcount", "profile_value": "14", "email_value": "12", "source_ref": "synthetic-gk-001",
     "status": "open|resolved|deferred", "options": ["Use 14", "Use 12", "Ask me"]}
  ]
}
```

### LedgerBundle

```json
{
  "summary": {
    "year": 2025,
    "revenue_cents": 214000000,
    "expense_cents": 143730000,
    "capital_cents": 22800000,
    "payroll_cents": 50300000,
    "tips_cents": 14860000,
    "reconciled_delta_cents": 0,
    "missing_receipts": 6,
    "duplicates": 2
  },
  "transactions": [
    {"id": "txn_2025_0042", "date": "2025-07-28", "vendor": "ProBrew Equipment",
     "description": "Canning line — 24-head filler/seamer", "amount_cents": 18650000,
     "direction": "purchase", "category": "capital_assets", "tax_treatment": "capitalized",
     "payment_account": "Chase ...4410 (equipment financing)",
     "source_message_id": "synthetic-gk-0xx",
     "source_quote": "invoice total $186,500.00, placed in service July 28, 2025",
     "confidence": 0.98, "needs_receipt": false, "duplicate_of": null, "status": "verified"}
  ]
}
```

`category` ∈ `payroll|payroll_taxes|cogs_ingredients|cogs_packaging|rent|utilities|insurance|software|professional_fees|marketing|repairs|licenses|travel|capital_assets|other`.
`tax_treatment` ∈ `expense|capitalized|needs_review` (a flag for the accountant, not advice).
`direction` ∈ `purchase|sale`.

### Exceptions

```json
{
  "duplicates": [{"transaction_id": "txn_...", "duplicate_of": "txn_..."}],
  "missing_receipts": [{"transaction_id": "txn_...", "vendor": "...", "amount_cents": 12345}],
  "delta_cents": 0
}
```

### Application

```json
{
  "id": "app_it643",
  "program_id": "nys_hire_a_veteran",
  "program": "Hire a Veteran Credit",
  "form": "IT-643",
  "agency": "NYS Department of Taxation and Finance",
  "amount_estimate_cents": 1507500,
  "status": "MATCH_FOUND|FORM_READY|USER_APPROVED|SUBMITTED|CLAIM_RECEIVED|PROCESSING|APPROVED|PAYMENT_ISSUED|PAYMENT_CONFIRMED|NEEDS_DOCS|REJECTED|STOPPED_BY_USER",
  "next_action": "Upload DD-214 and sign",
  "deadline": "2026-01-15",
  "expected_by": "2027-02-01",
  "evidence_count": 2
}
```

Desk column mapping:
`FOUND = MATCH_FOUND + FORM_READY` · `IN PROCESS = USER_APPROVED + SUBMITTED + CLAIM_RECEIVED + PROCESSING + NEEDS_DOCS` · `APPROVED = APPROVED` · `PAID = PAYMENT_ISSUED + PAYMENT_CONFIRMED` (visually distinct).

### Verdict

```json
{
  "program_id": "nys_hire_a_veteran",
  "program": "Hire a Veteran Credit",
  "verdict": "eligible|needs_info|not_eligible|expired",
  "reasons": ["Two veterans hired in 2025", "NY employer"],
  "questions": [],
  "source_url": "https://www.tax.ny.gov/...",
  "as_of": "2026-10-17",
  "confidence": 0.9
}
```

### Packet

```json
{
  "packet_id": "pkt_2025_001",
  "year": 2025,
  "status": "prepared_for_review",
  "files": [
    {"name": "02_summary.xlsx", "url": "/api/ledger/packet/pkt_2025_001/02_summary.xlsx", "kind": "xlsx"},
    {"name": "03_ledger.csv", "url": "/api/ledger/packet/pkt_2025_001/03_ledger.csv", "kind": "csv"}
  ],
  "open_questions": ["§179 vs bonus depreciation on the canning line", "..."],
  "disclaimer": "Prepared for professional review. Not filed. Not tax advice."
}
```

---

## 4. Fixtures (Richard commits by 12:55)

`fixtures/api/profile.json` · `ledger.json` · `applications.json` · `eligibility.json` · `packet.json` · `run.json`

Each fixture file contains the exact response body above. UI client: `fetchJson(path, {fixture: true})` → loads `/fixtures/api/<name>.json` instead of the API. `?fixture=1` in the URL forces fixture mode for the whole app.

---

## 5. PRISM emitter (Richard implements, Thuy consumes dashboard)

```python
# src/observability/prism.py
with prism_run(session_id, agent_id="moneyfinder-backoffice"):
    prism_step(step_name, tool=tool_name, status="ok", latency_ms=940,
               input_summary="…", output_summary="…")
```

- One trace/step per model or tool call; `step_name` must match §1 exactly.
- Attach `model`, `prompt_version`, `cost_usd`, `status` as metadata.
- No raw PII in payloads; summaries only.
- Env: `PRISMTRACE_API_KEY`, `PRISMTRACE_PROJECT_ID`, `PRISMTRACE_HOST`.

---

## 6. Environment

```bash
MODEL_PROVIDER=nicrron            # default; bedrock fallback
NICRRON_API_KEY=
NICRRON_BASE_URL=https://api.nicrron.ai/v1
NICRRON_MODEL=nicrron/auto
PRISMTRACE_API_KEY=
PRISMTRACE_PROJECT_ID=6e1051f7-8dce-498f-9846-d6acaa087737
PRISMTRACE_HOST=https://api.prism.blockconvey.com
ELEVENLABS_API_KEY=               # P1 only
```

`.env` is local and gitignored. `.env.example` carries names only.

---

## 7. UI routes + owners

| Route | Screen | Owner | Fixture |
|---|---|---|---|
| `/onboarding` | connect → scan → profile → conflicts → consent | Thuy | `profile.json` |
| `/desk` | four columns, detail, exceptions, reconciliation | Kenan | `applications.json` |
| `/books` | summary, ledger table, exceptions, packet | Kenan | `ledger.json`, `packet.json` |
| `/` | redirect to onboarding or desk | Kenan | — |

Design tokens: `ui/static/css/design.css` (Thuy). UI shell: `ui/index.html` (Kenan). No one else edits those files without the owner.

---

## 8. Non-negotiables

- Synthetic data only: `.example` domains, `00-` EIN, 555-01xx phones.
- No real agency submission; mock portal only. Human approval before any submit.
- Money semantics: identified ≠ approved ≠ paid; `PAYMENT_ISSUED` is not a deposit.
- Packet says **"Prepared for professional review. Not filed. Not tax advice."**
- Never commit `.env`, keys, real personal data, or large video files.
