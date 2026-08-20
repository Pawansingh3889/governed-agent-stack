import { NextResponse } from "next/server";

const ELENCHUS_URL = process.env.NEXT_PUBLIC_ELENCHUS_URL ?? "http://localhost:8000";
const ELENCHUS_USER_ID =
  process.env.ELENCHUS_USER_ID ?? "00000000-0000-0000-0000-0000000000a1";

export async function GET() {
  try {
    const res = await fetch(`${ELENCHUS_URL}/api/v1/templates/published`, {
      headers: { "X-User-Id": ELENCHUS_USER_ID },
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) throw new Error(`${res.status}`);
    return NextResponse.json(await res.json());
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "unknown";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}