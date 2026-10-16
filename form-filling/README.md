# form-filling: agentic browser form filler (Anchor Browser)

`fill.py` loads a business dossier (SurrealDB Cloud `business:<slug>.dossier`, falling back to
`research/company/data/<domain>/dossier.json`), maps it to the mock claim portal (`mock_portal/index.html`),
and types the approved values in an Anchor Browser cloud session whose live view opens locally so you can watch.
It reads the DOM back and diffs it against the approved values, saves a screenshot and a JSON receipt to
`form-filling/out/`, and **never clicks submit**: the form waits for the user's final OK in the product UI.

    make fill                                   # SLUG=gowanuskettle-example HOLD=10
    uv run --project kb --with playwright python form-filling/fill.py --slug gowanuskettle-example [--hold 10] [--no-open]

Fields with no dossier value (`property_name`, `amount_requested` for the demo business) are left blank and listed
as `needs_user`; nothing is guessed. Needs `ANCHOR_API_KEY` in the repo-root `.env`. Safety rules: `docs/FORM_FILLER_HANDOFF.md`.
