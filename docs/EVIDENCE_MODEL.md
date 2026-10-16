# Evidence model

Every status upgrade that implies government or bank action requires an evidence kind.

| Target status | Required `evidence.kind` | Typical source |
|---------------|--------------------------|----------------|
| `SUBMITTED` | `submission` | Daytona / agent submit payload + timestamp |
| `CLAIM_RECEIVED` | `agency_receipt` | Mock/real portal confirmation ID |
| `APPROVED` | `agency_approval` | Agency status page or notice |
| `PAYMENT_ISSUED` | `agency_payment_issued` | Agency payment-issued status/reference |
| `PAYMENT_CONFIRMED` | `bank_deposit` | Synthetic bank match or Plaid/SimpleFIN later |

## Evidence record shape (Surreal)

```text
evidence {
  claim,
  kind,
  source,
  reference?,
  payload?,
  created_at  // UTC datetime
}
```

Linked from immutable `pipeline_event` rows (`from_status`, `to_status`, `actor`, `evidence`, `created_at`).

## Two rails

1. **AgencyStatusProvider** — receipt, processing, approval, payment issued  
2. **BankTransactionProvider** — deposit observed  

Neither rail may write the other rail’s statuses.
