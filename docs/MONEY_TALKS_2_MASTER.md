# Moneyfinder — PRD & Delivery Epic (Merged)

**Version 1.1 · Build baseline · October 17, 2026**
**Supersedes:** Kenan's PRD v1.0 (product baseline) + Epic 01 v1 "Claims Desk & Books" (delivery plan).
**Event:** MONEY TALKS 2 · Track: **Money Operations** · Nomad Works, NYC · one day.
**Repo:** https://github.com/muen-dev/moneyfinder · **Team:** Thuy (design/PRISM), Kenan (UI/demo), Richard (agent/platform).
**Freeze:** 16:15 (`demo-freeze`) · **Demo:** 2-min video + 3-min live pitch.

> **One line:** Moneyfinder turns a small business's scattered email and transaction evidence into a review-ready package and a next-year action plan — with every finding traceable, no eligibility calls, and no filing.

---

## 0. Merge decision — read this first

The two documents disagreed about what the product is. The PRD wins the product; the epic supplies the delivery plan, demo craft, sponsor integration and team split.

| # | Area | Epic v1 said | Kenan PRD says | **Merged decision** |
|---|---|---|---|---|
| 1 | Product job | Find credits, file applications, track approved/paid | Organize evidence, evidence-status checklist, draft review package, next-year actions | **PRD wins.** Review assistant. No filing, no eligibility authority, no autonomous external action. |
| 2 | Eligibility | Verdicts: eligible / needs info / not eligible | Requirement states: supported / missing / conflicting / needs_review; never "Eligible" | **PRD wins.** The word "Eligible" never appears as a decision state. |
| 3 | Dashboard | Four-column claims pipeline (found / in process / approved / paid) | Case status, unresolved requirements, pending actions, last run, integration status | **PRD wins.** No government-application states, no payment tracking. |
| 4 | Programs | Real NY/federal credits (IT-636, IT-212, IT-643, 8846) | Fictional `DEMO-CREDIT-001`; real rules need release review | **PRD wins for the demo.** Real catalog stays in the repo as a P2 reference, disabled. |
| 5 | Agency web search | Live official-page fetch + rule extraction | Not in scope; no invented eligibility | **Dropped from P0.** P2 only, behind release review. |
| 6 | Form filling / submission | Mock portal fill, stop before submit | No filing; no transaction modification; no third-party submission | **Dropped from P0.** Not built, not demoed. |
| 7 | Accountant output | XLSX/CSV ledger + accountant packet | Markdown Review Package: preview + real download, evidence index, limitations | **PRD wins for P0.** Markdown is required; XLSX/CSV is optional P1. |
| 8 | Ledger | EOY ledger, tax treatment, capex/tips tie-out, reconciliation | Transactions: date, counterparty, amount, category, receipt, review flag; code-based arithmetic; no benefit math | **Merged.** Transactions become evidence; keep dedupe / missing-receipt / arithmetic checks; **drop tax-treatment advice and benefit estimates.** |
| 9 | Next Year | "Next action" on each claim | Cards in documentation / spending-review / credit-readiness, accepted as persisted tasks | **PRD wins.** Core P0 screen. |
| 10 | Voice | ElevenLabs voice briefing (P1) | Not mentioned | **P2.** No owner until the demo spine is green. |
| 11 | Persona & data | Marisol Vance, Gowanus Kettle Brewing (real credits) | Harbor Studio Demo LLC, fictional program, Cases 001–003 + control | **PRD wins for the demo.** Gowanus becomes a legacy regression fixture, not the demo. |
| 12 | Modes & status | Not specified | Demo / fixture replay / live mailbox disabled; persistent synthetic banner; integration status | **PRD wins.** All three required. |
| 13 | PRISM | 12-step claims run; 50 runs; alert; root cause v1/v2 | 7+ substantive local tool executions, 6+ verified in PRISM, agent_id `moneyfinder`, v1/v2, honest telemetry | **Merged.** Use the PRD tool set and thresholds; keep the alert (hackathon Money Operations proof) and root-cause/v2. |
| 14 | Stack | Flask repo + optional Ninoo | Ninoo build prompt / builder architecture | **One runtime.** Flask repo is the integration target; Ninoo is an optional UI prototype only. Decision in §25. |

### What survives from Epic v1

- The **persona-led demo** and the honesty discipline ("the receipt is the product").
- **Provenance + quote requirement**: every fact/finding tied to a source excerpt; contradictions preserved.
- The **Nicrron adapter** (OpenAI-compatible, one key, model swap).
- The **PRISM proof plan**: 50+ runs, alert, root-cause cluster + v2, screenshot fallbacks.
- The **3-person parallel split**, checkpoints and freeze.
- The **estimate method** (story points + three-point hours + capacity cut line).

### What is explicitly dropped from P0

- Filing, form filling, mock submissions, agency portals.
- Real-program eligibility verdicts and "approved/paid" tracking.
- Dollar savings, benefit estimates, eligibility percentages, invented deadlines.
- Live agency web search, live Gmail mailbox (disabled by default), voice.
- XLSX accountant packet (optional P1 only).

---

# Part I — Product requirements (PRD baseline)

## 1. Vision and positioning

Moneyfinder helps a small business **organize financial evidence today and improve administrative readiness tomorrow**. It is a **review assistant** — not an accountant, tax filer or eligibility authority.

The user is a small-business owner with paperwork spread across an inbox, attachments and a transaction export. The product converts that mess into:
1. a **case file** with an evidence-status checklist,
2. a **draft professional-review package**, and
3. a **next-year action plan** the owner can accept and track.

It never tells the owner they qualify for anything, never estimates a refund, never files, and never contacts an agency.

## 2. Goals and non-goals

**Goals**
- **G1:** Convert sample correspondence into a complete evidence-status checklist.
- **G2:** Generate a draft professional-review package with source links.
- **G3:** Convert observed gaps and transaction patterns into reviewed future actions.
- **G4:** Demonstrate real reasoning through **Nicrron** and observable execution in **PRISM**.

**Non-goals (hard):** filing, legal conclusions, live financial transfers, guaranteed savings, autonomous external actions, email sending, Gmail write, transaction modification, third-party submission.

## 3. Persona and demo story (merged)

**Primary demo business:** **Harbor Studio Demo LLC** — synthetic, per Kenan's fixtures. (If `fixtures.json` names a founder, use that name; do not invent new facts over the fixture.) The working narration name in scripts is **the Harbor Studio founder**; add a name only when the fixture supplies one.

**Fictional program:** `DEMO-CREDIT-001` — *explicitly not a real tax credit*. Demo-only evidence requirements:
1. consistent business identity,
2. paid training invoice,
3. payment evidence,
4. attendance record.

**Cases (from the PRD):**
- **Case-001** — lacks the attendance record (missing evidence → collection task).
- **Case-002** — references an attachment that is not actually available (filename ≠ proof → `missing`/`needs_review`).
- **Case-003** — conflicting business names (→ `conflicting`; cannot become `supported`).
- **Control case** — clean; every requirement has verified evidence.

**The story:** the founder has a reviewable file but cannot tell what is proven, what is missing, and what to fix before the professional review. Moneyfinder produces the checklist, the package and the next-year actions — and on `Case-002` it refuses to treat a claimed attachment as evidence. That refusal is the product.

**Legacy fixture:** the repo's Gowanus Kettle dataset and real NY credit catalog remain for regression/reference only. They are **not** in the demo and **not** enabled in the UI.

## 4. Modes, banner and integration status

**Modes**
- **Demo mode** (default): synthetic data, fictional checklist, persistent banner on every screen and every export: **"Synthetic demo — Not tax advice. No eligibility decision."**
- **Fixture replay**: no model call; explicitly labeled replay; never claims live sponsor execution.
- **Live mailbox mode**: disabled by default; only a dedicated synthetic-data mailbox for the event. Production financial data is outside this release.

**Setup status indicator** (Settings, Dashboard, Run History) must distinguish:
`configured` · `verified` · `unavailable` · `demo-only`.
Never show a green "connected" for an unverified integration. Nicrron and PRISM each get a status row. Fixture replay gets a `demo-only` label.

## 5. Primary journey

`Open dashboard → load sample → inspect inbox and transactions → run analysis → review case findings and evidence → inspect Next Year recommendations → accept actions → export draft package.`

Secondary flow: **import a validated CSV → rerun analysis as a new run** without silently replacing previous results (run history keeps both).

## 6. Information architecture

| Screen | Must show | Must not show |
|---|---|---|
| **Dashboard** | case status, unresolved requirements, pending actions, last run, integration status, mode banner | invented dollar savings, eligibility percentages, "approved/paid" |
| **Inbox** | searchable category list; sender, date, subject, attachment availability; source detail drawer; category correction | claims that an attachment exists without evidence |
| **Transactions** | date, counterparty, amount (integer cents), category, receipt link, review flag, explicit `direction` (expense/credit), CSV import + errors | tax treatment advice, projected benefit, auto-cancellation |
| **Credit Review** | checklist version, requirement states (`supported`/`missing`/`conflicting`/`needs_review`), evidence, rationale, unresolved questions | the word "Eligible" as a decision, percentages, filing CTA |
| **Next Year** | cards in `documentation` / `spending_review` / `credit_readiness`; finding, evidence IDs, action, conditions, proposed reviewer, timing basis, status; accept/dismiss; owner and owner-selected due date | inferred legal deadlines, "do this to get $X" |
| **Review Package** | preview and real Markdown download; evidence index; limitations; run version; generated timestamp; fictional-program warning | final eligibility or tax advice |
| **Run History** | run status (`queued`/`running`/`succeeded`/`failed`/`partial`), version, step states, errors, telemetry delivery, verified PRISM link **only if configured**; local steps labeled separately | fabricated PRISM proof |
| **Settings** | profile, modes, integration status, connection controls, reset demo | live production connections |

**Design language:** professional finance dashboard — light background, navy text, restrained teal accents, accessible status badges with text as well as color, mobile-friendly tables/cards. Primary action: **Analyze Sample Business**. Loading, empty, partial and error states required. All main buttons work.

## 7. Functional requirements

- **FR-01** Scope retrieval to the selected dataset, dates and case. Record the query and page completion.
- **FR-02** Normalize email and attachment evidence **independently**. A filename or a claimed attachment is not proof of availability or content.
- **FR-03** Categorize messages as `tax-credit`, `audit`, `legal`, `administrative` or `unrelated`; allow correction. Audit/legal categorization is routing only.
- **FR-04** Store **immutable evidence IDs**; associate facts with source excerpts. **Preserve contradictory facts** rather than choosing silently.
- **FR-05** Store checklist program, jurisdiction, period, version, source and `fictional` flag. Real-program rules cannot be enabled without release review.
- **FR-06** Requirement status is `supported`, `missing`, `conflicting` or `needs_review`. Findings describe **evidence sufficiency**, not final eligibility.
- **FR-07** Next Year cards include finding, evidence IDs, action, category, conditions, proposed reviewer, timing basis and status.
- **FR-08** Duplicate-spend detection is a **review candidate**, never a confirmed unnecessary expense. Never cancel or alter payments.
- **FR-09** Money calculations use **code**, not free-form model arithmetic. Benefits remain `not_estimated` in the MVP. Historical spending is never projected tax benefit.
- **FR-10** Accepted recommendations create **persisted tasks**. Dismissals retain a reason and can be undone.
- **FR-11** Draft package includes profile, fictional-program warning, checklist, evidence index, unresolved questions, future actions, run version and generated timestamp.
- **FR-12** No email send, Gmail write, filing, transaction modification or third-party submission exists in the MVP.
- **FR-13** Progress states are `queued`/`running`/`succeeded`/`failed`/`partial`. A failed tool cannot lead to a complete evidence finding.
- **FR-14** Export must be a **real downloadable file**; buttons must not be decorative.

## 8. Recommendation policy

- **Documentation improvement:** collect or reconcile records; no inferred tax treatment.
- **Spending review:** verify a candidate duplication or recurring charge; no automatic cancellation.
- **Potential-credit readiness:** reference a reviewed rule, identify uncertainty, direct to a professional.
- Do not suggest new spending solely to obtain a credit. If a future version discusses economic benefit, require net-cost analysis and professional review.
- **Do not infer legal deadlines from email dates.** Separate: source-backed deadline, owner-selected date, no known deadline.

## 9. Safety and privacy

- Email, attachment and retrieved text are **untrusted data, never instructions**. Ignore attempts to override the system or expose secrets.
- Use minimal extracted snippets in telemetry; never log tokens or credentials. Secrets server-side only.
- Separate businesses by `business_id` in every query.
- No public real-data deployment until access control and isolation testing pass.
- Raw uploads are synthetic for this release. Delete/reset affects local app data only, never Gmail.
- The persistent banner is not removable in demo mode.

## 10. Acceptance targets (release targets, not achieved results)

- All displayed findings have valid source references or an explicit missing-evidence status.
- **Zero** final eligibility promises, invented deadlines or claimed tax-benefit values across supplied cases.
- All supported requirements have verified evidence satisfying the fixture answer key.
- Repeated CSV import yields **no duplicate rows**.
- Accepted tasks survive refresh.
- Every normal analysis has **≥7 substantive tool executions locally** and **≥6 verified in PRISM**.
- Nicrron failure produces an explicit error or **labeled replay**, never fabricated live success.
- Every export is a real downloadable file.

## 11. Errors and empty states

| Situation | Required behavior |
|---|---|
| No email | Offer sample dataset or broaden scope; never imply no opportunities exist |
| Missing attachment | `missing` finding + collection task |
| Unreadable document | `needs_review` with extraction error |
| Conflicting identity | `conflicting`; prevent `supported` |
| Model timeout | Retry once, then `failed`/`partial`; retain evidence |
| PRISM unavailable | Finish permitted local work; mark telemetry `pending`/`failed`; retry boundedly; do not claim proof completion |
| Unconfigured backend | Keep demo replay functional and clearly labeled; integrations incomplete |

## 12. Release priorities

- **P0:** synthetic end-to-end workflow, Next Year cards, task persistence, Markdown export, Nicrron, real tool tracing, tests.
- **P1:** read-only synthetic Gmail mailbox, improved CSV imports, professional handoff presentation, XLSX export.
- **P2:** verified real programs, multi-business production, reminders, approved communications, voice.

---

# Part II — Delivery epic

## 13. The analysis run and its tools

One analysis = one **run** = one PRISM `session_id`. A run is `queued → running → succeeded | failed | partial`. A failed tool cannot produce a complete finding; the UI shows the failure and retains evidence.

**Tool set (8; ≥7 substantive executions per normal run):**

| Tool | Does | Deterministic or model |
|---|---|---|
| `search_mail` | Scoped query over the case dataset; records query + pages completed | deterministic |
| `fetch_messages` | Fetch matching messages; untrusted content delimited | deterministic |
| `extract_attachments` | Normalize attachment availability **independently** of message claims | deterministic |
| `load_transactions` | Load/validate CSV rows; integer cents; dedupe | deterministic |
| `retrieve_checklist` | Load the fictional program checklist (version, source, `fictional=true`) | deterministic |
| `compare_evidence` | Match evidence to requirements; identity/attachment/arithmetic checks; preserve contradictions | deterministic + model-assisted extraction |
| `generate_recommendations` | Documentation / spending-review / credit-readiness cards | model, schema-validated |
| `compose_review_package` | Markdown package with evidence index + limitations | deterministic template + model synthesis |

**Model use:** classification (FR-03), extraction assistance, readable synthesis. **Arithmetic and state decisions are code.** Every model output is schema-validated; unsupported evidence cannot be marked `supported`.

**Evidence discipline**
- Immutable `evidence_id`; each fact/finding points to a source excerpt.
- Contradictions are stored and surfaced, never silently resolved.
- A claimed attachment without an extracted record is `missing` — this is the demo's integrity moment.

## 14. Architecture

```
Browser (Flask/Jinja or Ninoo)
   │  Dashboard · Inbox · Transactions · Credit Review · Next Year · Package · Run History · Settings
   ▼
Flask API (src/server.py)
   ├── Case + dataset service (business_id scoping, fixture/demo modes)
   ├── Analysis orchestrator (run state machine, tool steps, persistence)
   ├── Nicrron client (OpenAI-compatible; classify/extract/synthesize; schema-validated JSON)
   ├── Deterministic checks (attachment availability, identity conflicts, arithmetic, dedupe)
   ├── Checklist service (fictional program, versioned)
   ├── Recommendation + task service (accept/dismiss/undo, persistence)
   ├── Package composer (Markdown; real download)
   ├── Integration status service (configured/verified/unavailable/demo-only)
   └── PRISM emitter (session per run; step per tool; metadata version v1/v2)
```

**Runtime decision:** the existing Flask repo is the integration target (Python, tests, PRISM HTTP/SDK, Nicrron OpenAI-compatible). **Ninoo is optional** — if used, it must hit the same contract, and only one runtime is demoed. Nicrron satisfies the required platform; Ninoo is not required.

**Fixture replay:** a first-class mode, not a fallback. No model call; labeled `demo-only`; the UI never claims live execution.

## 15. Platform integrations

### Nicrron (required)
- OpenAI-compatible client, server-side only: `base_url=https://api.nicrron.ai/v1`, `NICRRON_API_KEY`, `NICRRON_MODEL=nicrron/auto` (configurable).
- Treat tool-calling and structured-output support as **capabilities to test**; orchestrate server functions with schema-validated model JSON.
- No provider key in frontend. **No silent fixture fallback after a failed API call** — explicit error or labeled replay.
- Model swap is a capability demo (same guardrail, different model), not a requirement.

### PRISM (required) — Money Operations proofs
- `agent_id = moneyfinder`; one `session_id`/`run_id` per analysis; metadata `version: v1|v2`.
- **Real trajectories**: if the backend can only send model-level HTTP traces, mark trajectory integration incomplete and use the supported SDK/OTel path for tool spans. Do not claim a bare `POST /api/traces` captures tools.
- **Proof 1 — Sessions:** one run on the Steps tab with **≥7 tool executions** (≥6 verified in PRISM), named after the tools above.
- **Proof 2 — Alert:** alert on **failed tool / partial run** (e.g., `extract_attachments` failure on Case-002), firing on a real run. Screenshot rule + firing event.
- **Proof 3 — Root Cause:** 3+ failed runs of the attachment-evidence scenario; cluster + cause sentence; **v2** (evidence validator requires an extracted attachment record + excerpt) passes the same inputs.
- **50+ runs** seeded before fixes; Run History shows telemetry delivery + a verified PRISM link only when configured.
- **Cause sentence:** *"v1 treated a claimed attachment as evidence because the validator checked the message text, not an extracted attachment record."*

### ElevenLabs (optional, P2)
Not in the demo spine. If time remains, a spoken run summary — never a replacement for the dashboard, never a claim of live sponsor proof.

## 16. Data model

All rows scoped by `business_id`. Money in integer cents. Evidence IDs immutable.

```text
business        id, name, profile, mode(demo|fixture|live), created_at
case            id, business_id, program_id, title, status, created_at
message         id, business_id, case_id, sender, date, subject, category,
                attachment_state(none|claimed|available|missing|unreadable), excerpt, source
attachment      id, message_id, filename, available, extracted_text_ref, error
transaction     id, business_id, case_id, date, counterparty, amount_cents, direction,
                category, receipt_ref, review_flag, duplicate_of, source
checklist       id, program_id, jurisdiction, period, version, source_url, fictional
requirement     id, checklist_id, label, state(supported|missing|conflicting|needs_review),
                rationale, evidence_ids[], unresolved_questions[]
finding         id, case_id, run_id, requirement_id, state, evidence_ids[], excerpt, rationale
recommendation  id, case_id, category(documentation|spending_review|credit_readiness),
                finding, evidence_ids[], action, conditions[], proposed_reviewer,
                timing_basis(source_backed|owner_selected|none), status(open|accepted|dismissed),
                dismiss_reason, owner, due_date
task            id, case_id, recommendation_id, title, owner, due_date, status, created_at
run             id, case_id, version(v1|v2), status, started_at, ended_at, error,
                telemetry(ok|pending|failed), prism_url
run_step        id, run_id, tool, status, started_at, ended_at, input_summary,
                output_summary, error
package         id, case_id, run_id, markdown, generated_at, fictional_warning, limitations[]
integration     name, status(configured|verified|unavailable|demo-only), detail, checked_at
```

**Requirement state rules:** `supported` requires at least one verified evidence record satisfying the checklist rule; `missing` when required evidence is absent; `conflicting` when identity/values disagree; `needs_review` when evidence exists but cannot be verified (unreadable document, extraction error). No state is ever `eligible`.

## 17. Demo script

### 2-minute video

| Time | Screen | Action | Line |
|---|---|---|---|
| 0:00 | Banner + title | Persistent synthetic banner visible | "Every small business has a paperwork pile. Moneyfinder turns it into a review-ready file — without pretending to be your accountant." |
| 0:15 | Dashboard | Load sample; unresolved requirements, pending actions, integration status | "One case, four requirements, three evidence gaps — and no invented dollar figures." |
| 0:35 | Inbox | Open Case-002; claimed attachment; source drawer shows it is not actually available | "The email says there's an attachment. The file isn't there. Moneyfinder believes the record, not the claim." |
| 0:55 | Transactions | CSV import + duplicate candidate + receipt link; deterministic arithmetic | "Transactions are evidence: deduped, flagged for review, never auto-cancelled." |
| 1:15 | Credit Review | Requirement states supported/missing/conflicting/needs_review; evidence; questions | "This is evidence sufficiency, not eligibility. The word 'eligible' never appears." |
| 1:35 | Next Year | Three cards; accept the documentation action; task persists | "Every gap becomes a reviewed next action — with an owner, conditions and a reviewer — never an inferred deadline." |
| 1:55 | Review Package | Preview + real Markdown download; evidence index; limitations | "A draft package for the professional: evidence index, open questions, run version." |
| 2:05 | Close | Repo + banner | "Synthetic demo. Not tax advice. No eligibility decision." |

### 3-minute live pitch

1. **Problem (20s):** evidence is scattered; the review file is incomplete; owners cannot tell what is proven.
2. **Demo (100s):** Dashboard → Inbox (missing attachment) → Transactions (duplicate candidate) → Analyze (7+ tool steps) → Credit Review (states) → Next Year (accept) → Package (download).
3. **PRISM (40s):** 50+ runs; the 7-step session; the alert firing on the failed attachment tool; the v1 cluster + cause; v2 passes the same cases. Show Run History's local vs PRISM distinction.
4. **Nicrron (10s):** classification/extraction/synthesis through one OpenAI-compatible key; failure is explicit, never fake.
5. **Close (10s):** "Moneyfinder organizes the evidence and hands the professional a clean file. The decision stays with the professional."

### Failure → fix (rehearse)

- **v1 bug:** Case-002's message claims an attachment; v1 marks the requirement `supported` because the classifier saw the claim. Three variants of the case fail the same way.
- **PRISM cluster + cause:** "v1 validated message text, not an extracted attachment record."
- **v2:** `extract_attachments` must return an `available` record with an excerpt before `compare_evidence` can set `supported`; otherwise `missing` + collection task. Same inputs: pass.
- **Why it matters:** this is FR-02 and FR-06 made observable; it is the honest heart of the demo.

## 18. Team split (3 people, parallel)

| Person | Owns | Branch |
|---|---|---|
| **Thuy** — Product Designer, PRISM owner, repo owner | Dashboard, Inbox, Credit Review, Review Package UI; design tokens; copy/QA; **PRISM dashboard, alert, proofs**; submission visuals | `feat/thuy-onboarding-prism` (branch name historical; scope below) |
| **Kenan** — Developer, **Demo owner** | UI shell, Transactions, Next Year, Run History, Settings; API client; **2-min video, live pitch, submission** | `feat/kenan-desk-books` (historical; scope below) |
| **Richard** — Developer | Case/dataset API, analysis orchestrator + 8 tools, Nicrron client, persistence, CSV import, Markdown export, integration status, PRISM emitter, fixtures, tests | `feat/richard-ledger-agent` (historical; scope below) |

**File ownership**

- **Thuy:** `ui/dashboard.html`, `ui/inbox.html`, `ui/credit_review.html`, `ui/package.html`, `ui/static/css/design.css`, `docs/proofs/**`.
- **Kenan:** `ui/index.html`, `ui/transactions.html`, `ui/next_year.html`, `ui/run_history.html`, `ui/settings.html`, `ui/static/js/**`, `docs/DEMO_RUNBOOK.md`.
- **Richard:** `src/**`, `fixtures/**`, `scripts/**`, `requirements.txt`, `.env.example`, `research/**` (legacy reference only).
- Shared docs (`TEAM_PLAN.md`, `CONTRACT.md`, `MASTER`) change by announcement.

**Timeline (checkpoints hard):** 12:40 kickoff · 12:55 contract/fixtures frozen · 13:00–14:10 build · **14:10 CP1 merge** · 14:25–15:35 build · **15:35 CP2 end-to-end** · 15:50–16:15 proofs + video · **16:15 freeze** · 16:15–17:00 submission · 17:00–18:00 rehearsal/buffer.

**Scope cut for 3 builders (~15–18 person-hours):**
- Must: dashboard, inbox, transactions, credit review, analysis with 7+ tools, Next Year + accept/task, Markdown package, Run History (basic), Nicrron, PRISM proofs, video.
- Defer: CSV import advanced validation (use fixture CSV), Settings polish, XLSX export, Gmail read-only, voice, PRISM guardrails.
- Cut order: voice → XLSX → Gmail → Settings polish → CSV advanced. Never cut: missing-attachment integrity, 7+ tool run, 6+ PRISM verification, package download, banner.

## 19. Build plan (today)

| Window | Thuy | Kenan | Richard |
|---|---|---|---|
| 12:40–12:55 | Repo/branches, PRISM check, contract ack | UI shell + client with fixture mode | Contract + fixtures commit; Nicrron client skeleton |
| 12:55–14:10 | Dashboard + Inbox UI against fixtures | Transactions + Next Year UI | Case/message/transaction APIs; CSV load; deterministic checks |
| 14:10–14:25 | **CP1** | **CP1** | **CP1** |
| 14:25–15:35 | Credit Review + Package UI; PRISM alert monitoring | Run History + Settings; demo script draft | Analysis orchestrator + 8 tools; package composer; PRISM emitter + 50 runs |
| 15:35–15:50 | **CP2** end-to-end | **CP2** | **CP2** |
| 15:50–16:15 | Proof screenshots; review video claims | Record 2-min video | Root-cause v1/v2 replay; README |
| 16:15–17:00 | Submission copy/visuals | Upload video + submit | Public repo check |
| 17:00–18:00 | Pitch support (PRISM segment) | Rehearse live pitch | Buffer/Q&A |

## 20. Task checklist (acceptance)

**Product/backend (Richard)**
- [ ] Case + dataset API, `business_id` scoping, demo/fixture modes — *accept: no cross-case data leaks; mode labeled*
- [ ] Deterministic checks: attachment availability independent of message claims, identity conflict, arithmetic, CSV dedupe — *accept: Case-002 missing attachment; Case-003 conflicting; repeated CSV import yields no duplicates*
- [ ] Analysis orchestrator + 8 tools, run states, step persistence, failure retention — *accept: ≥7 substantive executions locally; failed tool blocks a complete finding*
- [ ] Nicrron client with schema validation; explicit error/replay on failure — *accept: no silent fixture fallback; no key in frontend*
- [ ] Checklist service with `fictional=true`, version/source — *accept: real rules cannot be enabled without a release flag*
- [ ] Recommendations + task persistence + dismiss reason/undo — *accept: accepted task survives refresh*
- [ ] Markdown package composer + real download — *accept: file downloads; contains evidence index, limitations, warning, run version, timestamp*
- [ ] PRISM emitter (session per run, step per tool, version v1/v2) + 50-run seed — *accept: ≥6 steps verified in PRISM; Run History link only if verified*
- [ ] Integration status service — *accept: configured/verified/unavailable/demo-only all render honestly*
- [ ] Tests for dedupe, missing attachment, conflict, export — *accept: run locally*

**UI (Thuy + Kenan)**
- [ ] Persistent synthetic banner on every screen and export — *accept: visible on all 8 screens*
- [ ] Dashboard — *accept: no savings/eligibility; shows case status, requirements, actions, last run, integrations*
- [ ] Inbox — *accept: search/filter/category correction/source drawer/attachment state*
- [ ] Transactions — *accept: direction, integer cents, receipt link, duplicate flag, import errors*
- [ ] Credit Review — *accept: four states only; no "Eligible"; evidence + questions*
- [ ] Next Year — *accept: three categories; accept/dismiss; owner/due date labeled owner-selected*
- [ ] Review Package — *accept: preview + real Markdown download*
- [ ] Run History — *accept: local steps vs PRISM verified link; telemetry status*
- [ ] Settings — *accept: profile, modes, integration status, reset demo*
- [ ] Fixture replay mode — *accept: labeled, no model call, no live claim*
- [ ] Empty/loading/partial/error states — *accept: all reachable*

**Proofs/demo**
- [ ] 50+ PRISM runs before fixes
- [ ] 7-step (or more) session; ≥6 verified
- [ ] Alert firing on failed attachment tool/partial run
- [ ] Root-cause cluster (3+) + cause sentence + v2 same inputs pass
- [ ] 2-min video + 3-min pitch + submission
- [ ] Public repo, README with sponsor tools + synthetic disclaimer

## 21. PRISM proof checklist

- [ ] `docs/proofs/prism-credential.png`
- [ ] `docs/proofs/prism-50-runs.png`
- [ ] `docs/proofs/prism-session-7steps.png`
- [ ] `docs/proofs/prism-alert.png`
- [ ] `docs/proofs/prism-root-cause.png`
- [ ] `docs/proofs/prism-v2.png`
- [ ] Run History screenshot showing local vs verified PRISM link
- [ ] Cause sentence on the slide

## 22. Judging alignment

| Criterion | Evidence |
|---|---|
| Real product | 8 working screens, real CSV import, real Markdown export, persisted tasks |
| Track fit (Money Operations) | Evidence ops, transaction review, professional handoff, next-year actions |
| PRISM | 50+ runs, ≥7 local / ≥6 verified steps, alert, root-cause + v2 |
| Nicrron | Classification/extraction/synthesis through one key; explicit failure behavior |
| Honesty | Fictional program, persistent banner, no eligibility/savings claims |
| Tangible artifact | Downloadable Markdown review package |
| Demo quality | Deterministic sample, fixture replay fallback, proof screenshots |

## 23. Risks and mitigations

| Risk | Mitigation |
|---|---|
| PRD scope bigger than time | Demo spine cut (§18); deferrals explicit; fixtures first |
| `fixtures.json`/`transactions.csv` missing | Generate from PRD schema by 13:00; Kenan supplies originals; never block UI |
| Ninoo vs Flask divergence | One runtime; Flask is the integration target; Ninoo only if it hits the contract |
| "Eligible" language slips in | Copy review by Thuy; grep the UI + package for banned words before freeze |
| PRISM tool trajectories not captured | Use SDK/OTel for tool spans; if only model-level, label integration incomplete, never claim proof |
| Nicrron outage | Explicit error + fixture replay; no fabricated success |
| Attachment bug not reproducible | Case-002 fixture variants (claim/filename/link) as the failure set |
| Time lost to Settings/Run History | Build them last; fixtures render them |
| Real data exposure | Synthetic `.example` data only; banner; no Gmail write |

## 24. Estimate (story-pointing)

**P0 — demo spine: 14 pts, split into two slices.**
- **Slice A — Evidence review + package: 10 pts.** O=9h, M=12h, P=19h → E≈12.7h; σ≈1.7h.
- **Slice B — Next Year + tasks + Run History/Settings: 4 pts.** O=3h, M=5h, P=7h → E≈5.0h; σ≈0.7h.
- P0 total: **E≈17.7h**, σ≈1.8h, p85≈20h.
- Capacity: 3 builders × ~6h = **18 person-hours** (event runs to ~6–7 PM). Fits at E, not at p85 → cut line active.
- Factor: **1.27 h/pt**. Reference: hand-me-up seed 1.0 h/pt; flags: existing repo reuse (−0.2), first-time PRD screens + Nicrron/PRISM integration (+0.5).
- **P1: 5 pts** (Gmail read-only synthetic, CSV advanced import, XLSX export, Settings polish) — E≈5.2h.
- **P2:** real programs (release review), voice, production isolation.

## 25. Open questions (resolve before 13:00)

1. **Seed data:** where are Kenan's `fixtures.json` and `transactions.csv`? If absent, generate the Harbor Studio schema from the PRD by 13:00. Confirm Harbor Studio is the demo dataset (Gowanus stays legacy).
2. **Runtime:** Flask repo vs Kenan's Ninoo app. Recommendation: Flask for P0 (tests, PRISM Python, one repo); Ninoo only as a UI prototype hitting the same contract. **One runtime on stage.**
3. **Kenan's GitHub username** — invite as collaborator to `muen-dev/moneyfinder`.
4. **Exact submission deadline** — confirm in Discord/`#hackathon-support`; freeze moves earlier if needed.
5. **PRISM billing code** `MONEYTALKS#2` — confirm redeemed under Settings → Billing.
6. **`START_HERE` S1–S3 / Gmail design refs S4–S5** — not in this workspace; link them in the repo if they exist.
7. **Case-003 conflicting names** — exact fixture values (current repo uses an address/ZIP conflict; the PRD calls for business-name conflicts).
8. **Ninoo prompt** — is it an alternate build or a reference? If alternate, which artifact do we demo?

## 26. Appendix

### 26.1 Environment

```bash
MODEL_PROVIDER=nicrron
NICRRON_API_KEY=
NICRRON_BASE_URL=https://api.nicrron.ai/v1
NICRRON_MODEL=nicrron/auto
PRISMTRACE_API_KEY=
PRISMTRACE_PROJECT_ID=6e1051f7-8dce-498f-9846-d6acaa087737
PRISMTRACE_HOST=https://api.prism.blockconvey.com
ELEVENLABS_API_KEY=          # P2 only
```

### 26.2 API surface (contract details in `CONTRACT.md`)

```
GET  /api/health
POST /api/demo/reset
GET  /api/cases
GET  /api/cases/{case_id}
GET  /api/inbox?case_id=&q=&category=
GET  /api/messages/{message_id}
GET  /api/transactions?case_id=
POST /api/transactions/import
GET  /api/checklist?case_id=
POST /api/analysis/run {case_id, mode}
GET  /api/analysis/runs/{run_id}
GET  /api/analysis/runs/{run_id}/findings
GET  /api/next-year?case_id=
POST /api/next-year/{id}/accept
POST /api/next-year/{id}/dismiss
GET  /api/tasks?case_id=
PATCH /api/tasks/{id}
GET  /api/package?case_id=
GET  /api/package/{package_id}/download
GET  /api/integrations/status
GET  /api/settings
PATCH /api/settings
```

### 26.3 Review Package (Markdown) outline

```markdown
# Review Package — Harbor Studio Demo LLC
> Synthetic demo — Not tax advice. No eligibility decision.
Program: DEMO-CREDIT-001 (fictional) · Version: <checklist version> · Run: <run id/version>
Generated: <timestamp>

## Profile
## Checklist (requirements + states)
## Evidence index (ID → message/attachment/transaction excerpt)
## Unresolved questions
## Future actions (accepted tasks)
## Limitations
- Evidence sufficiency only; no eligibility conclusion.
- Synthetic data; no real program rules.
- No filing, no payments, no third-party submission.
```

### 26.4 Honesty lines to keep

- "Synthetic demo. Not tax advice. No eligibility decision."
- "Evidence sufficiency, not eligibility."
- "The decision stays with the professional."
- "A claimed attachment is not evidence."
- "No inferred deadlines: source-backed, owner-selected, or none."
- "Benefits are not estimated."

---

*Merged by Thuy's agent · Product baseline: Kenan's PRD v1.0 · Delivery baseline: Epic 01 v1 · Interface: `CONTRACT.md` · Team: `TEAM_PLAN.md`.*
