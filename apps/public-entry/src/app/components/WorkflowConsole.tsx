"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type Job = {
  job_id: string;
  project_id: string;
  title?: string;
  worldview?: string;
  status: string;
  progress?: number;
  message?: string;
  updated_at?: string;
  created_at?: string;
  outputs?: Record<string, string>;
  counts?: Record<string, number>;
};

const artifacts = [
  ["Complete novel", "02_novel/complete_novel.md"],
  ["Storyboard", "03_film/storyboard.md"],
  ["Asset prompts", "04_assets/asset_prompts.md"],
  ["Shot prompts", "05_shots/shot_prompts.md"],
  ["QC report", "06_qc/validation_report.md"],
  ["Manifest", "00_manifest.json"],
] as const;

function authHeaders(token: string): Record<string, string> {
  return token.trim() ? { "x-aigcpp-access-token": token.trim() } : {};
}

function artifactUrl(job: Job, rel: string, token: string) {
  const suffix = token.trim() ? `?token=${encodeURIComponent(token.trim())}` : "";
  return `/api/artifact/${encodeURIComponent(job.job_id)}/${rel}${suffix}`;
}

export default function WorkflowConsole() {
  const [worldview, setWorldview] = useState("A frontier archivist follows a forbidden map into a city under the sea");
  const [title, setTitle] = useState("Tide Archive");
  const [shots, setShots] = useState(12);
  const [token, setToken] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [preview, setPreview] = useState("Select an artifact to preview its contents.");
  const [notice, setNotice] = useState("Ready");

  const selectedJob = useMemo(() => jobs.find((job) => job.job_id === selectedId) || jobs[0], [jobs, selectedId]);
  const completeCount = jobs.filter((job) => job.status === "complete").length;
  const activeCount = jobs.filter((job) => job.status === "queued" || job.status === "running").length;

  async function loadJobs() {
    const response = await fetch("/api/jobs", {
      headers: authHeaders(token),
      cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to load jobs");
    const nextJobs = data.jobs || [];
    setJobs(nextJobs);
    if (!selectedId && nextJobs[0]) setSelectedId(nextJobs[0].job_id);
    const nextActive = nextJobs.filter((job: Job) => job.status === "queued" || job.status === "running").length;
    const nextComplete = nextJobs.filter((job: Job) => job.status === "complete").length;
    setNotice(`${nextJobs.length} jobs, ${nextActive} active, ${nextComplete} complete`);
  }

  async function submitJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("Submitting job");
    const response = await fetch("/api/jobs", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(token),
      },
      body: JSON.stringify({ worldview, title, shots }),
    });
    const data = await response.json();
    if (!response.ok) {
      setPreview(data.error || "Job submission failed");
      setNotice("Submission failed");
      return;
    }
    setSelectedId(data.job.job_id);
    setNotice("Job queued");
    await loadJobs();
  }

  async function loadArtifact(rel: string) {
    if (!selectedJob) return;
    const response = await fetch(artifactUrl(selectedJob, rel, token), { cache: "no-store" });
    setPreview(await response.text());
  }

  useEffect(() => {
    loadJobs().catch((error) => setPreview(error.message));
    const timer = window.setInterval(() => loadJobs().catch(() => undefined), 3000);
    return () => window.clearInterval(timer);
  }, [token]);

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <div className="mark" aria-hidden />
          <div>
            <strong>AIGC Production Pipeline</strong>
            <span>Local-first workflow entry</span>
          </div>
        </div>
        <div className="top-stats">
          <span>{activeCount} active</span>
          <span>{completeCount} complete</span>
          <span>{notice}</span>
        </div>
      </header>

      <section className="workspace">
        <form className="composer panel" onSubmit={submitJob}>
          <div>
            <h1>Production Package</h1>
            <p>Submit a world concept and produce a complete novel, film storyboard, asset prompts, shot prompts, and QC report.</p>
          </div>
          <label>
            Worldview
            <textarea value={worldview} onChange={(event) => setWorldview(event.target.value)} maxLength={240} required />
          </label>
          <label>
            Title
            <input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={80} />
          </label>
          <div className="split">
            <label>
              Shots
              <input type="number" min={4} max={60} value={shots} onChange={(event) => setShots(Number(event.target.value))} />
            </label>
            <label>
              Access token
              <input type="password" value={token} onChange={(event) => setToken(event.target.value)} autoComplete="off" />
            </label>
          </div>
          <div className="actions">
            <button type="submit">Run Workflow</button>
            <button type="button" className="secondary" onClick={() => loadJobs().catch((error) => setPreview(error.message))}>
              Refresh
            </button>
          </div>
        </form>

        <section className="queue panel">
          <div className="panel-title">
            <h2>Job Queue</h2>
            <p>Recent jobs from the connected worker.</p>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Job</th>
                  <th>Progress</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {jobs.length === 0 ? (
                  <tr>
                    <td colSpan={4}>No jobs yet.</td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <tr key={job.job_id} className={job.job_id === selectedJob?.job_id ? "active" : ""} onClick={() => setSelectedId(job.job_id)}>
                      <td>
                        <span className={`chip ${job.status}`}>{job.status}</span>
                      </td>
                      <td>
                        <strong>{job.title || job.project_id}</strong>
                        <small>{job.message || job.worldview}</small>
                      </td>
                      <td>
                        <span>{job.progress || 0}%</span>
                        <div className="bar" style={{ "--progress": `${job.progress || 0}%` } as React.CSSProperties}>
                          <i />
                        </div>
                      </td>
                      <td>{job.updated_at || job.created_at}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="artifacts panel">
          <div className="panel-title">
            <h2>Artifacts</h2>
            <p>{selectedJob?.project_id || "Select a completed job."}</p>
          </div>
          <div className="artifact-list">
            {artifacts.map(([label, rel]) => (
              <button key={rel} type="button" onClick={() => loadArtifact(rel)}>
                <span>{label}</span>
                <svg viewBox="0 0 24 24" aria-hidden>
                  <path d="M8 5l8 7-8 7" />
                </svg>
              </button>
            ))}
          </div>
          <pre>{preview}</pre>
        </aside>
      </section>
    </main>
  );
}
