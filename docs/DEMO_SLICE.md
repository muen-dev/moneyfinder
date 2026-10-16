# Minimum synthetic demo slice

Walk this path in `ui/index.html` (and optionally Daytona against `mock_portal/`):

1. **Onboard** synthetic business `Example NYC Foods LLC` with DBAs and Brooklyn address + consent.
2. **Search** shows name variants and mock NY corpus hits with confidence.
3. **Select matches** and prepare forms.
4. **Conflict**: first form forces a ZIP mismatch (`state_record` vs profile); user must edit.
5. **Approve** authorization checkbox; Send stays disabled until conflicts cleared.
6. **Submit** sandbox log → `CLAIM_RECEIVED` with confirmation `NY-DEMO-…`.
7. **Simulate agency** → `APPROVED` then `PAYMENT_ISSUED` (agency evidence only).
8. **Simulate demo bank deposit** → `PAYMENT_CONFIRMED` labeled synthetic.
9. **Trace** screen shows Arize-shaped accuracy bars (replace with live Arize numbers).

Pitch language: free state claims; we do paperwork with proof; synthetic identities only.
