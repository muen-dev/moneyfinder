/** The contract the MoneyFinder backend exposes for the composer. */

export type AgentEventType =
  | "thought"
  | "tool_call"
  | "tool_result"
  | "guardrail"
  | "probe"
  | "message";

export type AgentEvent = {
  type: AgentEventType;
  title: string;
  detail?: string;
  tool?: string;
  sponsor?: string;
  at?: string;
};

export type Approval = {
  id: string;
  title: string;
  body: string;
};

export type Citation = {
  label: string;
  url: string;
};

export type AgentTurn = {
  reply: string;
  events: AgentEvent[];
  approvals?: Approval[];
  citations?: Citation[];
  /** false when the FastAPI backend is not reachable (composer shows the banner). */
  connected?: boolean;
};
