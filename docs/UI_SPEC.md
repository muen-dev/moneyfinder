# UI specification (B2B)

## Screens

### 1. Landing

Value prop: find unclaimed funds owed to NYC businesses. Disclaimer: synthetic demo; not legal advice.

### 2. Business onboarding

Fields:

- Legal business name (required)
- DBAs (multi)
- Current address: street, city, borough/ZIP, state NY
- Former addresses (optional multi)
- Business type
- Authorized representative name + role
- Consent checkbox for search
- Optional document upload placeholders (authorization letter, DBA, cancelled check)

CTA: **Search for unclaimed funds**

### 3. Search progress

List each variant + source:

- State unclaimed funds database
- Show tick animation per source

### 4. Matches

Cards:

- Title / property type
- Location
- Tag: Found vs Estimate
- Confidence %
- Evidence bullets
- Amount (if synthetic demo exposes it; note NY public list may omit amounts)
- Checkbox to include in claim pack

### 5. Form review

Per form:

- Agency name
- Field list with source chip + confidence
- Conflict highlight (coral)
- View & edit / Remove
- Master authorization checkbox
- Send disabled until all conflicts cleared + checkbox

### 6. Submit log

Monospace log of Daytona/browser steps. Stop button.

### 7. Timeline / account

- Status chips
- Timestamps (UTC stored, local displayed)
- Confirmation IDs
- Next check time
- Evidence links
- Uncertainty copy when `PROCESSING`

### 8. Payment

- `PAYMENT_ISSUED`: agency evidence
- `PAYMENT_CONFIRMED`: synthetic bank row labeled **Demo deposit**
- Never label synthetic as real wire

### 9. Trace / Arize

Bars for fields correct, deadlines, match quality. Placeholder for live Arize numbers.

## Accessibility

- Focus outlines
- Reduced-motion respect
- Language chips optional (ElevenLabs later)
