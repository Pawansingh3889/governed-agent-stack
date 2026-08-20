import { NextResponse } from "next/server";

const FLOORMIND_API_URL =
  process.env.FLOORMIND_API_URL ?? "http://localhost:8001";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const url = new URL(request.url);
  const target = `${FLOORMIND_API_URL}/api/${path.join("/")}${url.search}`;
  const headers = new Headers(request.headers);
  headers.delete("host");

  try {
    const res = await fetch(target, { headers, signal: AbortSignal.timeout(60000) });
    return new Response(res.body, { status: res.status, headers: res.headers });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "unknown";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const url = new URL(request.url);
  const target = `${FLOORMIND_API_URL}/api/${path.join("/")}${url.search}`;
  const headers = new Headers(request.headers);
  headers.delete("host");

  try {
    const res = await fetch(target, {
      method: "POST",
      headers,
      body: await request.text(),
      signal: AbortSignal.timeout(60000),
    });
    return new Response(res.body, { status: res.status, headers: res.headers });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "unknown";
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}