# Team ownership (4 developers)

| Seat | Focus | Suggested branches | Owns in repo |
|------|-------|--------------------|--------------|
| A | AWS Bedrock agent + tools | `feature/agent-*` | `src/agent/` |
| B | SurrealDB memory + dates | `feature/memory-*` | `schemas/surreal/` |
| C | Money pipeline + providers | `feature/pipeline-*` | `src/pipeline/`, `src/providers/`, `src/search/` |
| D | UI, Daytona portal, Arize | `ui/*`, `feature/daytona-*`, `feature/arize-*` | `ui/`, `mock_portal/`, `evals/` |

Other teammates may supply richer data corpora; Seat C integrates adapters without changing status evidence rules.

## Handoffs

1. Seat B merges schema before Seat A writes durable events.
2. Seat C freezes status machine before Seat D wires timeline UI copy.
3. Seat D does not invent status labels outside `docs/MONEY_PATH.md`.
4. All seats open PRs into `main` — no direct pushes.
