# **Research and benefits planning**

**Project Scope and Architecture**

- Building an AI agent to research businesses and match them to applicable grants/tax benefits
- Two core workstreams identified:
    - Research gathering (scraping, data sourcing)
    - Form filling (submitting applications)
- Third workstream: financial tracing (post-submission money flow tracking)

**Data Sources and Research Layer**

- Agent to pull business context from multiple sources:
    - Company website (via link scraping)
    - Apollo (business descriptions)
    - Better Business Bureau
    - Internal/contextual data
- Geographic scope: narrowing to one state (New York) to simplify the build
    - Metro area considered but single-state preferred for legal clarity
- Dummy tax benefit/exemption data as a fallback; official NY government sites as a real corpus

**Financial Tracing**

- Post-filing, agent tracks whether money has arrived
- Approach: use KYC/open banking APIs (e.g., Plaid/Blade) to connect to bank account via API with user approval
    - Demo: simulate NY tax office sending funds to a linked account
- Notification triggered once payment lands
- Submission tracking via fax or email confirmation, depending on the agency

**Division of Work and Next Steps**

- Agent scaffolding: one person to start building the agent structure
- Research/stimulus flow: other person to build out the research pipeline with realistic-looking data
- Form filling: flagged as the trickiest part; to be figured out collaboratively
- Mono repo proposed so both workstreams can develop in parallel
- Clay and web search plugins noted as tools to explore for the research layer

**Action Items**

- **Scaffold the grant-matching agent**
Start with the core agent structure before tackling form filling.
- **Build research pipeline with realistic stimulus data**
Make research outputs and tax credit data look real; use official NY sources as corpus.
- **Set up a mono repo for parallel development**
Enables both workstreams to progress simultaneously.