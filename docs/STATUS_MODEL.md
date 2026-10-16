# Claim status model

Canonical statuses (do not invent alternate meanings in UI copy):

```text
MATCH_FOUND
FORM_READY
USER_APPROVED
SUBMITTED
CLAIM_RECEIVED
PROCESSING
NEEDS_DOCS
APPROVED
PAYMENT_ISSUED
PAYMENT_CONFIRMED
REJECTED
STOPPED_BY_USER
```

## Valid transitions

| From | To |
|------|----|
| `MATCH_FOUND` | `FORM_READY`, `STOPPED_BY_USER` |
| `FORM_READY` | `USER_APPROVED`, `MATCH_FOUND`, `STOPPED_BY_USER` |
| `USER_APPROVED` | `SUBMITTED`, `FORM_READY`, `STOPPED_BY_USER` |
| `SUBMITTED` | `CLAIM_RECEIVED`, `STOPPED_BY_USER` |
| `CLAIM_RECEIVED` | `PROCESSING`, `NEEDS_DOCS`, `REJECTED` |
| `PROCESSING` | `APPROVED`, `NEEDS_DOCS`, `REJECTED`, `PROCESSING` |
| `NEEDS_DOCS` | `PROCESSING`, `FORM_READY`, `STOPPED_BY_USER` |
| `APPROVED` | `PAYMENT_ISSUED`, `PROCESSING` |
| `PAYMENT_ISSUED` | `PAYMENT_CONFIRMED` |
| `PAYMENT_CONFIRMED` | — |
| `REJECTED` | — |
| `STOPPED_BY_USER` | — |

Enforced in code: [`src/pipeline/status.py`](../src/pipeline/status.py).

## Forbidden inferences

- Elapsed time alone must never move a claim to `APPROVED` or `PAYMENT_*`
- Form submission alone must never become `PAYMENT_CONFIRMED`
- Predicted/estimated amounts are not incoming funds
