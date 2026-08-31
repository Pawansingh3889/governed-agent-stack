import { NextResponse } from "next/server";

const ELENCHUS_URL = process.env.NEXT_PUBLIC_ELENCHUS_URL ?? "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${ELENCHUS_URL}/api/v1/health`, {
      signal: AbortSignal.timeout(5000),
    });
    const data = await res.json();
    return NextResponse.json({ status: res.ok ? "ok" : "down", ...data });
  } catch {
    return NextResponse.json({ status: "down" }, { status: 503 });
  }
}