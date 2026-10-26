import { NextResponse } from "next/server";

export const runtime = "nodejs";

const BASE = (process.env.MONEYFINDER_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

/** POST /api/agent/approve — records the human decision on an agent proposal. */
export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: { code: "invalid_json", message: "Body must be JSON" } }, { status: 400 });
  }

  try {
    const response = await fetch(`${BASE}/api/agent/approve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(process.env.MONEYFINDER_TOKEN ? { Authorization: `Bearer ${process.env.MONEYFINDER_TOKEN}` } : {}),
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(30_000),
    });
    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch (error) {
    return NextResponse.json(
      { connected: false, error: { code: "backend_unreachable", message: (error as Error).message } },
      { status: 503 },
    );
  }
}
