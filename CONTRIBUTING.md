# Contributing

Three founders, one repo. These rules exist so that any two of us can work the same day without
stepping on each other.

## Branches

`main` is protected: no direct pushes, one approval, `make test` green.

```
feat/<area>-<slug>     feat/onboarding-gmail-consent
fix/<area>-<slug>      fix/ledger-duplicate-row
docs/<slug>            docs/single-repo-consolidation
chore/<slug>           chore/archive-hackathon-lab
```

Keep a branch alive for days, not weeks. Rebase your own branch; never rebase or force-push `main`.

## Commits

Conventional Commits, scoped by area — this is already the repo's habit (`docs(mt2):`, `feat(composer):`,
`chore(vercel):`):

```
feat(eligibility): cite the as_of date per program
fix(books): stop double-counting refunded rows
docs(design): record the two design systems
```

One idea per commit. If the message needs "and", it is two commits.

## Before you open a PR

- `make test` passes (it fans out to business, company, legal, kb and pipeline).
- UI change: attach a screenshot at 390px and 1440px, light **and** dark. Both design systems have a
  dark mode and the Flask app has no toggle, so a screen that assumes white ships broken.
- Design token change: `docs/DESIGN.md` is updated **in the same PR**.
- Money-touching copy: check `docs/MONEY_PATH.md` — an estimate is never "money", an agency receipt is
  never a payment.
- No secrets, no real business data, no real personal data. Fixtures are synthetic and stay synthetic.

## Review

- One approval is enough; the author merges (squash or rebase, no merge commits on `main`).
- Review SLA: same business day. If a PR sits overnight, ping in the channel rather than waiting.
- Reviewers comment on the diff; if you disagree on direction, take it to a 10-minute call and record
  the outcome in `docs/DECISIONS.md` (create it on the first such decision).
- `CODEOWNERS` names a default reviewer per path — it documents the lane, it does not gate anything
  (three people cannot afford a hard gate).

## What needs two founders

Anything in `docs/MONEY_PATH.md`, `docs/STATUS_MODEL.md`, the evidence model, pricing, or a claim we
make to a customer or agency.

## Working agreements

- **No demo-only shortcuts in product paths.** If it needs a fixture to look right, it is demo-only and
  gets labelled. See the "Known drift" section of `docs/DESIGN.md` for the current list.
- **One runtime.** `make demo` is the app. Do not add a second server to show a feature.
- **Write it down when you decide.** A decision that lives only in chat is lost by the next session —
  put it in `docs/DECISIONS.md` (ADR-lite: decision, why, what we rejected).
