```mermaid
flowchart LR
    A["Gmail read-only"] --> B["Claude email agent"]
    A --> C["Web research agents"]
    B --> D["SurrealDB dossier"]
    C --> D
    D --> E["NY credit matcher"]
    E --> F["Anchor fills IT-636"]
    F --> G["User approves PDF"]
    B & C -.-> H["Arize traces, evals"]

    classDef dark fill:#0a0a0a,stroke:#333,color:#ededed;
    class A,B,C,D,E,F,G,H dark;
```

1. Business email + Gmail (read-only) -> in parallel: Claude email agent on Bedrock (EIN, barrels, license) and web research agents (Firecrawl, NY DOS, NYC Open Data, news, LinkedIn).
2. Both feed a SurrealDB Cloud dossier (facts with provenance) -> credit matcher ranks niche NY credits (forms from tax.ny.gov, irs.gov).
3. Anchor Browser fills NY Form IT-636 live, reads every field back, never submits -> user reviews and approves. Arize traces and evals throughout.
