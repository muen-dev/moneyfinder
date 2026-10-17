# UI specification (B2B)

## Screens

### 1. Business-first landing

Ask whether the business has a public website. Route to domain research or manual identity entry.

Show a qualified **possible funds** counter and journey thermometer on the landing page. Never label estimates as recovered or paid money.

Value prop: research the business first, then search for possible unclaimed funds. Disclaimer: synthetic demo; not legal advice.

**Track** experience: `ui/domain.html` (via `/track/` on the Flask shell or `src.server`). Distinct from **Send** (green Gmail/Wallet). Tracker dashboard, claim detail, rejection/needs-docs states, money-flow rails, and agent-memory trail are required screens.

### 2. Business research progress

Show website, NYS DOS, NYC Open Data, BBB/public snippets, and news collectors with loading, success, error, retry, and consent states.

### 3. Business profile review

Show each discovered fact with source URL, timestamp, confidence, and conflicts. Require representative confirmation before search.

### 4. Business onboarding fallback

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

### 5. Search progress

List each variant + source:

- State unclaimed funds database
- Show tick animation per source

### 6. Matches

Cards:

- Title / property type
- Location
- Tag: Found vs Estimate
- Confidence %
- Evidence bullets
- Amount (if synthetic demo exposes it; note NY public list may omit amounts)
- Checkbox to include in claim pack

### 7. Form review

Per form:

- Agency name
- Field list with source chip + confidence
- Conflict highlight (coral)
- View & edit / Remove
- Master authorization checkbox
- Send disabled until all conflicts cleared + checkbox

### 8. Submit log

Monospace log of Daytona/browser steps. Stop button.

### 9. Timeline / account

- Status chips
- Timestamps (UTC stored, local displayed)
- Confirmation IDs
- Next check time
- Evidence links
- Uncertainty copy when `PROCESSING`

### 10. Payment

- `PAYMENT_ISSUED`: agency evidence
- `PAYMENT_CONFIRMED`: synthetic bank row labeled **Demo deposit**
- Never label synthetic as real wire

### 11. Trace / Arize

Bars for fields correct, deadlines, match quality. Placeholder for live Arize numbers.

## Accessibility

- Focus outlines
- Reduced-motion respect
- Language chips optional (ElevenLabs later)
