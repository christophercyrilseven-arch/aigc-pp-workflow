import { NextRequest } from "next/server";

import { proxyJson } from "@/lib/workerProxy";

type Params = Promise<{ jobId: string }>;

export async function GET(request: NextRequest, context: { params: Params }) {
  const { jobId } = await context.params;
  return proxyJson(request, `/api/jobs/${encodeURIComponent(jobId)}`);
}
