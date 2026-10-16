# Scope

## In scope (hackathon primary)

- B2B New York unclaimed funds for NYC businesses
- Business onboarding profile → name/DBA/address search
- Form preparation with provenance and conflicts
- Human approval before submit
- Daytona + mock portal submission
- Agency vs bank evidence separation
- SurrealDB memory + UTC event timestamps
- Arize-shaped field and status evaluations
- B2B UI screens listed in `UI_SPEC.md`

## Explicitly out of scope (v1)

- D2C consumer SSN-heavy claim flow as primary demo
- Live EITC / SNAP filing
- Using Anchor as the NY search source
- Requiring Plaid/SimpleFIN for the demo
- Claiming real money movement without evidence
- Direct pushes to `main`

## Secondary (later)

- D2C consumer pipeline with privacy controls
- Eligibility screens for credits/benefits (labeled estimates)
- Real NY search adapter / location-service file import
- Real bank providers behind `BankTransactionProvider`
