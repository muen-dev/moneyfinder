# Minimum synthetic demo slice

Walk this **Track** path at `http://localhost:8000/track/` (`make demo`) or `http://localhost:4173` (`make api` / `python3 -m src.server`). UI is `ui/domain.html`; APIs are `/api/*`.

1. **Landing** shows the MoneyFinder counter as **possible funds identified** (not recovered cash) and the journey thermometer.
2. **Load seeded demo** from Start → “Load seeded demo business”, or begin with **example.com** research / manual onboarding for `Example NYC Foods LLC`.
3. **Verify profile** facts with source, confidence, and timestamps; confirm representative + consent.
4. **Search** shows mock NY corpus hits with confidence and estimate labels.
5. **Select matches** and prepare forms.
6. **Conflict**: prepared forms force a ZIP mismatch (`state_record` vs profile); Send stays disabled until conflicts are cleared and authorization is checked.
7. **Approve & submit** sandbox log → `CLAIM_RECEIVED` with confirmation `NY-DEMO-…`.
8. **Tracker dashboard** shows claim cards, progress bars, activity feed, next actions, and rejection / needs-docs states.
9. **Claim detail**: simulate agency → `PROCESSING` → `APPROVED` → `PAYMENT_ISSUED` (agency evidence only).
10. **Simulate demo bank deposit** → `PAYMENT_CONFIRMED` labeled synthetic.
11. **Agent memory** panel shows the JSON-backed decision trail (Surreal-ready schema, not a live Surreal connection).

Pitch language: free state claims; we do paperwork with proof; synthetic identities only.

## Persistence note

Runtime state lives in `data/moneyfinder-events.json` (gitignored). Deterministic seed is `fixtures/demo-seed.json` via `POST /api/demo/reset`. Records are shaped for a future SurrealDB mapping (`schemas/surreal/schema.surql`).
