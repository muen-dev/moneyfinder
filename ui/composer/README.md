# MoneyFinder agent composer

A conversational front end for the MoneyFinder pipeline, ported from the CommonWell
agent composer. It lives beside the Python app on purpose: one deployable UI, two
server-side proxy routes, no second agent loop.

```
ui/composer/
  app/page.tsx              composer, agent activity stream, approvals, citations
  app/api/agent/turn/       proxy → MoneyFinder POST /api/agent/turn
  app/api/agent/approve/    proxy → MoneyFinder POST /api/agent/approve
  lib/types.ts              the event/approval/citation contract
  lib/sample.ts             labelled offline transcript shown only when the backend is down
```

## Run

```bash
cd ui/composer
npm install
MONEYFINDER_API_URL=http://127.0.0.1:8000 npm run dev   # http://localhost:3100
```

The MoneyFinder app runs separately on :8000 (`make demo` in the repo root).

## Backend contract

```http
POST /api/agent/turn
{ "session_id": "…", "message": "…", "company_domain": "optional" }
→ { "reply": "…",
    "events":   [{ "type": "thought|tool_call|tool_result|guardrail|probe|message",
                   "title": "…", "detail": "…", "tool": "…", "sponsor": "…" }],
    "approvals":[{ "id": "…", "title": "…", "body": "…" }],
    "citations":[{ "label": "…", "url": "…" }] }

POST /api/agent/approve
{ "session_id": "…", "approval_id": "…", "approved": true }
→ { "ok": true }
```

Until the two routes exist, the composer shows the labelled sample transcript; it
never claims the agent ran when the backend is unreachable.
