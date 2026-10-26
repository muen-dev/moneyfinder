import type { AgentTurn } from "./types";

/**
 * Clearly-labelled offline preview. Used only when the MoneyFinder backend is not
 * running, so the composer can be reviewed without pretending the agent ran.
 */
export const SAMPLE_TURN: AgentTurn = {
  connected: false,
  reply:
    "I'd start by learning how the business operates from public data, then match it against the New York credit catalog. Connect the backend to run this for real.",
  events: [
    { type: "thought", title: "Reading the company profile", detail: "Domain, NAICS code, hiring signals" },
    { type: "tool_call", title: "company_research", detail: "website · BBB · NY Dept. of State · news", tool: "research" },
    { type: "tool_result", title: "Profile drafted", detail: "14 employees · Brooklyn · brewery", sponsor: "moneyfinder" },
    { type: "tool_call", title: "match_credits", detail: "catalog/niches.toml", tool: "matching" },
    { type: "tool_result", title: "3 credit niches matched", detail: "IT-636 · IT-212 · IT-643" },
    { type: "guardrail", title: "Human approval required", detail: "Nothing is filed until you approve" },
  ],
  approvals: [
    { id: "sample-1", title: "Run the credit match?", body: "Reads public data only; no Gmail access yet." },
  ],
  citations: [{ label: "NY IT-636 form", url: "https://www.tax.ny.gov/pdf/current_forms/it/it636_fill_in.pdf" }],
};
