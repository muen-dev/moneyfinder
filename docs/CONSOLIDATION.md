# Consolidation — one repo, three founders

**Status:** decided 2026-10-26. Owner: Thuy. Executes: whoever has the `gh` token.

## The decision

`muen-dev/moneyfinder` is the single repository for the product. `muen-dev/hackathon-lab` is **retired
(read-only archive)** — not deleted, because it holds the only commit history of the product app.

Why this repo and not the other: this one carries the engine (`src/` pipeline and status machine,
`research/` collectors, `contracts/`, `schemas/`, `evals/`) and the design system that new work already
uses. `hackathon-lab` carries the more complete *screens* — those get imported, not the repo.

## What the two repos actually are

| | moneyfinder | hackathon-lab |
|---|---|---|
| Commits | 22, root `33c23ae` (2026-10-16) | 32, root `1db50ac` (2026-10-17) |
| Shared history | **none** — `git merge-base` is empty | **none** |
| Shape | research packages (`uv` per package) + `src/` pipeline + `ui/` prototypes + Makefile | one Flask app (`app/`), fixtures, Vercel deploy |
| Product screens | `/`, `/live`, `/wallet/*`, `/track` in the Flask shell under `research/business` | 33 templates: landing, sign-in, onboarding, Gmail crawl, profile review, verification, benefits, eligibility, form fill, progress, dashboard, application, books, run history, settings |
| Deploy | `make demo` on `:8000` | Vercel (`hackathon-lab.vercel.app`) with Redis state shim |
| Tests | 4 pytest files (`tests/`) | 1 (`tests/test_app.py`) |
| CI | none | none |

**The histories are unrelated, not diverged.** `hackathon-lab` was scaffolded fresh on Oct 17
(`1db50ac scaffold: MoneyFinder Claims Desk`), then copied code back out of moneyfinder — `c4978d1`
*"real PRISM tool spans + official PDF fill ported from moneyfinder"*. So there is no merge to do: it
is a **file import with provenance**, not a history merge. `git merge --allow-unrelated-histories`
would collide on `README.md`, `docs/`, `Makefile` and `.gitignore` in one unreviewable diff.

## Inventory — what survives

**Import into `moneyfinder` (product surface, highest value):**

| From hackathon-lab | Why |
|---|---|
| `app/routes/{pages,flow,api}.py` | the only complete screen flow we have (onboarding → profile → eligibility → forms → dashboard → books) |
| `app/services/{eligibility,evidence,applications,ledger,packet,pdf_fill}.py` | eligibility with citations, evidence rails, accountant packet — not present here |
| `app/services/{prism,tracing,nicrron}.py` + `AGENTS.md` standing rule | real PRISM spans; the standing instrumentation rule must survive the move |
| `app/templates/` (33) | the screens themselves |
| `fixtures/forms/{IT-636,IT-212,IT-643,8846}.pdf` + `fixtures/*.json` | official blank forms and the synthetic business; replace the Harbor Studio names with this repo's demo business |
| `tests/test_app.py` | smoke coverage for those routes |
| `docs/PRD.md` (81 lines) | the product definition, still the best statement of what this is |
| `docs/PROVENANCE.md` (28 lines) | every public number sourced — keep this discipline |

**Do not import:**

| From hackathon-lab | Why |
|---|---|
| `vercel.json`, `Procfile`, `render.yaml`, `api/index.py`, Dockerfile | hackathon deploy shims; a real product needs a durable DB, not a Redis state shim |
| `docs/EPIC.md` (746 lines), `docs/EPIC_UI_FLOW.md` (153), `docs/TEAM_PLAN.md` (63) | hackathon planning; superseded by `docs/ROADMAP.md` and `docs/TEAM.md`. Stay in the archive. |
| `docs/CONTRACT.md`, `docs/ARCHITECTURE.md` | this repo has newer versions of both |
| `DESIGN.md` (Finix-derived) | already parked as `docs/reference/DESIGN-hackathon-lab.md`, reference only |
| `docs/REUSE_FROM_MONEYFINDER.md`, `docs/ASSETS.md` | historical notes |

## Target layout

```
moneyfinder/
├─ app/                  # product surface, imported from hackathon-lab (routes, services, templates)
├─ src/                  # agent runtime, status machine, providers — Richard
├─ research/             # collectors + the Flask shell that /live, /wallet, /track run on — Thuy
├─ ui/                   # design reference + composer prototype — Kenan/Thuy
├─ fixtures/, demo/      # synthetic business, official blank forms
├─ contracts/, schemas/, evals/
├─ docs/                 # TEAM, ROADMAP, DESIGN, MONEY_PATH, DECISIONS, reference/
└─ .github/              # CODEOWNERS, PR template
```

`app/` and `research/business/.../web/` both being Flask is temporary and known. Consolidating the two
into one server is a roadmap item, not a scaffolding one.

## Retirement runbook — hackathon-lab

Run in order. Steps 1–2 are the ones that lose access if skipped.

```bash
# 1. Kenan must exist on moneyfinder BEFORE anything is archived.
gh api -X PUT repos/muen-dev/moneyfinder/collaborators/kenwon22 -f permission=push

# 2. Confirm the three of you can read the target repo.
gh api repos/muen-dev/moneyfinder/collaborators --jq '.[].login'

# 3. Land the import as one commit on moneyfinder with provenance in the message.
#    (branch docs/single-repo-scaffold → PR → main)

# 4. Freeze hackathon-lab at its final commit.
cd /tmp/hl-full && git tag archive/2026-10-26 665109e && git push origin archive/2026-10-26

# 5. Replace its README with the retirement notice (next section), then archive.
gh repo archive muen-dev/hackathon-lab --yes   # add -y / --yes, it confirms interactively otherwise
```

**Before step 5, deal with the Vercel project.** `hackathon-lab.vercel.app` is a live demo URL. Either
point that project at `moneyfinder` (`app/` is its natural successor) or shut it down — an unmaintained
public demo that claims "live" is the worst of the three options.

**After archiving:**

- `muen-dev/hackathon-lab` stays readable by its collaborators. Nothing is deleted; the 32 commits and
  all 33 templates remain inspectable at that URL forever.
- Update anything that links to it: `docs/reference/DESIGN-hackathon-lab.md` states its provenance,
  `docs/CONSOLIDATION.md` (this file) records the archive tag.
- The GitHub "archived" banner is the signal. No redirect exists — say the new home in the notice.

## Retirement notice (paste into hackathon-lab README, then archive)

```markdown
# ⚠️ Archived — this project moved

This repository is **read-only**. MoneyFinder / FindMoney is now developed in
**[muen-dev/moneyfinder](https://github.com/muen-dev/moneyfinder)**.

- The product screens (`app/`) were imported into `moneyfinder` on 2026-10-26; the history stays here.
- Final commit: `665109e`, tagged `archive/2026-10-26`.
- The live demo at `hackathon-lab.vercel.app` is retired; run `make demo` in `moneyfinder` instead.
- Design system: `moneyfinder/docs/DESIGN.md`. This repo's `DESIGN.md` is kept there for reference only.
- Team and ownership: `moneyfinder/docs/TEAM.md`.
```

## Risks this creates

| Risk | Mitigation |
|---|---|
| Kenan loses the only repo he can read | invite him to moneyfinder **first** (step 1) |
| The imported `app/` rots next to `research/`'s Flask shell | roadmap item: one server; until then `app/` is the target and the shell is legacy |
| Two sources of truth for eligibility/evidence (`app/services` vs `src/`) | import first, then delete the loser in a follow-up PR — do not run both |
| Vercel demo keeps answering after the repo is archived | explicitly retire or re-point the project (above) |
| Someone links an old README | notice + tag + this file |
