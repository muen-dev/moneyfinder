# Agent architecture (form accuracy)

## Goals

1. Fill claim forms correctly with provenance.
2. Never submit without human approval.
3. Verify browser-entered values match the approved snapshot.

## Loop

```text
Bedrock model
  → choose tool
  → tool executes (deterministic Python where possible)
  → result written to Surreal
  → model continues until blocked by approval gate or done
```

Model: `AWS_BEDROCK_MODEL_ID` (default `anthropic.claude-sonnet-4-6`).

## Tools

| Tool | Allowed to | Forbidden to |
|------|------------|--------------|
| `build_search_profile` | Normalize business inputs | Invent EINs/SSNs |
| `generate_name_variants` | Expand legal/DBA names | Call external APIs |
| `search_unclaimed` | Query search adapter | Mark claim approved |
| `score_matches` | Rank candidates | Auto-select without UI |
| `prepare_claim_form` | Map facts → fields | Clear `requires_confirmation` |
| `validate_form` | Schema + conflict rules | Submit |
| `request_user_approval` | Pause for UI | Bypass |
| `daytona_fill_and_submit` | Fill approved fields only | Fill flagged fields |
| `poll_agency_status` | Read provider | Fabricate APPROVED |
| `match_bank_transaction` | Score bank txns | Mark confirmed if LOW |
| `record_evidence_event` | Append Surreal event | Rewrite history |

## Form accuracy pipeline

1. Extract structured facts from onboarding (+ optional ElevenLabs transcript).
2. Attach `source`, `confidence`, `captured_at`.
3. Map to form schema for claim type.
4. Validate required fields, formats, address consistency.
5. Surface conflicts (`requires_confirmation: true`).
6. User edits → mark `edited_by_user`.
7. Freeze **approved form hash**.
8. Daytona fill → DOM read-back → diff against hash.
9. Mismatch → stop + UI alert.
10. Match + final OK → submit → store confirmation evidence.

## Stopping conditions

- Missing consent
- Unresolved confirmation fields
- Browser read-back mismatch
- Agency returns `NEEDS_DOCS`
- User hits Stop
