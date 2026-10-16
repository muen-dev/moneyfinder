# System architecture

```text
ElevenLabs (optional multilingual data entry)
        │
        ▼
Business UI (onboarding / search / form / timeline / payment)
        │
        ▼
Agent API / toolbox
        ├── AWS Bedrock (reasoning, tool selection, prompt_version)
        ├── SurrealDB (profiles, facts, claims, form fields, events, evidence, eval traces)
        ├── Search adapter (mock NY → later real NY)
        ├── Form provenance + deadline extraction + validation
        ├── Daytona browser → mock NY portal
        ├── AgencyStatusProvider (mock → later real)
        ├── BankTransactionProvider (mock → later Plaid/SimpleFIN)
        └── Arize (traces + field/status/deadline evals)
```

## Component map

| Layer | Path |
|-------|------|
| UI | `ui/index.html` |
| Mock portal | `mock_portal/index.html` |
| Agent tools | `src/agent/tools.py` |
| Bedrock config | `src/agent/runtime.py` |
| Search | `src/search/` |
| Forms | `src/forms/` |
| Status machine | `src/pipeline/status.py` |
| Providers | `src/providers/` |
| Surreal schema | `schemas/surreal/schema.surql` |
| Evals | `evals/` |

Anchor is **not** on the NY search path. Banking connectors only confirm deposits after `PAYMENT_ISSUED`.
