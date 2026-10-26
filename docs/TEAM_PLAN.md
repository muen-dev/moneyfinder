# MONEY TALKS 2 — 3-Person Parallel Build Plan (v2 — merged PRD)

> **Historical — hackathon-era plan, kept as a record.** It is not the current way we work. For who owns
> what now see [`TEAM.md`](TEAM.md); for what we build next see [`ROADMAP.md`](ROADMAP.md); for the
> single-repo decision see [`CONSOLIDATION.md`](CONSOLIDATION.md). The 13:00 gate and the "staleness
> warning" below are closed; Kenan is `@kenwon22` and owns the app UI.

**Scope of record:** [`MONEY_TALKS_2_MASTER.md`](MONEY_TALKS_2_MASTER.md) · **Interface:** [`CONTRACT.md`](CONTRACT.md)
**Event:** Saturday, October 17, 2026 · Track: **Money Operations** · **Freeze: 16:15** (`demo-freeze`)
**Repo:** https://github.com/muen-dev/moneyfinder (`origin`) · `upstream` = thetradingdoc/moneyfinder
**Demo:** 2-min video + 3-min live pitch · Product: evidence-status checklist → Next Year → Markdown review package

> **Merge note:** this plan replaces the Epic-v1 claims/ledger lanes. The product is now the **review assistant** from Kenan's PRD: no filing, no eligibility, no approved/paid tracking, no dollar figures. Read `MONEY_TALKS_2_MASTER.md` §0 for the full conflict record.
>
> **⚠ Staleness warning:** Kenan's PRD v1.0 is **unverified as current** — its fixtures, Harbor Studio dataset and Ninoo path are not in the repo or on disk (audit in `MONEY_TALKS_2_MASTER.md` §0.1). Until the **13:00 confirmation gate**, build only the **shared core**: app shell, case/evidence model, inbox, transactions, review package, Nicrron + PRISM. Do **not** build claims/filing screens or depend on the missing fixtures.
>
> **13:00 gate:** Kenan confirms (a) the PRD is current, (b) where `fixtures.json`/`transactions.csv` or the Ninoo app are, (c) Flask vs Ninoo. If no answer by 13:00, the fallback is the shared core on the Gowanus synthetic dataset with a fictional `DEMO-CREDIT-001`-style checklist.

| Person | Role | Owns | Branch (historical name) |
|---|---|---|---|
| **Thuy** | Product Designer · PRISM owner · repo owner | Dashboard, Inbox, Credit Review, Review Package; design tokens; copy/QA; **PRISM dashboard, alert, proofs**; submission visuals | `feat/thuy-onboarding-prism` |
| **Kenan** | Developer · **Demo owner** | UI shell, Transactions, Next Year, Run History, Settings; API client; **2-min video + live pitch + submission** | `feat/kenan-desk-books` |
| **Richard** | Developer · platform/agent | Case/dataset API, analysis orchestrator + 8 tools, Nicrron client, persistence, CSV import, Markdown export, integration status, PRISM emitter, fixtures, tests | `feat/richard-ledger-agent` |

---

## 0. Setup status

- Fork `muen-dev/moneyfinder`; `origin` = fork, `upstream` = original.
- `main` + three feature branches pushed; docs committed.
- **Richard (`thetradingdoc`) invited with write access — pending acceptance.**
- **Kenan's GitHub username still needed** — invite:
  ```bash
  gh api -X PUT repos/muen-dev/moneyfinder/collaborators/<kenan-username> -f permission=push
  ```
- Clone:
  ```bash
  git clone https://github.com/muen-dev/moneyfinder.git
  cd moneyfinder
  git checkout -b feat/<your-branch> origin/main
  ```

**Branch rules:** `main` is demo; only Thuy merges. Work on your branch; push at every checkpoint; rebase before push (`git fetch origin && git rebase origin/main`); PRs with one reviewer, squash merge. Revert `main` to the last green commit if it breaks. No drive-by edits outside your files.

**Hard rules:** never commit `.env`, keys, real personal data or video; `.env` local, `.env.example` names only; run `git status` before every commit; screenshots to `docs/proofs/`; video stays outside the repo (link it).

---

## 1. File ownership (disjoint write scopes)

| Owner | Files |
|---|---|
| **Thuy** | `ui/dashboard.html`, `ui/inbox.html`, `ui/credit_review.html`, `ui/package.html`, `ui/static/css/design.css`, `docs/proofs/**` |
| **Kenan** | `ui/index.html`, `ui/transactions.html`, `ui/next_year.html`, `ui/run_history.html`, `ui/settings.html`, `ui/static/js/**`, `docs/DEMO_RUNBOOK.md` |
| **Richard** | `src/**`, `fixtures/**`, `scripts/**`, `requirements.txt`, `.env.example`, `research/**` (legacy only) |
| **Shared (read-only others)** | `docs/MONEY_TALKS_2_MASTER.md`, `docs/CONTRACT.md`, `docs/TEAM_PLAN.md` |

`ui/index.html` is Kenan's; `src/server.py` is Richard's. Ask the owner for one-line changes rather than editing.

---

## 2. Contract freeze (12:55)

The full shapes are in [`CONTRACT.md`](CONTRACT.md). Key points:

- One analysis run = one PRISM `session_id`, `agent_id=moneyfinder`, version `v1|v2`.
- 8 tools: `search_mail`, `fetch_messages`, `extract_attachments`, `load_transactions`, `retrieve_checklist`, `compare_evidence`, `generate_recommendations`, `compose_review_package`. ≥7 substantive local executions; ≥6 verified in PRISM.
- Requirement states: `supported|missing|conflicting|needs_review`. **Never `eligible`.**
- A claimed attachment is not evidence: `extract_attachments` must return an extracted record before `supported`.
- Run states: `queued|running|succeeded|failed|partial`; a failed tool cannot complete a finding.
- Fixtures: `fixtures/{cases,inbox,transactions.csv,checklist,findings,next_year,package.md,run}` — Richard commits by **12:55**. UI must render in fixture mode (`?fixture=1`, labeled `demo-only`).
- No endpoint sends email, writes Gmail, files, modifies transactions or submits anything.

**Change protocol:** announce in the team thread, update `CONTRACT.md`, get an ack from both consumers, then code. No silent shape changes after 13:00.

---

## 3. Timeline (three parallel tracks)

| Clock | Thuy | Kenan | Richard | Integration |
|---|---|---|---|---|
| **12:40–12:55** | PRISM check, branches, contract ack | UI shell + client + fixture mode | Contract + fixtures commit; Nicrron client skeleton | Kickoff |
| **12:55–13:00** | — | — | — | **GATE:** Kenan confirms PRD/fixtures/runtime (§0 staleness) |
| **12:55–14:10** | Dashboard + Inbox against fixtures | Transactions + Next Year against fixtures | Case/message/transaction APIs; CSV load; deterministic checks | — |
| **14:10–14:25** | — | — | — | **CP1:** merge, fixture→API swap, mismatch list |
| **14:25–15:35** | Credit Review + Review Package; PRISM alert setup/monitoring | Run History + Settings; demo script draft | Analysis orchestrator + 8 tools; package composer; PRISM emitter + 50 runs | — |
| **15:35–15:50** | — | — | — | **CP2:** end-to-end run, 7+ steps, 6+ verified |
| **15:50–16:15** | Capture proofs (credential, 50 runs, session, alert, root cause, v2) | Record 2-min video | Root-cause v1/v2 replay; README | **16:15 freeze** |
| **16:15–17:00** | Submission copy/visuals | Upload video + submit | Repo public check | — |
| **17:00–18:00** | PRISM pitch segment | Live pitch rehearsal | Buffer/Q&A | Buffer |

**Checkpoints are hard.** Stop coding at 14:10 and 15:35; merge, run the demo path, post one status line each (`done / next / blocked`).

---

## 4. Work assignments

### Thuy — Designer, PRISM owner, repo owner

**T1 · PRISM for the EOD demo (12:50–13:20, monitor after)**
Credential is already verified in `.env` (handshake 200). Your job is the dashboard + proofs:
1. Confirm project `6e1051f7-8dce-498f-9846-d6acaa087737`; Settings → Billing confirm code `MONEYTALKS#2`.
2. Confirm one active API key (don't paste it anywhere).
3. Create the **alert**: failed tool / partial run (the Case-002 attachment failure is the trigger). Save notification.
4. After Richard's seed: verify **50+ runs** before fixes.
5. Capture: credential, 50 runs, **7-step session**, alert firing, root-cause cluster (3+), v2 same inputs pass. Save to `docs/proofs/`.
6. Own the PRISM segment of the live pitch (40s, exact clicks).

**T2 · Dashboard + Inbox + Credit Review + Review Package UI**
- Dashboard: case status, unresolved requirements, pending actions, last run, integration status. No savings/eligibility.
- Inbox: search/filter/category correction/source drawer/attachment state (`claimed` vs `available` vs `missing`).
- Credit Review: checklist version + four states + evidence + questions; **no "Eligible"**.
- Review Package: preview + real Markdown download; evidence index; limitations; run version/timestamp.
- Design tokens `design.css`, copy QA, banned-word grep before freeze.

**T3 · Proofs + submission visuals (15:50–17:00):** proof set, screenshot sheet, video claim review.

### Kenan — Developer, Demo owner

**K1 · UI shell + API client (12:40–13:10):** routes, fetch wrapper with fixture/replay switch, demo reset, global banner, integration status chip.
**K2 · Transactions + Next Year (13:10–14:10):** table with explicit direction, integer cents, receipt link, duplicate/recurring review flag, CSV import errors; Next Year cards with accept/dismiss, owner, owner-selected due date, persisted task.
**K3 · Run History + Settings (14:25–15:35):** run status/version/step states/errors/telemetry delivery; verified PRISM link only if configured; local steps labeled separately; Settings: profile, modes, integration status, reset demo.
**K4 · Demo (15:50–17:00):** record 2-min video (dashboard → inbox → transactions → analyze → credit review → next year → package), build 5-slide pitch, submit, rehearse with fallbacks.
**K5 · Submission:** public repo, video link, tool list (PRISM, Nicrron, ElevenLabs optional), team, track Money Operations.

### Richard — Developer, platform/agent

**R1 · Contract + fixtures + Nicrron (12:40–13:00):** commit `fixtures/*` + contract shapes; `src/agent/nicrron.py` (`complete_json`, retry/timeout, usage, schema validation).
**R2 · Data APIs + deterministic checks (13:00–14:10):** cases/messages/transactions/checklist; CSV import with dedupe; attachment availability independent of message claims; identity conflict; arithmetic in code.
**R3 · Analysis orchestrator + package (14:25–15:35):** 8 tools, run states, step persistence, failure retention; recommendations + tasks; Markdown package + real download; integration status; PRISM emitter + 50-run seed.
**R4 · Root cause v1/v2 (15:35–16:15):** reproduce the claimed-attachment bug across 3+ runs; v2 validator requires an extracted attachment record + excerpt; same inputs pass. Fix only blockers.
**R5 · README + public repo (16:15–17:00):** sponsor tools, architecture, how to run, synthetic disclaimer, incognito check.

---

## 5. Scope cut for 3 builders (~15–18 person-hours)

**Must ship (demo spine):** banner; Dashboard; Inbox; Transactions; Analyze with ≥7 tools; Credit Review (four states); Next Year + accept/task; Markdown package download; Run History (basic); Nicrron; PRISM 50+ runs / ≥6 verified / alert / root cause v2; video.
**Defer:** advanced CSV validation (fixture CSV is enough), Settings polish, XLSX export, Gmail read-only, voice, guardrails.
**Cut order:** voice → XLSX → Gmail → Settings polish → CSV advanced. **Never cut:** missing-attachment integrity, 7+ tool run, 6+ PRISM verification, package download, banner.

**Demo fallback:** every screen renders from fixtures; every proof has a screenshot by 16:15. If the API dies on stage, switch to replay and keep talking.

---

## 6. Definition of done

- [ ] `main` at `demo-freeze` runs the PRD journey from `/api/demo/reset` with no manual repair.
- [ ] Replay mode works with the API stopped, labeled `demo-only`.
- [ ] Case-002 shows missing attachment; Case-003 conflicting; control case supported; no "Eligible".
- [ ] ≥7 tool executions visible locally; ≥6 verified in PRISM; alert + root-cause + v2 screenshots.
- [ ] Markdown package downloads and contains evidence index, limitations, warning, run version.
- [ ] Accepted task survives refresh; dismissal keeps a reason.
- [ ] Banner visible on every screen and export; no dollar benefit/eligibility text.
- [ ] Public repo, video, submission confirmed; `.env` not tracked.

---

## 7. Open items (before 13:00)

1. **Kenan's GitHub username** → invite.
2. **Seed data:** Kenan's `fixtures.json` + `transactions.csv` are **not in the repo or on disk** (checked 12:45). If Kenan confirms/provides them, use Harbor Studio; if not by 13:00, Richard generates a fictional `DEMO-CREDIT-001`-style checklist over the existing Gowanus synthetic dataset. Do not block the UI on missing fixtures.
3. **Runtime:** Flask repo vs Ninoo app — recommendation: Flask only; Ninoo optional prototype. One runtime on stage.
4. **Submission deadline** — confirm in Discord/`#hackathon-support`; move freeze earlier if needed.
5. **PRISM billing code** — confirm `MONEYTALKS#2` redeemed.
6. **Case-003 fixture values** — business-name conflicts (not the old ZIP conflict).
7. **Ninoo prompt** — alternate build or reference? If alternate, decide which artifact is demoed.

---

*Owner: Thuy · Scope: `MONEY_TALKS_2_MASTER.md` · Interface: `CONTRACT.md` · Freeze: 16:15.*
