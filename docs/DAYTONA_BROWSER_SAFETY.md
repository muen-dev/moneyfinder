# Daytona browser safety rules

1. Navigate only to the **mock portal** in demo mode (`mock_portal/index.html` or hosted equivalent).
2. Fill **only** fields present on the approved form snapshot.
3. Skip any field with `requires_confirmation: true`.
4. After fill, read DOM values back and diff against approved values.
5. On any mismatch: stop, screenshot, write Surreal evidence `browser_mismatch`, return to UI.
6. Submit only after final user OK in the product UI (or explicit final pause log).
7. Persist confirmation ID + page HTML/screenshot metadata as `agency_receipt` evidence.
8. Never store secrets from `.env` inside the sandbox page.
9. Host allowlist: mock portal origin only for claim submission.
