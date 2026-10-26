# MoneyFinder × CommonWell and the agent composer

**Decision:** CommonWell is the demo / source of truth only — not a product. MoneyFinder is the business. The one thing worth carrying over from CommonWell is the **agent composer** (chat UI + agent activity stream), not the whole app.

## What MoneyFinder is today

- Python backend: `src/server.py` (web app on :8000), `src/agent/{runtime,orchestrator,tools}.py`, pipeline + providers + SurrealDB persistence.
- Frontend: static HTML — `ui/index.html`, `ui/domain.html` — no build step.
- Flows: Google sign-in / company profile → dossier → matched NY credits → form-filling → ready-to-file.

## What the CommonWell composer gives us

| Piece | Where | Use in MoneyFinder |
| --- | --- | --- |
| Composer UI (empty state, quick prompts, Enter-to-send, auto-grow) | `app/page.tsx`, `cw-composer` styles | Ask the business for context, then run the credit pipeline conversationally |
| Agent activity stream (thought / tool call / tool result / guardrail / approval cards) | `app/page.tsx`, `cw-act` styles | Show the Gmail agent, web research, matching and form-fill steps as they run |
| Approval gates + evidence | approval cards, `recordEvidence` | Keep the human in the loop before filing or connecting accounts |
| Trace widget (PRISM) | `components/TraceWidget.tsx` | Live receipts for every step; MoneyFinder already records traces (`src/observability/arize.py`) |
| Guardrails (PII redaction, injection scan) | `lib/guardrails.ts` | Port to Python so prompts/research stay clean server-side |

## Integration options

1. **Next.js composer microfrontend (recommended).** New `ui/composer/` Next app cloned from CommonWell's composer page. It talks to two routes on the MoneyFinder backend:
   - `POST /api/agent/turn` → `{ session_id, message }` → `{ reply, events[], approvals[], citations[] }`
   - `POST /api/agent/approve` → `{ session_id, approval_id, approved }`
   Ships separately from the FastAPI app (same origin via reverse proxy), keeps secrets server-side, reuses components as-is. Cost: a second Node deploy.
2. **React island inside the existing UI.** Vite build mounted at `#composer` in `ui/index.html`; same API contract. Smaller deploy, but mixes build systems.
3. **Vanilla JS rewrite** in `ui/index.html`. No new stack, but throws away the component work and is slowest to iterate.

## Backend contract the engineers need to expose

```
POST /api/agent/turn
  { session_id, message, company_domain? }
  -> { reply, events: [{ type, title, detail, tool?, sponsor?, at }],
       approvals: [{ id, title, body }], citations: [{ label, url }] }

POST /api/agent/approve
  { session_id, approval_id, approved }
  -> { ok, next_event? }
```

Events map 1:1 to CommonWell's `thought | tool_call | tool_result | guardrail | message | probe`, so the activity stream renders without changes.

## Milestones

1. **Contract** (engineer, 0.5d): add the two FastAPI routes wrapping `src/agent/orchestrator.py`; return the event shape above.
2. **Composer scaffold** (Thuy, 1–2d): `ui/composer/` Next app; port composer + activity stream + approval cards + trace widget; point at the two routes via a server-side proxy.
3. **Company context** (1d): pass the selected company/domain into turns so the agent can run profile → credits → forms for that business.
4. **Guardrails + tracing** (1d): port redaction/injection scan to Python; emit PRISM/arize spans per event; show them in the widget.
5. **Approvals + filing** (1–2d): connect the existing form-filling step behind a composer approval.
6. **Deploy + eval** (1d): deploy composer beside FastAPI, run the existing `evals/` for agent turns, record a demo video.

## Risks

- Two runtimes (Node + Python) in one deploy — mitigate with a thin Next proxy and one reverse proxy in front.
- Session/auth: MoneyFinder uses Google sign-in on :8000; composer must share that session (cookie or signed token).
- Streaming: start with request/response + event list (as today); add SSE once the contract is stable.
- Don't fork the agent loop — MoneyFinder already has `runtime.py`; the composer is a view over it, not a second agent.
