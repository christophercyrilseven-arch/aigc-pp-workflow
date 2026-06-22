import { NextRequest, NextResponse } from "next/server";

export function workerBaseUrl() {
  const value = process.env.AIGCPP_WORKER_URL?.trim();
  if (!value) return "";
  return value.replace(/\/+$/, "");
}

function workerHeaders(init?: RequestInit) {
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
  };
  const workerToken = process.env.AIGCPP_WORKER_TOKEN?.trim();
  if (workerToken) headers["x-aigcpp-worker-token"] = workerToken;
  return headers;
}

export function assertAccess(request: NextRequest) {
  const expected = process.env.AIGCPP_ACCESS_TOKEN?.trim();
  if (!expected) return null;

  const token = request.headers.get("x-aigcpp-access-token") || request.nextUrl.searchParams.get("token") || "";
  if (token === expected) return null;

  return NextResponse.json({ error: "access token required" }, { status: 401 });
}

export async function proxyJson(request: NextRequest, path: string, init?: RequestInit) {
  const denied = assertAccess(request);
  if (denied) return denied;

  const base = workerBaseUrl();
  if (!base) return NextResponse.json({ error: "worker url is not configured" }, { status: 500 });

  const response = await fetch(`${base}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...workerHeaders(init),
    },
  });

  const text = await response.text();
  try {
    return NextResponse.json(JSON.parse(text), { status: response.status });
  } catch {
    return NextResponse.json({ error: text || "worker returned non-json response" }, { status: response.status });
  }
}

export async function proxyArtifact(request: NextRequest, path: string) {
  const denied = assertAccess(request);
  if (denied) return denied;

  const base = workerBaseUrl();
  if (!base) return NextResponse.json({ error: "worker url is not configured" }, { status: 500 });

  const response = await fetch(`${base}${path}`, { cache: "no-store", headers: workerHeaders() });
  const body = await response.arrayBuffer();
  const headers = new Headers();
  headers.set("Content-Type", response.headers.get("content-type") || "text/plain; charset=utf-8");
  headers.set("Content-Length", String(body.byteLength));
  return new NextResponse(body, { status: response.status, headers });
}
