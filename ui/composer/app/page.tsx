"use client";

import { useEffect, useRef, useState } from "react";
import type { AgentEvent, AgentTurn, Approval } from "@/lib/types";
import { SAMPLE_TURN } from "@/lib/sample";

const QUICK_PROMPTS = [
  "What NY credits might my business qualify for?",
  "I run a 14-person brewery in Brooklyn",
  "Help me claim the R&D credit",
];

const EVENT_TAG: Record<AgentEvent["type"], string> = {
  thought: "thinking",
  tool_call: "tool call",
  tool_result: "result",
  guardrail: "guardrail",
  probe: "probe",
  message: "message",
};

const TAG_CLASS: Partial<Record<AgentEvent["type"], string>> = {
  tool_call: "mf-tag--tool",
  tool_result: "mf-tag--result",
  guardrail: "mf-tag--guard",
};

type Turn = { user: string; data: AgentTurn; sample?: boolean };

export default function ComposerPage() {
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [connected, setConnected] = useState<boolean | null>(null);
  const [approvals, setApprovals] = useState<Record<string, "approved" | "denied" | "sending" | "error">>({});
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setSessionId(crypto.randomUUID());
  }, []);

  function resize() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }

  async function send(prompt?: string) {
    const message = (prompt ?? draft).trim();
    if (!message || busy) return;
    setDraft("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setBusy(true);
    try {
      const response = await fetch("/api/agent/turn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message }),
      });
      const data = (await response.json()) as AgentTurn & { error?: { message?: string } };
      if (!response.ok) throw new Error(data.error?.message ?? `HTTP ${response.status}`);
      setConnected(true);
      setTurns((current) => [...current, { user: message, data }]);
    } catch {
      setConnected(false);
      setTurns((current) => [...current, { user: message, data: SAMPLE_TURN, sample: true }]);
    } finally {
      setBusy(false);
    }
  }

  async function decide(approval: Approval, approved: boolean) {
    setApprovals((current) => ({ ...current, [approval.id]: "sending" }));
    try {
      const response = await fetch("/api/agent/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, approval_id: approval.id, approved }),
      });
      setApprovals((current) => ({
        ...current,
        [approval.id]: response.ok ? (approved ? "approved" : "denied") : "error",
      }));
    } catch {
      setApprovals((current) => ({ ...current, [approval.id]: "error" }));
    }
  }

  return (
    <div>
      <header className="mf-topbar">
        <div className="mf-brand">
          <span className="mf-brandmark" aria-hidden="true">◈</span>
          moneyfinder <span style={{ color: "var(--mut)", fontWeight: 500, fontSize: 13 }}>· agent composer</span>
        </div>
        <div className="mf-topbar__meta">
          <span className={`mf-pill ${connected ? "is-live" : connected === false ? "is-offline" : ""}`}>
            {connected ? "pipeline connected" : connected === false ? "backend offline · sample" : "ready"}
          </span>
          <a className="mf-pill" href="http://localhost:8000" target="_blank" rel="noreferrer">moneyfinder app ↗</a>
        </div>
      </header>

      <main className="mf-wrap">
        <section className="mf-hero">
          <span className="mf-hero__sun" aria-hidden="true">◈</span>
          <h1>Your business is leaving tax credits on the table.</h1>
          <p>
            Tell the agent how the business operates. It reads public data, matches the New York credit
            catalog, and fills the forms — with every step and source shown, and nothing filed without
            your approval.
          </p>
          <div className="mf-hero__chips">
            <span>public data only</span>
            <span>every fact sourced</span>
            <span>approval before filing</span>
          </div>
        </section>

        <section className="mf-composer" aria-label="Agent composer">
          <div className="mf-composer__head">
            <p className="mf-composer__eyebrow">new conversation</p>
            <span className={`mf-pill ${connected ? "is-live" : ""}`}>
              {busy ? "agent working…" : connected === false ? "sample transcript" : "agent on standby"}
            </span>
          </div>

          <div className="mf-quick">
            {QUICK_PROMPTS.map((prompt) => (
              <button key={prompt} type="button" onClick={() => void send(prompt)} disabled={busy}>
                {prompt}
              </button>
            ))}
          </div>

          <div className="mf-input">
            <label htmlFor="mf-input" className="sr-only" style={{ position: "absolute", left: -9999 }}>Message the agent</label>
            <textarea
              id="mf-input"
              ref={textareaRef}
              rows={1}
              value={draft}
              placeholder="Describe the business, or ask what it may qualify for… (Enter to send)"
              onChange={(event) => { setDraft(event.target.value); resize(); }}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); }
              }}
            />
            <button type="button" className="mf-send" onClick={() => void send()} disabled={busy || !draft.trim()} aria-label="Send">
              ↑
            </button>
          </div>
          <p className="mf-hint">
            <span>Enter sends · Shift+Enter adds a line</span>
            <span>connected to the MoneyFinder pipeline</span>
          </p>
        </section>

        {turns.length > 0 ? (
          <section className="mf-stream" aria-live="polite" style={{ marginTop: 18 }}>
            {turns.map((turn, index) => (
              <div key={index} className="mf-stream" style={{ gap: 10 }}>
                <div className="mf-user">{turn.user}</div>
                {turn.sample ? (
                  <div className="mf-banner">
                    Backend not running — this is a labelled sample transcript to preview the composer UI.
                    Start MoneyFinder on :8000 (or set <code>MONEYFINDER_API_URL</code>) and ask again.
                  </div>
                ) : null}
                {turn.data.events.map((event, eventIndex) => (
                  <div className="mf-card" key={eventIndex}>
                    <div className="mf-card__top">
                      <span className="mf-card__title">{event.title}</span>
                      <span className={`mf-tag ${TAG_CLASS[event.type] ?? ""}`}>{EVENT_TAG[event.type]}</span>
                    </div>
                    {event.detail ? <p className="mf-card__detail">{event.detail}</p> : null}
                  </div>
                ))}
                <div className="mf-reply">{turn.data.reply}</div>
                {turn.data.approvals?.map((approval) => {
                  const state = approvals[approval.id];
                  return (
                    <div className="mf-approval" key={approval.id}>
                      <p className="mf-approval__title">{approval.title}</p>
                      <p className="mf-approval__body">{approval.body}</p>
                      <div className="mf-approval__actions">
                        {state === "approved" ? (
                          <span className="mf-pill is-live">approved</span>
                        ) : state === "denied" ? (
                          <span className="mf-pill">declined</span>
                        ) : state === "error" ? (
                          <span className="mf-pill is-offline">backend offline — decision not saved</span>
                        ) : (
                          <>
                            <button type="button" className="mf-btn" disabled={state === "sending"} onClick={() => void decide(approval, true)}>
                              {state === "sending" ? "saving…" : "Approve"}
                            </button>
                            <button type="button" className="mf-btn mf-btn--ghost" disabled={state === "sending"} onClick={() => void decide(approval, false)}>
                              Not now
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
                {turn.data.citations?.length ? (
                  <div className="mf-citations">
                    {turn.data.citations.map((citation) => (
                      <a key={citation.url} href={citation.url} target="_blank" rel="noreferrer">{citation.label} ↗</a>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </section>
        ) : null}

        <footer className="mf-foot">
          <span>Composer prototype · wired to <code>/api/agent/turn</code> on the MoneyFinder backend</span>
          <span>No filings without approval</span>
        </footer>
      </main>
    </div>
  );
}

