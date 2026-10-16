# Money path: how we know approval and deposit

## Problem

We do not control New York State. Submission ≠ approval ≠ deposit.

## Two evidence rails

```text
AgencyStatusProvider  →  APPROVED / PAYMENT_ISSUED
BankTransactionProvider → PAYMENT_CONFIRMED
```

| Provider | Proves | Does not prove |
|----------|--------|----------------|
| NY portal / mock agency | Receipt, approval, payment issued | Bank deposit landed |
| Plaid / SimpleFIN / mock bank | Matching inbound txn | Agency approved the claim |
| User confirmation | User says funds arrived | Independent agency proof |

## State machine

```text
MATCH_FOUND
FORM_READY
USER_APPROVED
SUBMITTED
CLAIM_RECEIVED
PROCESSING
APPROVED
PAYMENT_ISSUED
PAYMENT_CONFIRMED
```

Also: `REJECTED`, `NEEDS_DOCS`, `STOPPED_BY_USER`.

## Bank match scoring (when a feed exists)

| Confidence | Criteria |
|------------|----------|
| HIGH | Amount + date window + reference/description match |
| MEDIUM | Amount + date; no reference |
| LOW | Similar amount only → require user review |

Hackathon default: `MockBankTransactionProvider` emits a labeled synthetic deposit. UI must show **Demo / synthetic**.

## Plaid / SimpleFIN

Optional future adapters behind `BankTransactionProvider`. Not required for Day 1.
Anchor is not used for NY search or for proving NY approval.
