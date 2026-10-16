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
| UI | `ui/domain.html` (served by `src.server`) |
| Mock portal | `mock_portal/index.html` |
| Local API | `src/server.py` |
| Persistence | `src/persistence.py` → `data/moneyfinder-events.json` (Surreal-ready shapes) |
| Demo seed | `fixtures/demo-seed.json` (`POST /api/demo/reset`) |
| Agent tools | `src/agent/tools.py` |
| Bedrock config | `src/agent/runtime.py` |
| Search | `src/search/` |
| Forms | `src/forms/` |
| Status machine | `src/pipeline/status.py` |
| Providers | `src/providers/` |
| Surreal schema | `schemas/surreal/schema.surql` (target mapping; claim demo is JSON-backed today) |
| Evals | `evals/` |

Anchor is **not** on the NY search path. Banking connectors only confirm deposits after `PAYMENT_ISSUED`.

Run the domain-first vertical slice with:

```bash
python3 -m src.server
# http://localhost:4173
```

Set `NY_UNCLAIMED_DATA_FILE` to use imported NY data. Without it, the API
labels every result `demo_only`.
