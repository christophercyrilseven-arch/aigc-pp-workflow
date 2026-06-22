import { NextRequest } from "next/server";

import { proxyJson } from "@/lib/workerProxy";

export async function GET(request: NextRequest) {
  return proxyJson(request, "/api/jobs");
}

export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyJson(request, "/api/jobs", {
    method: "POST",
    body,
  });
}
