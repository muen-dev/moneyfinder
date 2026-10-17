# Epic 01 — MoneyFinder Claims Desk & Books

**MONEY TALKS 2 · AI × Finance Hackathon · Saturday, October 17, 2026 · Nomad Works, 1216 Broadway, NYC**

| | |
|---|---|
| **Track** | **Money Operations** (primary) — with Money Intelligence research and Trust & Risk guardrails as supporting evidence |
| **Builds on** | `thetradingdoc/moneyfinder` (Daytona HackSprint build). This is an **extension**, not a rewrite. |
| **Execution** | 3-person split (Thuy / Kenan / Richard) in the repo's `docs/TEAM_PLAN.md`; interface frozen in `docs/CONTRACT.md` |
| **Persona** | Marisol Vance, Managing Member, Gowanus Kettle Brewing Co. LLC (synthetic) |
| **Status** | Build now — P0 |
| **Demo target** | Today, ~5:00–6:00 PM ET · 2-min video + 3-min live pitch |
| **Submission** | Public GitHub repo + Builderbase submission + Discord (confirm exact drop-dead time in `#hackathon-support`) |
| **Estimate** | **Slice A — Claims Desk: 11 pts**, O=10h M=14h P=21h → E≈14.5h · **Slice B — Claim-Ready Books: 5 pts**, O=3h M=5h P=8h → E≈5.2h · **P0 total 16 pts, E≈19.7h** · P1 voice 5 pts |
| **Created** | 2026-10-17 |

> **The one-line pitch:** *"MoneyFinder finds the money you're owed. The back office files the claims, tracks them until the deposit clears, and hands your accountant books that are ready to sign."*

---

## 1. The decision: Money Operations, and the build modification

### 1.1 Why Money Operations

The three tracks are themes, not assignments. Money Operations is the honest fit, and the new **books** capability makes it decisive:

- The product's job is not to *explain* money (Money Intelligence) or to *screen* a transaction (Trust & Risk). It is to run the recurring back-office workflows that move money into the business — exactly the track's definition: *"Build AI that improves how money moves and how finance teams operate."*
- A small business's tax credits and rebates are **receivables from the government**. Each application is an invoice to an agency with a status, an expected payment date, an evidence chain and an exception queue. That is an AR / CFO workflow.
- The same inbox that builds the claims profile also holds the **purchases**. Extracting them into an **end-of-year ledger, reconciling it, and packaging it for the accountant** is the track's expense/CFO workflow verbatim — and it is the feature that turns this from "a clever finder" into "software a finance operator would actually use."
- The track's own examples map one-to-one: *"an invoice or AP agent that … flags only what a human needs to see"* → our **exception queue**; *"a payment or expense reconciliation agent that works through mismatches step by step and shows its work"* → our **ledger reconciliation** and **agency-vs-deposit matching**; the sponsor doc's voice example → our **spoken claims briefing**.
- Two of the three required PRISM proofs are native to this build: a session with 6+ tool calls (we will have **12**), and an alert on a failed or out-of-tolerance run (we will fire it on a **reconciliation delta**).

### 1.2 The repositioning

> **Old MoneyFinder:** *"You may qualify for these credits."*
>
> **Claims Desk & Books:** *"You are owed $45,737. Four applications are open — two need your signature, one is approved. Your 2025 books are reconciled and packaged for your accountant. Here is exactly what happens next, with the evidence."*

We are not shipping another eligibility finder. We are shipping the **back office for money a small business is already owed**.

### 1.3 What changes in the build to fit the track

Six deltas, each visible in the demo and each a Money Operations idea:

| # | Delta | Why it fits Money Operations | PRISM payoff |
|---|---|---|---|
| 1 | **AR view, not a claim list.** Every application is a receivable: amount, status, expected payment date, aging, evidence. Pipeline total at the top. | Payments, budgeting, CFO reporting. | The pipeline run is one session. |
| 2 | **Exception queue ("Needs you").** The agent surfaces only conflicts, missing docs, missing receipts, signatures and deadlines. | *"Flags only what a human needs to see."* | Every exception is a span in the session. |
| 3 | **Reconciliation.** `PAYMENT_ISSUED` (agency says paid) ≠ `PAYMENT_CONFIRMED` (deposit matched); ledger duplicates and missing receipts become exceptions. | *"Works through mismatches step by step and shows its work."* | A deliberate mismatch gives a failed run + an alert. |
| 4 | **Claim-ready EOY books.** Purchases/receipts are extracted from the same inbox into a 2025 ledger: category, tax treatment, source email, confidence, missing-receipt flag. Duplicates deduped; totals reconciled; capex and tips tied to the exact figures the credit forms use. | Expense capture, reconciliation, accountant handoff — the core CFO workflow. | Adds 4 auditable steps to the session; new alert target. |
| 5 | **Accountant packet.** One download: XLSX (Summary, Ledger, Evidence index, Open questions, Credits), a one-page cover, and an email draft to the accountant. Clearly labeled *prepared for review — not filed*. | The professional handoff is the product; the accountant stays the professional. | Packet build is the final step of the session. |
| 6 | **Alerting + voice CFO.** Deadline, stalled claim, reconciliation delta, failed tool call, cost/latency alert; a spoken "where's my money?" briefing. | *"Voice CFO assistant for Money Operations"* (sponsor doc). | Required proof #2 (alert) + optional voice trajectory. |

The eligibility engine does not disappear — it becomes the **intake funnel** that feeds the desk.

### 1.4 Why not the other tracks

- **Money Intelligence** would put a memo at the center. Marisol does not need a better memo; she needs the forms filed, the receipts gathered, and the books signed off.
- **Trust & Risk** would put guardrails at the center. We do run them (no SSN/EIN leakage, no unlicensed tax advice, human approval before submission, accountant review), but they are **table stakes** for a money-moving agent, not the product.

**Track sentence for the pitch:** *"MoneyFinder Claims Desk & Books is the back office for the money a small business is already owed: it reads the inbox to prove eligibility, files the claims, tracks every application like a receivable, and turns the same inbox into a reconciled ledger your accountant can sign."*

---

## 2. The persona and the gap

**Marisol Vance** is the Managing Member of **Gowanus Kettle Brewing Co. LLC** — a fictional Brooklyn microbrewery (everything in `demo/gowanus-kettle/` is synthetic: `.example` domain, `00-` EIN, 555-01xx phone). Fourteen employees. Taproom tips. A canning line financed in July 2025. Two veterans hired in 2025. Rooftop solar and an EV charger. About 3,100 barrels brewed in New York.

Her inbox already contains the evidence — 55 synthetic emails (the 25 originals plus 30 receipts/invoices for the books demo): Gusto payroll, Indeed offers, DD-214s, NYS DOL WOTC notices, Chase equipment financing, Con Edison solar, Oscar health, her accountant **Owen Halloran CPA**, who has already **filed an extension for the 2025 IT-204**. That is the second half of the story: it is October, the 2025 return is on extension, and the accountant is asking for the receipts.

**What v1 already found for her:** four credits worth **$45,737**.

| Form | Agency | Credit | Amount |
|---|---|---|---|
| IT-636 | NYS DTF | Alcoholic Beverage Production Credit | $13,471 |
| IT-212 | NYS DTF | Investment Credit (canning line) | $7,460 |
| IT-643 | NYS DTF | Hire a Veteran Credit (two veterans) | $15,075 |
| IRS 8846 | IRS | FICA tip credit | $9,731 |
| | | **Total identified** | **$45,737** |

**What she still does not have, and what this epic gives her:**

1. A 10-minute onboarding that turns her inbox into a reviewed business profile — instead of a form.
2. Eligibility that cites the agency's **own eligibility rules**, not a keyword match — and notices when a program has lapsed.
3. One desk that answers three questions at any moment: **what is in process, what is approved, what is paid** — with the evidence behind each.
4. A **2025 ledger built from her own receipts**, reconciled, with the gaps flagged, in a package her accountant can use — instead of a shoebox of forwarded emails.
5. A way to ask out loud, *"Where's my money?"*

> *"I'm a brewer, not a tax attorney or a bookkeeper. Tell me what I qualify for, file it, and give my accountant the books so I can sign and move on."*
> — Marisol, the user this epic is written for

---

## 3. What already exists (reuse inventory)

The prior build is a working product. This epic should reuse it aggressively and only build the deltas.

| Capability | Where it lives | State | Change in this epic |
|---|---|---|---|
| Gmail OAuth + synthetic inbox + email fact extraction | `research/business/.../gmail/`, `email_facts.py`, `demo/gowanus-kettle/inbox.jsonl` | Works with synthetic mailbox; Bedrock for the LLM pass | **Swap to Nicrron**; add onboarding review UI; **reuse the same scan for purchase extraction** |
| Company research (website, BBB, NY DOS, NYC Open Data, news) | `research/company/` | Works | Keep; feed the same profile |
| Program catalog: 33 niches, official links, NY claim counts, form PDFs | `research/legal/catalog/*.toml`, `legal_research/` | Works; keyword/NAICS matching only | **Add rule extraction from the official page** + citations |
| Dossier with per-fact provenance | `research/business/`, `dossier.json` | Works | Extend with eligibility verdicts and ledger links |
| PDF form filling (IT-636, IT-212, IT-643, 8846) | `form-filling/`, `demo/gowanus-kettle/filled/` | Works; stops before submit | Keep as the execution step |
| Status machine + Track UI | `src/pipeline/status.py`, `ui/domain.html` | Works | **Add Claims Desk board + Books tab** |
| Mock portal, mock agency/bank providers | `mock_portal/`, `src/providers/` | Works | Use to simulate approval/payment |
| SurrealDB dossier store | `kb/`, `schemas/surreal/` | Optional / cloud | Keep optional; JSON is enough for the demo |
| Arize tracing | `src/observability/arize.py` | Prior stack | **Replace with PRISM** |
| Anthropic on Bedrock | `src/agent/runtime.py`, `email_facts.py`, `research/company/.../synthesize.py` | Prior stack | **Replace with Nicrron** |
| ElevenLabs | `.env` placeholder only | New | **Voice briefing (P1)** |
| XLSX export | — | New | `openpyxl` for the accountant packet (bundled Python has it) |

**Rule:** every new line either (a) reuses an existing pipeline, or (b) is one of the demo beats. No new infrastructure beyond the sponsor integrations.

---

## 4. What this epic adds

Five capabilities across two slices. Each has a demo beat, an acceptance test, and a PRISM consequence.

### Slice A — Claims Desk (Epic 01a, 11 pts)

#### 4.1 Onboarding: read the inbox, not a form

**Demo beat (0:15–0:35).** Marisol lands on the back office. One button: **Connect Gmail**. The agent scans the synthetic inbox (55 messages: 25 original + 30 receipts), extracts profile facts with the quote and sender for each, and shows a profile card:

- legal name, entity type, NY formation year
- headcount (14), payroll provider (Gusto), payroll totals, tips
- NYC address, NAICS 312120, brewery / taproom
- hires in 2025 (Darnell Reyes, Keisha Monroe — both veterans per DD-214 thread)
- capex (canning line, $186,500, placed in service July 2025), solar (38 kW)
- health plan (Oscar small group), SIMPLE IRA
- accountant (Owen Halloran CPA), tax year (2025), extension filed

The same scan reports **47 purchases** found and queued for the Books tab (below). Then three **conflicts** the agent refuses to guess: headcount 14 (profile) vs 12 paid (March payroll), a ZIP mismatch between the state record and the profile, and a missing DD-214 attachment. Marisol resolves one, defers one, and the agent marks the third **needs your input**. Consent checkbox → **Build my back office**.

**Acceptance**
- The profile is assembled from the inbox and existing research only; every fact carries `source`, `quote`, `confidence`, `captured_at`.
- No fact without a source survives into the profile.
- Conflicts render as **coral exceptions**, never silently resolved.
- Consent is explicit, revocable, and the demo emails are synthetic (`demo: true`).
- A "why do you know this?" click opens the source email.

#### 4.2 Eligibility: read the agency's rules, not keywords

**Demo beat (1:00–1:20).** The agent takes the profile's signals (brewery, 14 employees, two veteran hires, $186.5k capex, 38 kW solar, NY) and produces **candidate programs** from the curated catalog, a live search of official domains, and the program pages themselves. For each candidate it fetches the official page and extracts a **structured rule object**:

```json
{
  "program_id": "nys_hire_a_veteran",
  "form": "IT-643",
  "agency": "NYS Department of Taxation and Finance",
  "source_url": "https://www.tax.ny.gov/.../it643_fill_in.pdf",
  "as_of": "2026-10-17",
  "criteria": [
    {"field": "state", "op": "=", "value": "NY", "quote": "..."},
    {"field": "new_hire_veteran", "op": ">=", "value": 1, "quote": "..."},
    {"field": "wages_first_year", "op": "is", "value": "reported", "quote": "..."}
  ],
  "amount": {"kind": "percent_of_wages", "value": 0.15},
  "deadline": "with the tax return",
  "pre_approval": false
}
```

The desk returns three verdicts per program — **eligible (reasons + citations)**, **needs info (one question)**, **not eligible (why)** — and it is allowed to say **"expired"**. The demo moment: the catalog lists the federal **WOTC**, but the notes say it lapsed for hires after 2025-12-31. The agent **does not open an application**; it shows the lapse and the citation. That is judgment, not keyword matching. Then it surfaces one program the static catalog missed, found by live search on an official domain (e.g., a Con Edison / NYSERDA solar or EV rebate), with the same rule treatment.

**Acceptance**
- Every verdict cites an official URL and the quoted sentence(s) behind it.
- Unknown fields become a **single** question, never a guess.
- Expired/lapsed programs are blocked from the pipeline with the reason.
- Official-host allow-list, robots.txt, rate limit; cached HTML snapshot for replay if the network fails.
- At least one live-fetched program appears in the demo, and one catalog program is correctly rejected.

#### 4.3 Claims Desk: track every application like a receivable

**Demo beat (1:20–1:45).** The desk is a single screen:

```
┌───────────────────────────────────────────────────────────────────────┐
│  CLAIMS DESK          $45,737 identified · $22,535 in process         │
│                       $13,471 approved · $0 paid                       │
├──────────────┬──────────────┬──────────────┬──────────────────────────┤
│ FOUND (3)    │ IN PROCESS   │ APPROVED (1) │ PAID (0)                 │
│ IT-636 $13,471│ IT-643 $15,075│ IT-212 $7,460│  awaiting deposit        │
│ 8846   $9,731│  needs DD-214 │  agency said │  reconcile bank feed     │
│ NYSERDA ...  │  sign & file  │  yes 10/14   │                          │
└──────────────┴──────────────┴──────────────┴──────────────────────────┘
   NEEDS YOU (3): confirm ZIP · upload DD-214 · 6 receipts · IT-643 signature due Fri
```

- **Money semantics are explicit.** "Identified" is an estimate; "approved" is agency evidence; "paid" requires a matched deposit. Never conflate them.
- Each card opens a **detail**: program, amount and formula, deadline, next action, evidence chain (agency receipt, confirmation ID, timestamps), and the agent's decision log.
- The agent proposes the **next action** ("sign IT-643; DD-214 is the only blocker"), and a human approves before anything is submitted.
- **Reconciliation**: simulate the agency paying IT-212. The card moves to `PAYMENT_ISSUED`; no `PAID` until a mock bank row matches amount + reference. Force one mismatch to show the exception.
- Status transitions go only through the status machine (`src/pipeline/status.py`); every transition writes an event with actor, timestamp and evidence.

**Acceptance**
- Four columns map to the canonical statuses; illegal transitions are rejected.
- Every card carries amount, source/form, next action, deadline, evidence.
- `PAYMENT_ISSUED` is visually distinct from `PAYMENT_CONFIRMED`; the UI says "agency says paid — deposit not yet matched" until reconciled.
- The exception queue is the only place the user is asked to act.
- A demo reset restores a clean, deterministic state.

### Slice B — Claim-Ready Books (Epic 01b, 5 pts)

#### 4.4 EOY ledger: purchases from the same inbox

**Demo beat (0:35–1:00).** The onboarding scan also answered a second question Marisol could not: *"What did I actually spend in 2025?"* Open the **Books** tab:

```
BOOKS · TAX YEAR 2025                    47 transactions · 6 need receipts
Revenue        $2,140,000      (taproom + wholesale summaries)
Expenses       $1,437,300      (COGS, payroll, rent, utilities, insurance, …)
Capital        $228,000        (canning line $186,500 · taproom equipment $41,500)
Reconciled     Δ $0            · 2 duplicates merged · 6 missing receipts
```

The ledger table: date, vendor, description, amount, category, tax treatment, payment account, **source email**, confidence, flag. Clicking the canning line opens the Chase financing + invoice emails; clicking the tips line opens the Square/Gusto threads. A filter shows only the **exceptions** (duplicates, missing receipts, capital-vs-expense questions).

**How it is built (and why it is safe):**
- Deterministic first: sender/domain rules (Gusto, Chase, Con Ed, Square, known vendors), amount/date regexes, statement totals.
- Then Nicrron reads a bounded subset of purchase-like messages and returns strict JSON with a **mandatory verbatim quote** per line. A value survives only if it (or its quote) is in the cited email.
- Normalization: vendor, date (ISO), amount in cents, direction (purchase/sale), payment account, category.
- **Categories** (accountant-friendly, not tax-advice-fancy): payroll & payroll taxes, COGS — ingredients, COGS — packaging, rent, utilities, insurance, software & subscriptions, professional fees, marketing, repairs & maintenance, licenses & permits, travel, **capital assets**, other.
- **Tax treatment** is a *flag for review*, not a conclusion: `expense`, `capitalized`, `needs_review`. Capital assets are matched to the fixed-asset schedule and to **IT-212** (the $186,500 canning line); tips are matched to **IRS 8846** ($148,600); veteran wages to **IT-643**. One source of truth: the ledger numbers and the credit forms cannot disagree.
- **Reconciliation:** dedupe (same vendor + amount + date ± 2 days after normalization), compare monthly statement totals where present, flag missing receipts, flag revenue lines separately. A `reconciled_delta` is computed and shown.
- **Revenue** is kept separate from expenses: Square weekly summaries + wholesale invoices, clearly labeled as summaries, not audited books.

**Acceptance**
- ≥40 transactions extracted from the synthetic inbox, each with a source email id and quote.
- 2 duplicates detected and merged; 6 missing receipts flagged; `reconciled_delta` shown.
- Capex total ties exactly to the $186,500 IT-212 basis; tips tie to the $148,600 8846 basis.
- No line without evidence survives; every line shows confidence and category.
- Deterministic-first, LLM-second; the LLM cannot add a transaction that is not in the mail.
- The Books tab is read-only except for a user override (`edited_by_user`), which is recorded.

#### 4.5 Accountant packet: prepared for review, not filed

**Demo beat (1:00–1:10, continues the books beat).** One button: **Prepare accountant packet**. A download appears:

```
Owen Halloran CPA — Gowanus Kettle Brewing Co. LLC — TY2025
├── 01_cover.pdf            one page: what this is, what it is not, what changed
├── 02_summary.xlsx         P&L summary, category totals, capital schedule
├── 03_ledger.csv           every transaction, source email id, confidence, flags
├── 04_evidence_index.pdf   email subject/date/sender per ledger line
├── 05_open_questions.pdf   for the accountant, not answered by us
└── 06_credits.pdf          the four applications, amounts, statuses, form evidence
```

The packet has a cover line that matters: **"Prepared for professional review. Not filed. Not tax advice."** Then a list of questions the agent refuses to answer for the accountant: §179 vs bonus depreciation on the canning line; NY vs federal treatment of the solar/EV assets; meals vs tips; state apportionment; how IT-212 interacts with the federal credits. The email draft to Owen is pre-filled with the packet summary and the three blocking questions.

**Acceptance**
- Packet generates from the ledger, not from a template with hardcoded numbers.
- Cover states synthetic data, tax year, prepared date, and *not filed / not tax advice*.
- Open questions are **questions**, not conclusions; no tax advice.
- XLSX + CSV open cleanly; totals match the Books tab exactly.
- The credits section reuses the Claims Desk statuses (one source of truth).
- A "send to accountant" action is a mail draft/download — never an automatic email.

### P1 — Voice CFO (stretch, ElevenLabs)

**Demo beat (live pitch only).** Press and hold the mic: *"Where's my money?"* The desk answers with the real ledger: *"You have $45,737 identified. $15,075 is in process and needs your DD-214; $7,460 was approved on October 14 and is expected in November; nothing has been deposited yet. Your IT-643 signature is due Friday."*

Two modes, pick the cheap one that fits the time: **voice onboarding** (five spoken questions) or **spoken briefing** (ElevenLabs TTS over the same `get_claims_summary` tool result). If ElevenLabs Agents are used, add the **PRISM post-call webhook** (§7.3) so voice calls appear as PRISM trajectories.

**Acceptance**
- The answer reads from the same ledger as the dashboard (no separate script).
- It states identified vs in-process vs approved vs paid correctly.
- Fallback: a transcript card shows the same answer. Voice never blocks the demo.

---

## 5. Demo script

### 5.1 Two-minute video (shot list)

| Time | Screen | Action | The line that matters |
|---|---|---|---|
| 0:00 | Title / Marisol | Stat card: **$45,737 owed · 55 emails · 47 purchases · 4 forms · 2025 return on extension** | "Marisol runs a brewery. She's owed $45,737, and her accountant is waiting on the 2025 books." |
| 0:15 | Onboarding | Connect synthetic Gmail → scan → profile with citations → 3 conflicts | "The agent learns her business from her inbox — every fact points to the email it came from." |
| 0:35 | Books | 47-transaction ledger → click canning line → missing receipts / duplicates → prepare packet | "The same inbox is her 2025 ledger: reconciled, gaps flagged, packaged for her accountant — prepared for review, not filed." |
| 1:00 | Eligibility | Fetch `tax.ny.gov` pages → rule cards → WOTC flagged expired → one live program found | "It reads the agency's own rules. When a program lapsed, it says so instead of filing." |
| 1:20 | Claims Desk | Four columns; IT-212 to approved; simulate deposit; mismatch exception | "Every application is a receivable: in process, approved, paid — and payment needs a matching deposit, not just an agency claim." |
| 1:45 | PRISM | Steps tab: 12 steps; alert firing; root-cause cluster; v2 passing | "One run, twelve auditable steps. We found the failure, fixed it, and PRISM proves the fix." |
| 2:00 | Close | Logo + repo | "The money is already hers. We built the back office that gets it home — and the books that prove it." |

Voice is **not** in the 2-minute video (P1); it appears in the live pitch if it is green.

### 5.2 Three-minute live pitch (same spine, more proof)

1. **Problem (20s):** small businesses leave credits unclaimed and hand their accountant a shoebox. Marisol's $45,737 is in four forms; her 2025 return is on extension; the receipts are in her inbox.
2. **Demo (110s):** run the five beats live — onboarding, books, eligibility, desk, packet. If the network or OAuth is flaky, the cache and synthetic inbox keep the story intact.
3. **PRISM proofs (40s):** Steps session (12 steps), alert firing, root-cause cluster + v2.
4. **Why it matters (10s):** the same desk works for any jurisdiction and any program; the reconciled ledger is the receipt.
5. **Close (10s):** "Build with PRISM, model calls through Nicrron, voice by ElevenLabs. The money is already hers."

### 5.3 The failure → fix story (rehearse this)

**v1 failure (3+ runs):** the eligibility extractor reads the page but returns a *plausible* rule that is not in the text — e.g., it invents a `min_employees` threshold, or drops the "NY barrel production" requirement. The form still fills; the run is "successful" but the claim is wrong. PRISM's Intelligence cluster groups the failed runs; the cause is "evidence not required in the extraction schema".

**v2 fix:** the extraction schema requires a `quote` for every criterion, the validator rejects any criterion whose quote is not a substring of the fetched page, and a `citation_required` evaluator scores v1 vs v2 on the same ten pages. Same inputs, v2 passes. That is the required Root Cause + "v2 no longer failing" proof, and it is the most honest part of the demo.

**Backup failure (if time):** two different vendors' charges are merged as duplicates (or a capital purchase is categorized as an expense), the ledger delta is wrong, and v2 fixes the normalization/dedupe key. This is a second, operations-native failure story.

---

## 6. Architecture

```
Marisol (browser)
   │  onboarding · claims desk · books · accountant packet · voice
   ▼
Flask UI ────────────────────────────────────────────────────────┐
   │                                                            │
   ▼                                                            │
Agent API (Flask/FastAPI)                                       │
   ├── Nicrron gateway (OpenAI-compatible, one key)             │  all model calls
   ├── Gmail adapter (synthetic inbox now, OAuth later)         │
   ├── Fact extractor (profile)                                 │
   ├── Purchase extractor + ledger normalizer                   │
   ├── Ledger reconciliation (dedupe, totals, missing receipts) │
   ├── Accountant packet builder (XLSX/CSV/PDF)                 │
   ├── Agency fetcher (official-host allow-list, cache)         │
   ├── Eligibility rules engine (deterministic + LLM)           │
   ├── Dossier + ledger (JSON now, Surreal-ready)               │
   ├── Status machine + evidence providers (mock)               │
   ├── Claims Desk API (pipeline, forecast, exceptions)         │
   └── PRISM emitter (traces, sessions, alert hooks) ───────────┤
   │                                                            │
   ▼                                                            │
ElevenLabs (voice, P1) ──► PRISM voice webhook (optional) ──────┘
```

**Run model.** One back-office run = one `session_id` = one PRISM trajectory: scan → facts → purchases → ledger → reconcile → candidates → fetch → rules → match → form → approve → packet. Every tool call is a step. The dashboard, the ledger and the packet read the same ledger the agent writes, so what the user sees and what PRISM sees cannot diverge.

**Component map**

| Layer | Path (existing or new) |
|---|---|
| Desk UI | `ui/` (extend) + new `ui/desk.html` |
| Books UI | new `ui/books.html` (read-only ledger + exceptions) |
| Onboarding | `research/business/.../web/` + new review screen |
| Agent tools | `src/agent/tools.py` (extend) |
| Purchase extraction | reuse `email_facts.py` pattern; new `src/ledger/extract.py` |
| Ledger + reconciliation | new `src/ledger/reconcile.py`; `src/persistence.py` |
| Accountant packet | new `src/ledger/packet.py` (`openpyxl`, CSV, HTML→PDF) |
| Eligibility | `research/legal/` + new `eligibility_rules.py` |
| Model adapter | new `src/agent/nicrron.py` |
| PRISM emitter | new `src/observability/prism.py` (replaces `arize.py`) |
| Status | `src/pipeline/status.py` |
| Voice | new `src/voice.py` (P1) |
| Demo fixtures | `demo/gowanus-kettle/` (expand inbox), `fixtures/demo-seed.json` |

---

## 7. Platform integrations

### 7.1 Nicrron (required)

- **Endpoint:** OpenAI-compatible, `https://api.nicrron.ai/v1`; env `NICRRON_API_KEY`, `NICRRON_BASE_URL`, `NICRRON_MODEL`.
- **Default model:** `nicrron/auto` (verified: routes to a Claude Haiku family model; response returned normally). Explicit models for the swap demo: `anthropic/claude-sonnet-5`, `openai/gpt-5.5`, etc. (list: `nicrron.ai/docs/models`).
- **Where it replaces Bedrock:**
  1. `email_facts.llm_facts()` — email → strict JSON facts.
  2. `research/company/.../synthesize.py` — company summary + NAICS guess.
  3. New purchase extractor — email → transaction JSON with quotes.
  4. New eligibility extractor — page text → rule JSON.
  5. New packet writer — ledger → open questions + cover copy.
- **Adapter contract** (`src/agent/nicrron.py`):
  - `complete_json(messages, schema, model=...)` — strict JSON, repair-once on parse failure, timeout + retry.
  - Returns `{content, model, provider, latency_ms, usage}`; every call is wrapped by the PRISM emitter.
  - Model can be overridden per request for the "same guardrail, different model" demo.
- **Rules:** no real PII; prompts treat email/agency text as delimited untrusted data; never send raw SSN/EIN in prompts; cache by prompt hash for the demo.
- **Credits:** $260 account (confirmed in dashboard). Expire Oct 18, 6:00 PM ET — use them today.

### 7.2 PRISM (required) — the three Money Operations proofs

**Status: credential already verified.** Project `6e1051f7-8dce-498f-9846-d6acaa087737`, host `https://api.prism.blockconvey.com`, key in `.env` (never commit). Handshake returned `ok: true` and stored a test trace at 2026-10-17T16:22Z.

**Instrumentation:** use the HTTP ingest path from the setup brief (`POST /api/traces`) or `pip install "prismtrace-sdk>=0.5.1"`. Send one trace per model call and per significant tool step, with `session_id` = back-office run id and `agent_id = moneyfinder-backoffice`; attach `model`, `step`, `tool`, `prompt_version`, `latency_ms`, `cost_usd`, `status`. Never send raw PII; PRISM scrubs server-side, but do not rely on it.

| Proof | Required | How we produce it | Where the judge looks | Screenshot to capture |
|---|---|---|---|---|
| **1. Sessions** | One run, **6+ steps** | One run, **12 steps**: `gmail_scan → extract_facts → extract_purchases → categorize_ledger → reconcile_ledger → program_candidates → agency_fetch → eligibility_extract → match_score → form_prep → human_approve → build_accountant_packet` | **Steps** tab of the run | Steps list + one expanded step with tool, input, output |
| **2. Alert** | Alert fires on a real run | Alert rule: **reconciliation delta > $250** (plus failed tool call / latency > 20s as backups). Force a real failure: remove one receipt email from the demo fixture, or mutate a ledger amount so the delta breaks | **Alerts** page + the flagged run | Rule definition + firing event + the run it fired on |
| **3. Root Cause** | Cluster of **3+ failed runs** + cause, then **v2 same inputs no longer failing** | Replay the "invented eligibility rule" scenario 5× (v1 prompt). Cluster appears. Fix = quote-required schema + validator. Replay the same 5 pages on v2: pass | **Intelligence / Root Cause** tab, then v2 run | Cluster (3+), cause sentence, v1 vs v2 results |

**Before fixing anything:** get **50+ runs** into PRISM (the doc's explicit instruction). A `scripts/prism_seed_runs.py` harness replays the demo scenarios and sends 50+ traces with varied session ids; it runs once and is not part of the demo path. This also gives the Root Cause clusters real data.

**Our cause sentence (write it on the slide):** *"The extractor treated a plausible rule as a fact because the schema did not require a verbatim quote from the agency page."*

**Optional bonus (Trust & Risk evidence):** an enforce-mode guardrail that blocks account numbers / SSNs / "guaranteed returns" in outbound text, and a **Block check** screenshot. Only if P0 is green.

**Don't rely on the onboarding brief's framework wiring.** The PRISM project's onboarding brief is profiled for an ElevenLabs voice app on Vercel AI; our app is Python/Flask. The HTTP ingest path is language-agnostic and is the source of truth.

### 7.3 ElevenLabs (optional sponsor, P1)

- **Account:** signed in; Creator-plan coupon is redeemed through the ElevenLabs Discord `#coupon-codes` → *Start Redemption* → select event → event email (per the builder pack). Confirm the plan before depending on it.
- **Build:** one Agent ("Marisol's Back Office") + one stock voice. Tools: `get_claims_summary`, `get_next_action`, `get_proof`. Voice onboarding: five questions mapped to the same profile schema. Spoken briefing reads the same ledger.
- **PRISM voice connection (optional, high differentiator):** in the ElevenLabs dashboard add a post-call webhook to
  `https://api.prism.blockconvey.com/api/connectors/elevenlabs/webhook?project_id=6e1051f7-8dce-498f-9846-d6acaa087737`
  and subscribe to **`post_call_transcription` only** (do **not** enable `post_call_audio`). Store the signing secret as the project's ElevenLabs credential. Calls then appear as PRISM trajectories.
- **Fallback:** server-side TTS of the briefing text only — no agent, no dependency on the coupon. Voice is never on the critical path.

### 7.4 Gmail (core, not a sponsor)

- Scope: `gmail.readonly` only. Demo runs on `demo/gowanus-kettle/inbox.jsonl` (expanded to ~55 synthetic messages), no real account.
- If a real account is connected on stage: show the consent screen, the scope, and a disconnect button. Never store bodies beyond derived facts and extracted transactions. Never show real personal data. `.example` addresses only in the demo.
- The onboarding review screen is the privacy moment: the user sees exactly what the agent learned and can delete any fact or ledger line.

### 7.5 Ninoo (optional)

Not required if we ship our own Flask UI — the rule is *"model calls through the Nicrron API **or** your app through Ninoo."* We satisfy it with Nicrron. Ninoo Builder is a fallback if the dashboard UI is behind schedule; do not spend P0 time on it.

---

## 8. Data model

```text
profile        id, legal_name, entity_type, state, naics, headcount, address,
               signals[], consent, updated_at
fact           profile_id, key, value, source_kind, source_ref(quote), confidence,
               captured_at, edited_by_user, requires_confirmation

program        id, name, agency, jurisdiction, official_url, as_of, status,
               amount_formula, deadline, pre_approval, source_snapshot
criterion      program_id, field, op, value, quote, source_url
match          profile_id, program_id, verdict(eligible|needs_info|not_eligible|expired),
               reasons[], questions[], confidence, run_id
application    id, profile_id, program_id, amount_estimate_cents, status, submitted_at,
               expected_by, confirmation_id, form_hash, next_action, evidence[]
event          application_id, from_status, to_status, actor, evidence_kind, source, note, at
evidence       application_id, kind(submission|agency_receipt|bank_match), source, ref, payload

transaction    id, year, date, vendor, description, amount_cents, direction(purchase|sale),
               category, tax_treatment(expense|capitalized|needs_review),
               payment_account, source_message_id, source_quote, confidence,
               needs_receipt, duplicate_of, status(verified|needs_review|excluded),
               edited_by_user
ledger_summary year, revenue_cents, expense_cents_by_category{}, capital_cents,
               payroll_cents, tips_cents, reconciled_delta_cents, missing_receipts,
               duplicate_count
packet         id, year, generated_at, files[], open_questions[], exclusions[],
               status(prepared_for_review)
```

**Status → desk column**

| Column | Statuses |
|---|---|
| Found | `MATCH_FOUND`, `FORM_READY` |
| In process | `USER_APPROVED`, `SUBMITTED`, `CLAIM_RECEIVED`, `PROCESSING`, `NEEDS_DOCS` |
| Approved | `APPROVED` |
| Paid | `PAYMENT_ISSUED`*, `PAYMENT_CONFIRMED` |
| Not shown | `REJECTED`, `STOPPED_BY_USER` → exceptions/archive |

\* `PAYMENT_ISSUED` shows as **"Paid — awaiting deposit"** in the Paid column, visually distinct from `PAYMENT_CONFIRMED` ("Paid — deposit matched"). Never label agency evidence as money in the bank.

**Money semantics (say it on stage):**
- **Identified** = estimated, not filed.
- **In process** = filed or awaiting signature/docs.
- **Approved** = agency evidence, not cash.
- **Paid** = deposit matched. Only then is it money.
- **Booked** = in the ledger with a source email; **reconciled** = totals agree and exceptions are listed.

**One source of truth:** the ledger's capex ($186,500) is the IT-212 basis; its tips ($148,600) are the 8846 basis; its veteran wages feed IT-643. If the ledger and the form disagree, the packet refuses to generate.

---

## 9. Agent loop, tools, guardrails

**Loop:** plan → choose tool → execute deterministic Python where possible → write event → observe → continue until an approval gate or done. The model never writes directly to the ledger without a tool and an event.

| Tool | Allowed | Forbidden |
|---|---|---|
| `scan_inbox` | Read synthetic inbox, emit facts/transactions with quotes | Store bodies; read unrelated mail |
| `build_profile` | Merge facts, flag conflicts | Invent values |
| `extract_purchases` | Emit transactions with quotes | Add a transaction not in the mail |
| `categorize_ledger` | Category + tax-treatment flag | Conclude tax advice |
| `reconcile_ledger` | Dedupe, totals, missing receipts, delta | Hide a mismatch |
| `find_candidates` | Catalog + official-domain search | Fetch non-official hosts |
| `fetch_program_page` | Official URL, cache, robots-aware | Bypass paywall/robots |
| `extract_eligibility` | Rule JSON with mandatory quotes | Emit a criterion without a quote |
| `score_match` | Verdict + reasons + one question | Guess a missing field |
| `prepare_application` | Map facts → fields with provenance | Clear a conflict |
| `request_approval` | Pause for the human | Auto-submit |
| `submit_mock` | Mock portal only | Real agency submission |
| `poll_status` | Read mock provider | Fabricate APPROVED |
| `reconcile_deposit` | Match amount + reference | Mark PAID on agency claim alone |
| `build_accountant_packet` | Generate XLSX/CSV/PDF from the ledger | Answer tax questions for the accountant |

**Failure handling:** invalid JSON → repair once, then fail the step visibly; no quote → drop the line/criterion; page stale/blocked → mark `stale` and use the cached snapshot with `as_of`; conflict → exception queue; tool timeout → retry once, then alert; packet mismatch → refuse to generate.

**Guardrails (Trust & Risk evidence):** human approval before any submit; no real agency filing; block SSN/EIN/account-number patterns in outbound text; "not tax or legal advice" label on the packet; accountant remains the professional; synthetic data only; an audit log that cannot be rewritten.

---

## 10. Build plan (today, timeboxed)

It is ~13:00. Assume demos/submission 5:00–6:00 PM.

> **Three-person execution:** the repo's `docs/TEAM_PLAN.md` supersedes this four-lane table. Thuy owns onboarding UI + PRISM dashboard/proofs, Kenan owns the UI shell + Desk/Books + the demo, Richard owns the agent/ledger/PRISM emitter. The **demo spine** in `TEAM_PLAN.md` §6 is the real P0; this table is the scope inventory behind it.

| Window | Lane A — Platform | Lane B — Agent / ledger | Lane C — UI | Lane D — Demo / voice |
|---|---|---|---|---|
| 13:00–13:30 | ✅ Env + PRISM credential (done); Nicrron adapter; PRISM emitter; run the existing demo once | Baseline: email facts + legal match on Gowanus; expand synthetic inbox to ~55 messages with receipts | Desk + Books wireframes against the seed | ElevenLabs coupon/agent; write demo script; capture v1 screenshots |
| 13:30–14:30 | PRISM emitter on every model/tool call; session id per run; 50-run seed script | Purchase extractor + ledger normalizer; dedupe + missing-receipt flags | Onboarding review + Books tab (ledger table, summary, exceptions) | Voice agent tools + TTS fallback |
| 14:30–15:30 | Alert rule (recon delta) + forced failure; root-cause replay harness (v1 ×5) | Eligibility rules + quote validator + WOTC expiry; packet builder (XLSX/CSV) | Desk board + detail + exception queue; packet download screen | Record the 2-min video (draft) |
| 15:30–16:30 | Root Cause screenshots; optional guardrail/block check | v2 schema + evaluator; v1/v2 rerun; reconciliation + deposit match | Polish money semantics, reset, mobile; packet preview | Final video + Builderbase/Discord submission |
| 16:30–17:00 | Buffer: proof capture, README, repo public | Buffer | Buffer | Rehearse the 3-min live pitch |

**Cut line (in order):** voice agent → live web search (use cached snapshot) → forecast → optional guardrail. **Never cut:** PRISM credential, 12-step session, alert, root-cause cluster + v2, the desk statuses, the ledger + packet.

---

## 11. Task checklist

### P0 — required for the demo

**Platform**
- [ ] `src/agent/nicrron.py` adapter; env wired; email facts + synthesize + extractors use it — *accept: one real call returns strict JSON; no Bedrock on the demo path*
- [ ] `src/observability/prism.py`; emit a trace per model call/tool step with `session_id`, `agent_id`, model, latency, status — *accept: 1 run visible in PRISM with 6+ steps (target 12)*
- [ ] `scripts/prism_seed_runs.py`; 50+ runs seeded — *accept: PRISM shows 50+ runs; Root Cause has data*
- [ ] Alert rule (reconc delta > $250) + one real firing — *accept: alert event screenshot*
- [ ] Root Cause v1 cluster (3+ failed) + v2 rerun passes — *accept: cluster + cause + v1/v2 comparison*
- [ ] `.env.example` updated (names only), `.env` gitignored — *accept: `git status` has no secret*

**Agent / ledger**
- [ ] Expand `demo/gowanus-kettle/inbox.jsonl` to ~55 synthetic messages with 30 receipts/invoices across categories — *accept: ≥40 transactions extractable; no real data*
- [ ] `extract_purchases` with mandatory quote per transaction — *accept: rejecting one planted hallucination*
- [ ] Category + tax-treatment flags; capital assets schedule — *accept: canning line flagged capitalized*
- [ ] Reconciliation: dedupe (≥2), missing receipts (≥6), `reconciled_delta` — *accept: delta visible, duplicates merged*
- [ ] Capex/tips tie-out to IT-212 / 8846 bases — *accept: packet numbers match credit forms*
- [ ] Accountant packet: XLSX + CSV + cover + open questions + evidence index — *accept: files open; totals match Books tab*
- [ ] Official-host allow-list + cached page snapshot — *accept: page fetched once, cached, replay works offline*
- [ ] `extract_eligibility` schema requires verbatim quotes; validator rejects non-substring quotes — *accept: rejecting one planted hallucination*
- [ ] Expired/lapsed program handling (WOTC) — *accept: WOTC appears as expired with citation, no application created*
- [ ] Live search finds at least one official program not in the catalog — *accept: program card with source URL*
- [ ] Verdicts: eligible / needs info / not eligible, with reasons + confidence — *accept: three verdicts visible in the demo*
- [ ] Reconciliation: agency paid vs deposit matched + one mismatch exception — *accept: `PAYMENT_ISSUED` ≠ `PAYMENT_CONFIRMED` in UI*

**UI**
- [ ] Onboarding: connect → scan progress → profile facts with source → conflicts → consent — *accept: ~55-message scan, 20+ facts, 3 conflicts*
- [ ] Books tab: summary, ledger table, exceptions filter, source-email click — *accept: 40+ rows, 6 missing receipts, 2 duplicates*
- [ ] Accountant packet download + preview — *accept: XLSX and CSV download from the UI*
- [ ] Claims Desk: four columns + totals + next action + evidence detail — *accept: all four columns populated in the demo seed*
- [ ] Exception queue ("Needs you") — *accept: only actionable items; no wall of forms*
- [ ] Money-semantics copy ("agency says paid" vs "deposit matched"; booked vs reconciled) — *accept: no green "Paid" before a matched deposit*
- [ ] Demo reset + deterministic seed — *accept: one command restores the scene*

**Submission / demo**
- [ ] 2-min video under the limit, shows five beats + PRISM proofs — *accept: file exported and uploaded*
- [ ] Public repo, README updated with sponsor tools + architecture — *accept: link opens in incognito*
- [ ] Builderbase/Discord submission with repo, video, tool list — *accept: confirmation visible*
- [ ] Rehearsed 3-min live pitch with fallback screenshots — *accept: one clean run*

### P1 — stretch

- [ ] ElevenLabs voice agent + stock voice + briefing from the ledger — *accept: spoken answer matches dashboard*
- [ ] PRISM ElevenLabs post-call webhook — *accept: one call appears as a PRISM trajectory*
- [ ] Optional enforce-mode guardrail + block check screenshot — *accept: block shown and honoured*
- [ ] Cash-in forecast bar — *accept: labeled estimate/confidence*
- [ ] Reconciled-deposit auto-match from a mock bank feed — *accept: IT-212 moves to `PAYMENT_CONFIRMED`*

---

## 12. PRISM proofs checklist (judge-facing)

Capture these **as files** during the build so the video and pitch can fall back to them:

- [ ] **Credential** — setup-doctor screenshot: `credential_ok: true`, test trace stored.
- [ ] **50+ runs** — Runs list with a count ≥50 (before any fix).
- [ ] **Session** — Steps tab, one run, **12 named steps** (scan → facts → purchases → ledger → reconcile → candidates → fetch → rules → match → form → approve → packet), one step expanded showing tool + input + output.
- [ ] **Alert** — rule definition + the firing event + the failed run it fired on.
- [ ] **Root Cause** — Intelligence cluster of **3+ failed runs**, its cause, and our one-sentence "why".
- [ ] **v2 proof** — the same inputs on v2 scoring/passing, side by side with v1.
- [ ] **Cause sentence on a slide** — *"The extractor treated a plausible rule as a fact because the schema did not require a verbatim quote from the agency page."*

---

## 13. Judging alignment

| Criterion | Our evidence |
|---|---|
| Real product, not a slide | Working back office: 4 applications, reconciled 2025 ledger, downloadable accountant packet, live official-page fetch, reconciled payments |
| Track fit (Money Operations) | AR pipeline, exception queue, expense capture + reconciliation, accountant handoff, CFO voice |
| Required platform — PRISM | All three proofs + 50+ runs + cause sentence |
| Required platform — Nicrron | Every model call through one OpenAI-compatible key; live model swap |
| Sponsor bonus — ElevenLabs | Spoken briefing + optional PRISM voice trajectory |
| Depth of agent | 12 auditable steps per run; approval gates; evidence required on every line |
| Tangible artifact | The accountant packet — judges can open the XLSX |
| Honesty | Synthetic identities; estimates vs agency evidence vs matched deposit; books prepared for review, not filed; not tax advice |
| Demo quality | One deterministic scene, reset button, screenshot fallbacks |

**Pitch line:** *"MoneyFinder finds the money. The back office files it, tracks it until the deposit clears, and hands your accountant books that are ready to sign."*

**Honesty lines to keep (from v1):** using the free official forms yourself is always an option; we sell the paperwork and the tracking, not access; synthetic identities only; not legal or tax advice; agency approval is not a bank deposit; the accountant remains the professional.

---

## 14. Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Gmail OAuth fails on stage | Medium | Demo uses the synthetic inbox; OAuth is a 20-second optional beat |
| Agency site blocks / slow | Medium | Cached official snapshots with `as_of`; one live fetch as a bonus; Firecrawl fallback |
| Ledger misclassification / false dedupe | Medium | Deterministic-first + quote-required LLM; confidence + review queue; only 2 dedupes in the demo fixture |
| Packet numbers disagree with credits | Low | One source of truth; packet refuses to generate on mismatch |
| Accountant-handoff overreach (advice) | Medium | Open questions, not conclusions; "prepared for review, not filed"; no tax advice |
| Nicrron latency or a bad route | Low | 20s timeout, one retry, `nicrron/auto` + explicit fallback; cache demo prompts |
| PRISM 200 runs/day analysed | Low | Seed 50, reuse session ids; don't spam |
| 50+ runs too slow | Medium | Batch harness, short prompts, parallel requests |
| Root Cause cluster doesn't form | Medium | Fail the same scenario deliberately 5×; use the forced recon alert as backup |
| ElevenLabs coupon/plan delayed | Medium | TTS-only fallback; voice is P1; no judging dependency |
| Time — UI behind | High | Board/ledger tables first, detail second, forecast third; screenshot fallback in video |
| Form filling flaky | Medium | Existing filled PDFs on disk; stop-before-submit; mock portal |
| Real data exposure | Low | `.example` only; `.env` gitignored; no real bank/agency logins |

---

## 15. Estimate (story-pointing)

The original 13-point cap is respected by splitting the work into two pointed slices. Both are P0; together they are the demo.

**Slice A — Claims Desk (Epic 01a): 11 pts.**

- O = 10h, M = 14h, P = 21h
- `E = (10 + 4×14 + 21) / 6 = 14.5h`; `σ = (21−10)/6 = 1.8h`; p85 ≈ **16.3h**
- Factor: **1.3 h/pt**. Reference class: hand-me-up "Design direction A" (5 pts, 5h actual → seed 1.0 h/pt). Flags: existing repo reuse (Gmail, catalog, form filling, status machine) **−0.3**; first-time sponsor/API integrations (PRISM, Nicrron) and a one-day event **+0.6** → 1.3.

**Slice B — Claim-Ready Books (Epic 01b): 5 pts.**

- O = 3h, M = 5h, P = 8h
- `E = (3 + 4×5 + 8) / 6 = 5.2h`; `σ = 0.8h`; p85 ≈ **6.0h**
- Factor: **1.0 h/pt**. Reuses the same inbox scan and provenance pattern; new work is normalization, reconciliation and the XLSX/CSV packet.

**P0 total: 16 pts, E ≈ 19.7h, σ ≈ 2.0h, p85 ≈ 22.3h.**

- Capacity check for the actual team — **3 builders (Thuy, Kenan, Richard) × ~5h = 15 person-hours** — is below P0's E≈19.7h. The **demo spine** is therefore the real P0: onboarding, ledger + packet (XLSX/CSV), desk statuses + exceptions, PRISM 12-step session/alert/root-cause-v2, video. Deferred unless green before 15:35: live agency fetch, ElevenLabs voice, forecast, packet PDFs, optional guardrail. Full lanes, cut order and per-person acceptance criteria: repo `docs/TEAM_PLAN.md` §5–§6.
- **P1 — Voice & showcase: 5 pts.** O = 3h, M = 5h, P = 8h → E ≈ 5.2h; starts only after the three PRISM proofs are captured.

**If both slices and voice land:** 21 pts, E ≈ 24.9h (P1 is bonus).

---

## 16. Open questions / assumptions

1. **Submission time** — assumed 5:00–6:00 PM today; confirm in Discord/Builderbase. If earlier, cut P1 immediately.
2. **Team size** — three builders: Thuy (design, PRISM, repo), Kenan (UI, demo), Richard (agent, ledger, platform). The demo spine fits ~15 person-hours; live fetch/voice/forecast/packet PDFs are deferred (see `docs/TEAM_PLAN.md` §6).
3. **PRISM billing code** `MONEYTALKS#2` — project exists and the key works; confirm the code is redeemed under Settings → Billing.
4. **ElevenLabs plan** — coupon redemption pending; TTS-only fallback regardless.
5. **Ninoo** — not used; the Nicrron API satisfies the required platform. Revisit only if the UI lane is behind.
6. **Deployment** — not required for the demo; a public GitHub repo + video are. Deploy only if time remains.
7. **Data** — synthetic only. No real card numbers, bank logins, or personal financial details, per the builder pack.
8. **Accountant packet format** — XLSX + CSV is the must; PDF cover/questions are nice-to-have (HTML → print). If `openpyxl` is missing from the app env, fall back to CSV + Markdown and add it to `requirements.txt`.

---

## 17. Appendix

### 17.1 Environment (names only — values live in the gitignored `.env`)

```bash
NICRRON_API_KEY=            # required sponsor
NICRRON_BASE_URL=https://api.nicrron.ai/v1
NICRRON_MODEL=nicrron/auto
PRISMTRACE_API_KEY=         # required sponsor; verified 2026-10-17
PRISMTRACE_PROJECT_ID=6e1051f7-8dce-498f-9846-d6acaa087737
PRISMTRACE_HOST=https://api.prism.blockconvey.com
ELEVENLABS_API_KEY=         # optional
ELEVENLABS_AGENT_ID=
ELEVENLABS_VOICE_ID=
```

### 17.2 Useful commands

```bash
make demo                 # existing Send + Track demo on :8000
make demo-seed            # load the synthetic Gowanus business
make legal-match DOMAIN=gowanuskettle.example
make fill SLUG=gowanuskettle-example
git status                # must never show .env
```

### 17.3 Sample ledger row

```json
{
  "id": "txn_2025_0042",
  "year": 2025,
  "date": "2025-07-28",
  "vendor": "ProBrew Equipment",
  "description": "Canning line — 24-head filler/seamer, installed",
  "amount_cents": 18650000,
  "direction": "purchase",
  "category": "capital_assets",
  "tax_treatment": "capitalized",
  "payment_account": "Chase for Business ...4410 (equipment financing)",
  "source_message_id": "synthetic-gk-0xx",
  "source_quote": "invoice total $186,500.00, placed in service July 28, 2025",
  "confidence": 0.98,
  "needs_receipt": false,
  "duplicate_of": null,
  "status": "verified"
}
```

### 17.4 Accountant packet contents

```text
01_cover.pdf            Prepared for professional review. Not filed. Not tax advice. Synthetic demo data.
02_summary.xlsx         TY2025: revenue, expenses by category, capital schedule, payroll, tips, net
03_ledger.csv           every transaction with source email id, confidence, flags
04_evidence_index.pdf   email subject/date/sender for each ledger line
05_open_questions.pdf   §179 vs bonus depreciation; NY/federal solar treatment; meals vs tips;
                        state apportionment; IT-212 interaction with federal credits
06_credits.pdf          IT-636 / IT-212 / IT-643 / 8846: amounts, statuses, form evidence
```

### 17.5 Sample PRISM trace payload (one tool step)

```json
{
  "project_id": "<prism project id>",
  "model": "nicrron/auto",
  "session_id": "backoffice-run-it643-001",
  "agent_id": "moneyfinder-backoffice",
  "input_messages": [{"role": "user", "content": "[step:extract_purchases] messages=<inbox batch 3>"}],
  "output_message": "{\"transactions\":[...]}",
  "latency_ms": 940,
  "metadata": {"step": "extract_purchases", "prompt_version": "ledger-v1", "tool": "extract_purchases", "status": "ok"}
}
```

### 17.6 Voice system prompt (ElevenLabs, P1)

> You are Marisol's back office for Gowanus Kettle Brewing. Answer only from `get_claims_summary`. Always distinguish identified, in process, approved, and paid, and book vs reconciled. Never say money has arrived unless a deposit is matched. Never give tax or legal advice; offer the next action and name the accountant for tax questions. Keep answers under 30 seconds.

### 17.7 Screenshot list for the submission folder

`prism-credential.png` · `prism-50-runs.png` · `prism-session-steps.png` · `prism-alert.png` · `prism-root-cause.png` · `prism-v2.png` · `desk-pipeline.png` · `desk-exception.png` · `onboarding-facts.png` · `books-ledger.png` · `books-exceptions.png` · `accountant-packet.png` · `eligibility-rules.png` · `voice-transcript.png`

---

*Epic owner: build team · This document is the scope of record for MONEY TALKS 2. If the cut line moves, this file changes the same day.*
