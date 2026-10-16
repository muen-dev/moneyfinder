# MoneyFinder Team Implementation Plan

**Audience:** all four developers  
**Primary demo:** B2B New York unclaimed funds for NYC businesses  
**Secondary (deferred):** D2C consumer claims, EITC, SNAP

This document is the source of truth for scope, money proof, agent architecture, Surreal memory, UI, and demo honesty.

---

## 1. Product contract

MoneyFinder helps a **business** recover forgotten New York State unclaimed property (uncashed checks, refunds, credits, deposits).

We do **not**:

- Move money ourselves
- Infer government approval from time passing
- Treat form submission as payment confirmation
- Put Anchor in the NY search path
- Require Plaid/SimpleFIN for the hackathon demo

We **do**:

1. Collect a business search profile
2. Search NY unclaimed funds (synthetic adapter for demo; real search adapter later)
3. Score matches with provenance
4. Prepare claim forms with field-level sources
5. Require authorized-user approval
6. Submit via Daytona into a mock portal
7. Track agency evidence separately from bank evidence
8. Confirm deposit only when a bank transaction (mock or real) matches

### Honest language

| Status | What we may say |
|--------|-----------------|
| `MATCH_FOUND` | “Possible money matched” |
| `FORM_READY` | “Claim form prepared for review” |
| `USER_APPROVED` | “You authorized submission” |
| `SUBMITTED` | “Form sent” |
| `CLAIM_RECEIVED` | “Agency/mock portal acknowledged receipt” |
| `PROCESSING` | “Awaiting agency decision; no approval evidence yet” |
| `APPROVED` | “Agency approved the claim” (requires evidence) |
| `PAYMENT_ISSUED` | “Agency says payment was sent” (requires evidence) |
| `PAYMENT_CONFIRMED` | “Deposit observed / confirmed” (requires bank evidence) |

---

## 2. Why B2B first (not D2C)

| | B2B (chosen) | D2C (deferred) |
|--|--------------|----------------|
| Search key | Legal name + DBA + address | Personal name + prior addresses |
| Sensitivity | Lower (no SSN for search) | Higher (SSN often needed to claim) |
| Name stability | Higher | Lower (nicknames, moves) |
| Proof of authority | Clear org docs | Identity docs |
| Hackathon executability | Strong | Harder to demo safely |

NY Office of Unclaimed Funds supports searching by **last or business name**, with city/ZIP refinement. Business claimants must prove authorization (notarized officer statement, corporate seal, cancelled business check, DBA cert, etc.).

Anchor is an embedded-finance / bank-account API. It is **not** a NY unclaimed-property search source. Keep it out of core search.

---

## 3. Architecture overview

```text
Business UI (onboarding / search / form / timeline / payment)
        │
        ▼
Agent API (orchestration + approval gates)
        │
        ├── AWS Bedrock (reasoning + tool selection)
        ├── SurrealDB (profiles, facts, claims, events, evidence, dates)
        ├── Search adapter (mock NY / later real NY)
        ├── Form validator + provenance
        ├── Daytona browser → Mock NY portal
        ├── AgencyStatusProvider (mock / later real)
        ├── BankTransactionProvider (mock / later Plaid|SimpleFIN)
        └── Arize (traces + field-level evals)
```

Optional: ElevenLabs for multilingual **data entry** only (not memory, not submission).

### Workstream ownership (4 people)

| Seat | Owns | Branches |
|------|------|----------|
| A | AWS Bedrock agent loop + tools | `feature/agent-*` |
| B | SurrealDB schema, memory, events | `feature/memory-*` |
| C | Money pipeline, status machine, providers | `feature/pipeline-*` |
| D | UI, Daytona mock portal, Arize demo | `ui/*`, `feature/daytona-*`, `feature/arize-*` |

Data-input teammates may supply richer search corpora; this team owns agentic memory, form accuracy, and money-status proof.

---

## 4. Business input contract (what to search)

Before any search, collect:

```json
{
  "entity_type": "business",
  "legal_name": "Example NYC Foods LLC",
  "dbas": ["Example Foods", "Example NYC Market"],
  "addresses": [
    {
      "street": "123 Main Street",
      "city": "Brooklyn",
      "state": "NY",
      "zip": "11201",
      "current": true
    }
  ],
  "business_type": "LLC",
  "authorized_representative": {
    "name": "Maria Alvarez",
    "role": "Managing Member"
  },
  "search_consent": true,
  "document_uploads": []
}
```

**Do not** use EIN as a public search key (NY downloadable lists do not expose TIN/amount). EIN belongs only in claim-verification steps if required, and should not live in long-term agent memory unless encrypted + scoped.

Search variants generated from the profile:

1. Exact legal name
2. Legal name without LLC/Inc/Corp suffix
3. Each DBA
4. Normalized punctuation / case
5. City + ZIP refinements
6. Prior addresses

See [`contracts/b2b_input.schema.json`](../contracts/b2b_input.schema.json) and [`src/search/variants.py`](../src/search/variants.py).

---

## 5. Money path and proof (the gap we close)

Government systems are one-sided: we cannot force approval. Architecture must **separate**:

1. **Agency evidence** → approval / payment issued  
2. **Bank evidence** → money arrived  

```text
PROFILE → SEARCH → MATCH_FOUND → FORM_READY → USER_APPROVED
  → SUBMITTED → CLAIM_RECEIVED → PROCESSING
  → APPROVED → PAYMENT_ISSUED → PAYMENT_CONFIRMED
```

Invalid inferences (forbidden):

- “Submitted 14 days ago ⇒ approved”
- “Amount predicted ⇒ incoming”
- “Fast-forward button ⇒ real money”

### Evidence requirements

| Transition | Required evidence |
|------------|-------------------|
| `MATCH_FOUND` | Search result ID, name/address match reason, confidence, source |
| `SUBMITTED` | Timestamp + outbound submission payload hash |
| `CLAIM_RECEIVED` | Confirmation / claim ID from portal |
| `APPROVED` | Explicit agency status or notice |
| `PAYMENT_ISSUED` | Agency payment-issued status + date/reference if available |
| `PAYMENT_CONFIRMED` | Matching bank txn (amount, date window, description/ref) **or** user-confirmed receipt |

Providers:

- `AgencyStatusProvider` — mock for demo; real portal/API later  
- `BankTransactionProvider` — synthetic ledger for demo; Plaid/SimpleFIN adapters later  

See [`src/providers/`](../src/providers/).

---

## 6. Agent architecture for correct form fill

The agent must not free-form invent and submit fields.

Pipeline:

```text
Voice/text → extract facts → attach source+confidence
  → map to form schema → validate → surface conflicts
  → user review/edit → immutable approved form snapshot
  → Daytona fills only approved fields
  → read-back verify → stop on mismatch
  → final OK → submit → save confirmation evidence
```

Each field:

```json
{
  "field": "legal_name",
  "value": "Example NYC Foods LLC",
  "source": "user_input",
  "confidence": 0.99,
  "requires_confirmation": false,
  "edited_by_user": false
}
```

Conflict example (ZIP from user vs state record):

```json
{
  "field": "zip",
  "value": "10456",
  "source": "user_input",
  "conflicting_value": "10457",
  "source_of_conflict": "state_record",
  "requires_confirmation": true
}
```

Tools (boundary list): `build_search_profile`, `generate_name_variants`, `search_unclaimed`, `score_matches`, `prepare_claim_form`, `validate_form`, `request_user_approval`, `daytona_fill_and_submit`, `poll_agency_status`, `match_bank_transaction`, `record_evidence_event`.

Hard rules:

- No submit without `USER_APPROVED`
- No status upgrade without evidence record in Surreal
- No browser fill of unapproved / flagged fields

---

## 7. SurrealDB memory model

Namespace: `moneyfinder` · Database: `main`

Tables: `business`, `fact`, `claim`, `form_field`, `pipeline_event`, `evidence`, `eval_trace`

Every `pipeline_event` stores UTC `datetime` (`created_at`). Claims store `submitted_at`, `approved_at`, `payment_issued_at`, `payment_confirmed_at`, `last_checked_at`, `expected_by`.

Schema: [`schemas/surreal/schema.surql`](../schemas/surreal/schema.surql)

---

## 8. UI requirements

| Screen | Purpose |
|--------|---------|
| Onboarding | Legal name, DBAs, addresses, rep, consent, docs |
| Search progress | Variants + sources checked |
| Matches | Property type, confidence, evidence, next action |
| Form review | Field / source / confidence / conflicts / approve |
| Timeline | Status, timestamps, confirmation IDs, next check, uncertainty |
| Payment | Label `PAYMENT_ISSUED` vs `PAYMENT_CONFIRMED`; synthetic bank events marked **demo** |

Prototype: [`ui/index.html`](../ui/index.html) (B2B rewrite of the earlier generic MoneyFinder HTML).

---

## 9. Daytona + Arize

- Mock portal under [`mock_portal/`](../mock_portal/) with mismatch, confirmation, status, payment-issued scenarios.
- Daytona sandbox runs browser fill against mock portal only in the demo.
- Arize evals: field accuracy, source attribution, match scoring, deadline extraction, approval compliance, status transition legality. Fixtures in [`evals/`](../evals/).

---

## 10. Minimum demo slice

1. Onboard synthetic business `Example NYC Foods LLC`
2. Search shows 1–3 matches with confidence
3. Prepare forms; force one ZIP conflict
4. User fixes conflict and approves
5. Daytona / simulated browser submits to mock portal
6. Show `CLAIM_RECEIVED` + confirmation ID
7. Advance mock agency → `APPROVED` → `PAYMENT_ISSUED`
8. Synthetic bank txn → `PAYMENT_CONFIRMED`
9. Show Arize field-accuracy sample (“X of Y fields correct”)

---

## 11. Risks and assumptions

- Real NY portal may block automation (CAPTCHA/MFA/ToS) → mock portal for hackathon
- No real-time “money cleared” webhook from the state → evidence polling + bank match
- Fee / finder-law issues if charging % of recovery → pitch free claim help / demo only
- Surreal Cloud needs a **database JWT** (control-plane token ≠ DB token)
- Arize `ARIZE_SPACE_ID` must be filled from the Arize dashboard
- Temporary AWS session credentials expire; rotate before team share

---

## 12. Hackathon deliverables

From Daytona HackSprint + Arize NYC:

- Public GitHub repo
- Devpost: summary, problem/impact, architecture, sponsor tools used
- Demo video &lt; 2 minutes
- 3-minute pitch + 2-minute Q&A if finalist
- Sponsor tools: Daytona, Arize, AWS, SurrealDB (and optionally ElevenLabs)

---

## 13. Review checklist

- [ ] AWS + Surreal choices confirmed
- [ ] Branch protection / PR policy accepted
- [ ] Data model + state machine reviewed
- [ ] No secrets on `main`
- [ ] Demo claims language approved (no false “money arrived”)
