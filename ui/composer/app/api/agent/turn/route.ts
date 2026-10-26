import { NextResponse } from "next/server";

export const runtime = "nodejs";

const BASE = (process.env.MONEYFINDER_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

/**
 * POST /api/agent/turn — forwards one composer message to the MoneyFinder
 * pipeline and returns its reply + activity events.
 *
 * The composer never talks to the Python app directly, so any future auth token
 * stays server-side.
 */
export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: { code: "invalid_json", message: "Body must be JSON" } }, { status: 400 });
  }

  try {
    const response = await fetch(`${BASE}/api/agent/turn`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(process.env.MONEYFINDER_TOKEN ? { Authorization: `Bearer ${process.env.MONEYFINDER_TOKEN}` } : {}),
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(60_000),
    });
    const text = await response.text();
    if (!response.ok) {
      return NextResponse.json(
        { connected: false, error: { code: "backend_error", status: response.status, message: text.slice(0, 400) } },
        { status: 502 },
      );
    }
    return NextResponse.json({ connected: true, ...JSON.parse(text) });
  } catch (error) {
    return NextResponse.json(
      { connected: false, error: { code: "backend_unreachable", message: (error as Error).message } },
      { status: 503 },
    );
  }
}
