# Interface Contract — Moneyfinder (MONEY TALKS 2)

**Frozen at 12:55.** Product baseline: [`MONEY_TALKS_2_MASTER.md`](MONEY_TALKS_2_MASTER.md). Changes require a team-thread announcement + this file + ack from both consumers.

**Rule:** every UI screen must render from `fixtures/*.json` in fixture mode. Live API is an enhancement, not a prerequisite. `?fixture=1` forces replay; the UI labels it `demo-only`.

**Global rules:** all rows scoped by `business_id`; money in integer cents; evidence IDs immutable; no endpoint sends email, writes Gmail, files, modifies transactions or submits to a third party; every response in demo mode carries `synthetic: true`.

---

## 1. Analysis run + steps (PRISM session mirror)

One analysis = one run = one PRISM `session_id`.

```json
{
  "run_id": "run_case002_v1",
  "case_id": "case_002",
  "version": "v1",
  "status": "queued|running|succeeded|failed|partial",
  "started_at": "ISO",
  "ended_at": "ISO|null",
  "error": null,
  "telemetry": "ok|pending|failed",
  "prism_url": null,
  "steps": [
    {"tool": "search_mail", "status": "queued|running|succeeded|failed", "started_at": "ISO", "ended_at": "ISO", "error": null}
  ]
}
```

Tool order (8; ≥7 substantive executions):
`search_mail → fetch_messages → extract_attachments → load_transactions → retrieve_checklist → compare_evidence → generate_recommendations → compose_review_package`

---

## 2. Endpoints

| Method | Path | Request | Response | Owner |
|---|---|---|---|---|
| GET | `/api/health` | — | `{ok, mode}` | Richard |
| POST | `/api/demo/reset` | — | `{ok}` | Richard |
| GET | `/api/cases` | — | `{cases:[Case]}` | Richard |
| GET | `/api/cases/{case_id}` | — | `{case, requirements[], actions[]}` | Richard |
| GET | `/api/inbox?case_id=&q=&category=` | — | `{messages:[Message]}` | Richard |
| GET | `/api/messages/{message_id}` | — | `{message, attachments[]}` | Richard |
| GET | `/api/transactions?case_id=` | — | `{transactions:[Transaction], summary}` | Richard |
| POST | `/api/transactions/import` | CSV upload or `{rows[]}` | `{imported, skipped, errors[]}` | Richard |
| GET | `/api/checklist?case_id=` | — | `{checklist, requirements[]}` | Richard |
| POST | `/api/analysis/run` | `{case_id, mode:"live|replay"}` | `{run_id}` | Richard |
| GET | `/api/analysis/runs/{run_id}` | — | Run (above) | Richard |
| GET | `/api/analysis/runs/{run_id}/findings` | — | `{findings:[Finding], requirements[]}` | Richard |
| GET | `/api/next-year?case_id=` | — | `{recommendations:[Recommendation]}` | Richard |
| POST | `/api/next-year/{id}/accept` | `{owner?, due_date?}` | `{recommendation, task}` | Richard |
| POST | `/api/next-year/{id}/dismiss` | `{reason}` | `{recommendation}` | Richard |
| GET | `/api/tasks?case_id=` | — | `{tasks:[Task]}` | Richard |
| PATCH | `/api/tasks/{id}` | `{owner?, due_date?, status?}` | `{task}` | Richard |
| GET | `/api/package?case_id=` | — | `{package_id, markdown, preview}` | Richard |
| GET | `/api/package/{package_id}/download` | — | `text/markdown` file | Richard |
| GET | `/api/integrations/status` | — | `{integrations:[Integration]}` | Richard |
| GET | `/api/settings` | — | `{profile, mode, integrations}` | Richard |
| PATCH | `/api/settings` | `{mode?}` | `{settings}` | Richard |

Errors: `{"error":{"code":"...","message":"..."}}` with 4xx/5xx. UI shows a non-blocking toast and keeps the last fixture data.

---

## 3. Shapes

### Case
```json
{"id": "case_002", "business_id": "harbor_studio", "title": "DEMO-CREDIT-001 — Case-002",
 "program_id": "DEMO-CREDIT-001", "program_fictional": true, "status": "needs_evidence",
 "unresolved_requirements": 2, "pending_actions": 1, "last_run_id": "run_case002_v1"}
```

### Message + Attachment
```json
{"id": "msg_014", "case_id": "case_002", "sender": "training@vendor.example", "date": "2025-09-12",
 "subject": "Paid training invoice", "category": "tax-credit",
 "attachment_state": "claimed|available|missing|unreadable|none",
 "attachment_claim": "see attached invoice", "excerpt": "…", "source": "demo mailbox"}
```
```json
{"id": "att_003", "message_id": "msg_014", "filename": "invoice.pdf", "available": false,
 "extracted_text_ref": null, "error": "attachment referenced but not present"}
```

### Transaction
```json
{"id": "txn_020", "case_id": "case_002", "date": "2025-09-15", "counterparty": "Northline Training Co.",
 "amount_cents": 185000, "direction": "expense", "category": "training",
 "receipt_ref": "msg_014", "review_flag": "duplicate_candidate|recurring|capex|none",
 "duplicate_of": "txn_019", "source": "transactions.csv"}
```
`direction` is explicit: `expense` or `credit`. No tax-treatment field, no benefit estimate.

### Checklist + Requirement
```json
{"id": "cl_demo_001", "program_id": "DEMO-CREDIT-001", "jurisdiction": "demo", "period": "2025",
 "version": "1.0", "source": "demo fixture", "fictional": true}
```
```json
{"id": "req_identity", "label": "Consistent business identity",
 "state": "supported|missing|conflicting|needs_review",
 "rationale": "…", "evidence_ids": ["ev_001"], "unresolved_questions": []}
```
No state is ever `eligible`. `supported` requires a verified evidence record; a claimed attachment cannot set it.

### Finding
```json
{"id": "find_003", "run_id": "run_case002_v1", "requirement_id": "req_payment",
 "state": "missing", "evidence_ids": ["ev_002"], "rationale": "…", "excerpt": "…"}
```

### Recommendation
```json
{"id": "rec_001", "case_id": "case_002", "category": "documentation|spending_review|credit_readiness",
 "finding": "Payment evidence is missing", "evidence_ids": ["ev_002"],
 "action": "Collect the paid training invoice or a bank confirmation",
 "conditions": ["Invoice must show the business name and amount"],
 "proposed_reviewer": "Owner", "timing_basis": "source_backed|owner_selected|none",
 "status": "open|accepted|dismissed", "dismiss_reason": null, "owner": null, "due_date": null}
```
`timing_basis` is mandatory; never infer a legal deadline from an email date.

### Task
```json
{"id": "task_001", "case_id": "case_002", "recommendation_id": "rec_001",
 "title": "Collect paid training invoice", "owner": "Owner", "due_date": null,
 "due_date_basis": "owner_selected|none", "status": "open"}
```

### Run + RunStep
See §1. `prism_url` is populated **only** after PRISM verifies the trace; otherwise `null` and `telemetry` = `pending|failed`. Local steps are always shown separately from the PRISM link.

### Package
```json
{"package_id": "pkg_case002_001", "case_id": "case_002", "run_id": "run_case002_v1",
 "markdown": "# Review Package …", "generated_at": "ISO",
 "fictional_warning": "Synthetic demo — Not tax advice. No eligibility decision.",
 "limitations": ["Evidence sufficiency only", "Synthetic data"]}
```

### Integration
```json
{"name": "Nicrron", "status": "configured|verified|unavailable|demo-only",
 "detail": "nicrron/auto", "checked_at": "ISO"}
```

---

## 4. Fixtures (Richard commits by 12:55)

`fixtures/cases.json` · `inbox.json` · `transactions.csv` · `checklist.json` · `findings.json` · `next_year.json` · `package.md` · `run.json`

Each mirror file holds the response body above. Demo dataset: **Harbor Studio Demo LLC**, fictional `DEMO-CREDIT-001`, Cases 001–003 + control. The repo's Gowanus Kettle data is a legacy regression fixture and is **not** loaded in demo mode.

UI client: `fetchJson(path)` → API in live mode, `/fixtures/<name>` in replay mode (`?fixture=1` or `DEMO_MODE=replay`). Replay is labeled `demo-only` and makes no model call.

---

## 5. PRISM emitter (Richard implements; Thuy consumes dashboard)

```python
# src/observability/prism.py
with prism_run(run_id, agent_id="moneyfinder", version="v1"):
    prism_step("extract_attachments", tool="extract_attachments", status="failed",
               latency_ms=820, input_summary="…", output_summary="…", error="attachment missing")
```

- One trace/step per tool/model call; step names must match §1.
- Metadata: `model`, `version`, `status`, `cost_usd`, `error`.
- No raw PII; summaries only.
- If only model-level HTTP traces are possible, set `telemetry="pending"` and mark trajectory integration incomplete. **Never claim a bare `POST /api/traces` captures tools.**

---

## 6. Environment

```bash
MODEL_PROVIDER=nicrron
NICRRON_API_KEY=
NICRRON_BASE_URL=https://api.nicrron.ai/v1
NICRRON_MODEL=nicrron/auto
PRISMTRACE_API_KEY=
PRISMTRACE_PROJECT_ID=6e1051f7-8dce-498f-9846-d6acaa087737
PRISMTRACE_HOST=https://api.prism.blockconvey.com
ELEVENLABS_API_KEY=      # P2 only
```

`.env` is local and gitignored; `.env.example` carries names only.

---

## 7. UI routes + owners

| Route | Screen | Owner | Fixtures |
|---|---|---|---|
| `/` | redirect → dashboard | Kenan | — |
| `/dashboard` | case status, unresolved requirements, pending actions, last run, integrations | Thuy | `cases.json`, `run.json` |
| `/inbox` | search/filter/category/source drawer/attachment state | Thuy | `inbox.json` |
| `/transactions` | table, direction, receipt, duplicate flag, CSV import errors | Kenan | `transactions.csv` |
| `/credit-review` | checklist, requirement states, evidence, questions | Thuy | `checklist.json`, `findings.json` |
| `/next-year` | cards, accept/dismiss, owner/due date | Kenan | `next_year.json` |
| `/package` | preview + real Markdown download | Thuy | `package.md` |
| `/run-history` | run status, steps, errors, telemetry, verified PRISM link | Kenan | `run.json` |
| `/settings` | profile, modes, integrations, reset demo | Kenan | — |

Design tokens: `ui/static/css/design.css` (Thuy). Shell: `ui/index.html` (Kenan). Shared docs change by announcement.

---

## 8. Non-negotiables

- Synthetic data only; persistent banner on every screen and export.
- No "Eligible", no eligibility percentage, no benefit estimate, no invented deadline.
- A claimed attachment is not evidence; `extract_attachments` must return an extracted record before `supported`.
- Failed tool ⇒ no complete finding; run `failed`/`partial`.
- No email send, Gmail write, filing, transaction modification, third-party submission.
- Export is a real Markdown file; buttons must work.
- Never commit `.env`, keys, real personal data or video files.
