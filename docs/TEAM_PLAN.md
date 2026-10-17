# MONEY TALKS 2 — 3-Person Parallel Build Plan

**Event:** MONEY TALKS 2 · Saturday, October 17, 2026 · Nomad Works, NYC
**Track:** Money Operations
**Repo:** https://github.com/muen-dev/moneyfinder (fork; `upstream` = thetradingdoc/moneyfinder)
**Demo target:** ~5:00–6:00 PM ET · 2-min video + 3-min live pitch
**Hard freeze:** **16:15** — tag `demo-freeze`, no feature commits after.

| Person | Role | Owns | Branch |
|---|---|---|---|
| **Thuy** | Product Designer · PRISM owner · repo owner | Onboarding UI, design system, copy/QA, **PRISM dashboard + proofs**, submission visuals | `feat/thuy-onboarding-prism` |
| **Kenan** | Developer · **Demo owner** | UI shell, Claims Desk, Books tab, API client, **2-min video + live pitch + submission** | `feat/kenan-desk-books` |
| **Richard** | Developer · platform/agent | Nicrron adapter, purchase extraction, ledger + reconciliation, packet builder, eligibility, PRISM emitter, fixtures/contract | `feat/richard-ledger-agent` |

The epic is the scope of record: [`EPIC_MONEY_TALKS_2.md`](EPIC_MONEY_TALKS_2.md). This plan is the **execution split** for three people and supersedes the epic's four-lane timeline.

---

## 0. The one rule

**Contract first, fixtures second, UI third, integration last.** Nobody waits on another person's code: every UI screen is buildable against `fixtures/api/*.json` from minute 15. If the contract changes, it is announced in the team thread and `CONTRACT.md` is updated before anyone codes against the new shape.

---

## 1. Repo setup (Thuy, 12:40–12:50)

**Setup status (2026-10-17):** fork `muen-dev/moneyfinder` created; `origin` = fork, `upstream` = thetradingdoc; `main` + the three feature branches pushed; docs committed (`3c99f45`, `364b1fb`); **Richard (`thetradingdoc`) invited with write access** (pending acceptance).

```bash
# Thuy: invite Kenan once his GitHub username is known
gh api -X PUT repos/muen-dev/moneyfinder/collaborators/<kenan-username> -f permission=push

# Everyone: clone and branch
git clone https://github.com/muen-dev/moneyfinder.git
cd moneyfinder
git checkout -b feat/<your-branch> origin/main
```

**Branch rules**

- `main` is the demo branch. Only Thuy merges into it.
- Work only on your branch. Push at every checkpoint even if incomplete.
- Rebase before pushing: `git fetch origin && git rebase origin/main`.
- PRs: `gh pr create --base main --head feat/<branch> --title "feat: …" --body "…"` — one reviewer, squash merge.
- If `main` breaks: revert to the last green commit, fix on `fix/<topic>`, do not debug on `main` during the demo window.

**Hard rules**

- **Never commit `.env`, real credentials, real personal data, or video files.** `.env` stays local; `.env.example` carries names only. Run `git status` before every commit.
- Do not edit another person's files (see §2). If a shared file must change, the owner makes the change.
- Commit small and often. Prefixes: `feat(desk):`, `feat(ledger):`, `fix(prism):`, `docs:`, `chore:`.
- Screenshots for proofs go in `docs/proofs/` (small PNGs, committed).
- Video goes to YouTube/unlisted or is shared as a file outside the repo; link it in the README.

---

## 2. File ownership (disjoint write scopes)

| Owner | Files / directories | Notes |
|---|---|---|
| **Thuy** | `ui/onboarding.html`, `ui/static/css/design.css` (tokens + components), `docs/proofs/**`, `README` demo copy section | Design tokens are the shared stylesheet; Kenan imports, never forks it |
| **Kenan** | `ui/index.html`, `ui/desk.html`, `ui/books.html`, `ui/static/js/**`, `docs/DEMO_RUNBOOK.md` | Owns the UI shell and all client-side routing/state |
| **Richard** | `src/**`, `research/legal/**`, `scripts/**`, `fixtures/api/**`, `demo/gowanus-kettle/inbox.jsonl`, `requirements.txt`, `.env.example` | Owns every API route, fixture and backend module |
| **Shared (read-only for others)** | `docs/TEAM_PLAN.md`, `docs/CONTRACT.md`, `docs/EPIC_MONEY_TALKS_2.md` | Changes via PR/announcement, not drive-by edits |

`ui/index.html` is Kenan's. If Thuy needs a mount point, she asks Kenan for a one-line change rather than editing it. Same for `src/server.py` (Richard).

---

## 3. Interface contract (freeze at 12:55)

The full shapes live in [`CONTRACT.md`](CONTRACT.md). Summary:

```
POST /api/run                       -> {run_id}
GET  /api/run/{run_id}              -> {status, steps[]}
GET  /api/onboarding/profile        -> {profile, facts[], conflicts[]}
GET  /api/ledger?year=2025          -> {summary, transactions[]}
GET  /api/ledger/exceptions         -> {duplicates[], missing_receipts[], delta_cents}
POST /api/ledger/packet             -> {packet_id, files[]}
GET  /api/applications              -> {applications[]}
GET  /api/applications/{id}         -> {application, events[], evidence[]}
POST /api/applications/{id}/transition {to_status, actor, note} -> {application}
GET  /api/eligibility               -> {verdicts[]}
GET  /api/voice/summary             -> {text}
POST /api/demo/reset                -> {ok}
```

**Fixtures are the parallelisation contract.** Richard commits `fixtures/api/{profile,ledger,applications,eligibility,packet,run}.json` by **12:55**. Kenan and Thuy build against them immediately. The UI must work in fixture mode if the API is down (`?fixture=1` or a client flag) — this is also the demo fallback.

**PRISM emitter interface** (Richard implements; Thuy consumes only the dashboard):

```python
# src/observability/prism.py
with prism_run("backoffice-run-it643-001", agent_id="moneyfinder-backoffice"):
    prism_step("extract_purchases", tool="extract_purchases", status="ok", latency_ms=940,
               input_summary="inbox batch 3", output_summary="12 transactions")
```

- One `session_id` per back-office run; one step per tool call/model call.
- 12 steps for the demo run: `gmail_scan → extract_facts → extract_purchases → categorize_ledger → reconcile_ledger → program_candidates → agency_fetch → eligibility_extract → match_score → form_prep → human_approve → build_accountant_packet`.
- Env: `PRISMTRACE_API_KEY`, `PRISMTRACE_PROJECT_ID`, `PRISMTRACE_HOST` (already in `.env`).

**Contract-change protocol:** post in the team thread, update `CONTRACT.md`, wait for one ack from each consumer, then code. No silent shape changes after 13:00.

---

## 4. Timeline (three parallel tracks)

| Clock | Thuy | Kenan | Richard | Integration |
|---|---|---|---|---|
| **12:40–12:55** | Repo invites, branches, contract ack, PRISM project check | Read contract + fixtures; scaffold UI shell routes | Commit fixtures + contract; Nicrron adapter skeleton | Kickoff: everyone green on `main` |
| **12:55–14:10** | Onboarding UI: connect → scan → facts → conflicts → consent | Claims Desk board + card detail against fixtures | Inbox expansion → purchase extraction → ledger → reconciliation | — |
| **14:10–14:25** | — | — | — | **Checkpoint 1:** merge branches, run fixture→API swap, list mismatches |
| **14:25–15:35** | Onboarding integration + design QA; PRISM alert + run monitoring | Books tab + ledger table + exceptions + packet download | Packet builder (XLSX/CSV) + eligibility rules (cached page) + PRISM emitter + 50-run seed | — |
| **15:35–15:50** | — | — | — | **Checkpoint 2:** end-to-end run, PRISM 12-step session, fix only blockers |
| **15:50–16:15** | Capture PRISM proofs (credential, 50 runs, session, alert, root cause, v2) | Record 2-min video (five beats) | Root-cause v1→v2 rerun; README sponsor section | **16:15 DEMO FREEZE** (`git tag demo-freeze`) |
| **16:15–17:00** | Submission copy + visuals; review video | Edit video, upload, Builderbase/Discord submission | Repo public, README, link check | — |
| **17:00–18:00** | Pitch support + PRISM segment | Live pitch rehearsal + fallbacks | Buffer / Q&A support | Buffer |

**Checkpoints are hard.** At 14:10 and 15:35, stop coding, merge, run the demo path, and write one status line each in the team thread: `done / next / blocked`.

---

## 5. Work assignments

### Thuy — Product Designer, PRISM owner, repo owner

**T0 · Repo + access (12:40–12:50)** — invite Kenan and Richard; confirm branches; post the clone command.
*Done when:* all three can push a commit to their branch.

**T1 · PRISM project setup for the EOD demo (12:50–13:20, then monitor)**
The credential is already verified in `.env` (handshake 200, test trace stored). Your job is the **dashboard and the proofs**, not the emitter.

1. Sign in at `prism.blockconvey.com`; open the project `6e1051f7-8dce-498f-9846-d6acaa087737`.
2. Settings → Billing: confirm code `MONEYTALKS#2` is redeemed (if not, redeem now).
3. Settings → Project: confirm the project name and copy the project ID into the team thread (no key values).
4. API keys: confirm one active key exists (Richard's `.env` already has it; never paste it in chat).
5. **Alerts:** create one alert that matters to the workflow — `reconciliation delta > 250` (or failed tool call). Set the notification channel (email/Discord). Confirm the rule saves.
6. Wait for Richard's 50-run seed; verify **Runs ≥ 50** before any fix (per the builder pack).
7. After Checkpoint 2: open the demo run → **Steps** tab → confirm 12 steps; capture screenshot.
8. **Root Cause:** open Intelligence; confirm a cluster of **3+ failed runs**; write the one-sentence cause; capture screenshot.
9. **v2:** confirm the same inputs on v2 no longer fail; capture the side-by-side.
10. Save all screenshots to `docs/proofs/` with the names in §7. Own the **PRISM segment of the live pitch** (20–40s, exact clicks).

**T2 · Onboarding UI (12:55–14:10, integrate 14:25–15:10)**
Screens: `Connect Gmail` → scan progress (messages scanned, facts found, purchases found) → **profile review** (fact, source email, quote, confidence; "why do you know this?") → **3 conflicts** (coral, cannot be silently resolved) → consent → `Build my back office`.
*Done when:* 20+ facts render with sources; the 3 conflicts require an explicit choice; consent gates the CTA; empty/loading/error states exist; the screen matches the design tokens.

**T3 · Design system + QA + copy (14:25–15:35)**
Own `ui/static/css/design.css` (tokens, type, spacing, status colors, coral exceptions, focus states). Review Kenan's Desk/Books screens: money semantics ("agency says paid" vs "deposit matched"; "booked" vs "reconciled"), the "Needs you" queue, packet labels ("Prepared for professional review. Not filed. Not tax advice.").
*Done when:* all screens share one visual language; every money label is unambiguous; mobile at 390px has no overflow.

**T4 · Proofs + submission visuals (15:50–17:00)**
Capture the proof set; produce the submission screenshot sheet; review the 2-min video for correct claims (no "we filed" or "you'll get $X" language).

### Kenan — Developer, Demo owner

**K1 · UI shell + API client (12:40–13:10)**
Routing for `/onboarding`, `/desk`, `/books`; fetch wrapper that switches between live API and `fixtures/api/*.json` (`?fixture=1`); demo reset button; global status bar.
*Done when:* all three routes render fixture data with one command.

**K2 · Claims Desk (13:10–14:10)**
Four columns (Found / In process / Approved / Paid), totals, cards with amount + next action + deadline, detail drawer with evidence/events, "Needs you" exception queue, one allowed status transition, and the deposit reconciliation moment (`PAYMENT_ISSUED` ≠ `PAYMENT_CONFIRMED`).
*Done when:* all four columns populate from fixtures; illegal transitions are blocked; the paid column never shows green before a matched deposit.

**K3 · Books tab + packet (14:25–15:35)**
Summary block (revenue, expenses, capital, reconciled delta, missing receipts), ledger table (40+ rows, category/treatment/source/confidence/flags), exceptions filter, click-to-source-email, **Download accountant packet** + preview.
*Done when:* the table renders 40+ rows; filters work; the packet download returns XLSX and CSV; totals match the summary.

**K4 · Demo video + pitch (15:50–17:00)**
Record the 2:00 video: hook → onboarding → books → eligibility → desk → PRISM → close. Then build the 3:00 live pitch deck (5 slides max): problem, demo path, proofs, architecture, close. Rehearse twice.
*Done when:* video is under 2:00 and uploaded; pitch is rehearsed with fallback screenshots; submission form is filled.

**K5 · Submission (16:15–17:00)**
Public repo link, video link, tool list (PRISM, Nicrron, ElevenLabs), team names, 2–3 sentence description, track = Money Operations. Confirm in Discord/Builderbase.

### Richard — Developer, platform/agent

**R1 · Contract + fixtures + Nicrron (12:40–13:00)**
Commit `CONTRACT.md` shapes and `fixtures/api/*.json`; `src/agent/nicrron.py` (`complete_json`, retry, timeout, usage); swap the Bedrock call sites behind a flag (`MODEL_PROVIDER=nicrron` default).
*Done when:* one live `nicrron/auto` JSON call returns and is logged; fixtures parse.

**R2 · Inbox → purchases → ledger (13:00–14:10)**
Expand `demo/gowanus-kettle/inbox.jsonl` to ~55 messages (30 receipts/invoices, synthetic); `extract_purchases` with mandatory quote; normalize vendor/date/amount; categorize; flag capital; dedupe (2); missing receipts (6); `reconciled_delta`.
*Done when:* ≥40 transactions with source ids; 2 duplicates merged; 6 missing receipts; the canning line is `capitalized`; totals tie to IT-212 ($186,500) and 8846 ($148,600).

**R3 · Packet + eligibility + PRISM (14:25–15:35)**
Packet builder (XLSX via openpyxl, CSV, cover, open questions); eligibility rules from a **cached official page** (live fetch optional); WOTC expiry handling; quote validator; `src/observability/prism.py` emitter; `scripts/prism_seed_runs.py` for 50+ runs; support Thuy's alert; v1/v2 root-cause replay.
*Done when:* packet downloads and totals match; one verdict per program with citation; PRISM shows 50+ runs and a 12-step session.

**R4 · Integration fixes (15:35–16:15)**
Only blocker fixes: API shape mismatches, quote-validator failures, packet totals, PRISM step names. No refactors after 15:35.
*Done when:* the demo path runs end-to-end from a clean reset.

**R5 · README + public repo (16:15–17:00)**
Sponsor tools section (PRISM, Nicrron, ElevenLabs), architecture image, how to run, synthetic-data disclaimer, public repo check in incognito.

---

## 6. Three-person scope cut (important)

The epic's full P0 was estimated for four builders. With three, the capacity is ~15 person-hours, so the **demo spine** is the contract:

**Must ship (P0):**
1. Onboarding with sourced facts + 3 conflicts + consent.
2. Books: 40+ transaction ledger, exceptions, packet download (XLSX/CSV).
3. Claims Desk: four columns, detail, exception queue, one transition, deposit mismatch.
4. PRISM: credential, 50+ runs, 12-step session, alert firing, root-cause cluster + v2.
5. 2-min video + submission.

**Deferred (only if green before 15:35):**
- live agency web fetch (use a cached official snapshot with `as_of`),
- ElevenLabs voice,
- cash forecast,
- packet PDFs (XLSX/CSV is enough),
- optional enforce-mode guardrail,
- mobile polish.

**Cut order if behind:** voice → live fetch → forecast → packet PDFs → design polish. **Never cut:** onboarding, ledger + packet, desk statuses, PRISM 12-step session + alert + root-cause/v2, video.

**Demo fallback:** every screen must render from fixtures; every proof has a screenshot saved by 16:15. If the API dies on stage, switch to fixture mode and keep talking.

---

## 7. Proofs and submission checklist

**PRISM proofs (Thuy):**
- [ ] `docs/proofs/prism-credential.png` — setup doctor `credential_ok: true`
- [ ] `docs/proofs/prism-50-runs.png` — runs ≥50, before fixes
- [ ] `docs/proofs/prism-session-steps.png` — 12 named steps, one expanded
- [ ] `docs/proofs/prism-alert.png` — rule + firing event
- [ ] `docs/proofs/prism-root-cause.png` — cluster 3+ + cause sentence
- [ ] `docs/proofs/prism-v2.png` — same inputs, v2 passing
- [ ] Cause sentence on the pitch slide: *"The extractor treated a plausible rule as a fact because the schema did not require a verbatim quote from the agency page."*

**Submission (Kenan):**
- [ ] Public repo link works in incognito
- [ ] 2-min video uploaded and linked
- [ ] Tool list: PRISM (required), Nicrron (required), ElevenLabs (optional)
- [ ] Team names + roles
- [ ] Track: Money Operations
- [ ] Submission confirmed in Builderbase/Discord

**Demo path (memorize):**
`/onboarding` (connect → facts → conflicts → consent) → `/books` (ledger → exceptions → packet) → `/desk` (four columns → detail → transition → deposit mismatch) → PRISM (session → alert → root cause → v2) → close.

---

## 8. Communication and escalation

- **Team thread:** one Discord channel/thread named `#mt2-moneyfinder`. One status line per person at each checkpoint: `done / next / blocked`.
- **Standups:** 12:55 kickoff, 14:10 checkpoint 1, 15:35 checkpoint 2, 16:15 freeze, 17:00 submission. 5 minutes max.
- **Blockers:** if blocked >10 minutes, post it and @ the owner. Do not silently wait.
- **Contract changes:** announce before coding; update `CONTRACT.md`; ack from both consumers.
- **No hero edits:** do not fix another person's file at 15:50. Send the exact snippet and the owner applies it.
- **Secrets:** `.env` local only; if a key is needed, DM — never in the repo, chat, or screenshot.

---

## 9. Definition of done

- [ ] `main` at `demo-freeze` runs the full demo path from `POST /api/demo/reset` with no manual repair.
- [ ] Fixture fallback works with the API stopped.
- [ ] 12-step PRISM session + alert + root-cause cluster + v2 are visible and screenshotted.
- [ ] Packet downloads and its totals match the Books tab and the credit forms.
- [ ] Video < 2:00; submission confirmed.
- [ ] `git status` clean; `.env` not tracked; README lists sponsor tools and synthetic-data disclaimer.

---

## 10. Open items (fill before 13:00)

1. **Kenan's GitHub username** — Thuy invites him as a collaborator (Richard = `thetradingdoc`).
2. **Exact submission deadline** — confirm in `#hackathon-support`; if earlier than 17:00, move freeze to 15:45.
3. **Video tool/recording permission** — Kenan confirms; fallback is QuickTime screen recording + captions.
4. **Who records the PRISM segment** — Thuy presents it live; Kenan records it in the video.
5. **ElevenLabs** — P1 only; no owner until the demo spine is green (Richard picks it up only if idle).

---

*Owner: Thuy (repo, plan) · Scope of record: `EPIC_MONEY_TALKS_2.md` · Interface: `CONTRACT.md` · Freeze: 16:15 `demo-freeze`.*
