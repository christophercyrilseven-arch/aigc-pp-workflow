import { NextRequest } from "next/server";

import { proxyArtifact } from "@/lib/workerProxy";

type Params = Promise<{ jobId: string; path: string[] }>;

export async function GET(request: NextRequest, context: { params: Params }) {
  const { jobId, path } = await context.params;
  const rel = path.map((part) => encodeURIComponent(part)).join("/");
  return proxyArtifact(request, `/artifact/${encodeURIComponent(jobId)}/${rel}`);
}
