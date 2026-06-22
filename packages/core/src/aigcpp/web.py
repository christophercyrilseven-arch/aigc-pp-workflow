"""Local multi-user web worker."""

from __future__ import annotations

import html
import json
import mimetypes
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .config import WorkflowConfig
from .workflow import run_pipeline, slugify


def now_local() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def read_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


class JobStore:
    def __init__(self, config: WorkflowConfig, workers: int) -> None:
        self.config = config
        self.state_path = config.output_root / "web_jobs.json"
        self.lock = threading.RLock()
        self.jobs: dict[str, dict] = {}
        self.executor = ThreadPoolExecutor(max_workers=workers)
        self.load()

    def load(self) -> None:
        rows = read_json(self.state_path, [])
        if isinstance(rows, list):
            with self.lock:
                for row in rows:
                    if isinstance(row, dict) and row.get("job_id"):
                        if row.get("status") in {"queued", "running"}:
                            row["status"] = "stale"
                            row["message"] = "worker restarted before this job completed"
                        self.jobs[str(row["job_id"])] = row

    def persist(self) -> None:
        with self.lock:
            rows = sorted(self.jobs.values(), key=lambda item: str(item.get("created_at", "")), reverse=True)[:200]
        atomic_write_json(self.state_path, rows)

    def list_jobs(self) -> list[dict]:
        with self.lock:
            return sorted((dict(job) for job in self.jobs.values()), key=lambda item: str(item.get("created_at", "")), reverse=True)[:80]

    def get(self, job_id: str) -> dict | None:
        with self.lock:
            job = self.jobs.get(job_id)
            return dict(job) if job else None

    def update(self, job_id: str, **fields: object) -> None:
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].update(fields)
        self.persist()

    def create(self, *, worldview: str, title: str, shots: int, requested_by: str) -> dict:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        short = uuid.uuid4().hex[:7]
        base = slugify(title or worldview, "project")[:44]
        job_id = f"{stamp}-{short}"
        project_id = f"{stamp}-{base}-{short}"
        job = {
            "job_id": job_id,
            "project_id": project_id,
            "worldview": worldview,
            "title": title,
            "shots": shots,
            "requested_by": requested_by,
            "status": "queued",
            "progress": 8,
            "message": "waiting for worker",
            "created_at": now_local(),
            "updated_at": now_local(),
            "outputs": {},
            "counts": {},
        }
        with self.lock:
            self.jobs[job_id] = job
        self.persist()
        self.executor.submit(self._run_job, job_id)
        return dict(job)

    def _run_job(self, job_id: str) -> None:
        job = self.get(job_id)
        if not job:
            return
        self.update(job_id, status="running", progress=24, message="building production package", updated_at=now_local())
        try:
            manifest = run_pipeline(
                worldview=str(job["worldview"]),
                title=str(job.get("title") or ""),
                project_id=str(job["project_id"]),
                shots=int(job.get("shots") or 12),
                config=self.config,
            )
            status = "complete" if manifest.get("ok") else "warning"
            self.update(
                job_id,
                status=status,
                progress=100,
                message="delivery ready" if status == "complete" else "delivery generated with validation warnings",
                updated_at=now_local(),
                project_dir=manifest.get("project_dir"),
                outputs=manifest.get("outputs") or {},
                counts=manifest.get("counts") or {},
                manifest=manifest,
            )
        except Exception as exc:  # noqa: BLE001
            self.update(
                job_id,
                status="failed",
                progress=100,
                message=str(exc),
                updated_at=now_local(),
                error=traceback.format_exc(limit=12),
            )


def response_json(handler: BaseHTTPRequestHandler, payload: object, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def response_text(handler: BaseHTTPRequestHandler, payload: str, content_type: str = "text/html; charset=utf-8", status: int = 200) -> None:
    body = payload.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_body_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length") or "0")
    raw = handler.rfile.read(length).decode("utf-8") if length else "{}"
    data = json.loads(raw or "{}")
    if not isinstance(data, dict):
        raise ValueError("request body must be a JSON object")
    return data


def safe_artifact_path(job: dict, rel: str) -> Path | None:
    project_dir = Path(str(job.get("project_dir") or ""))
    if not project_dir.exists():
        return None
    target = (project_dir / rel).resolve()
    root = project_dir.resolve()
    if target != root and root not in target.parents:
        return None
    if not target.is_file():
        return None
    return target


def render_page() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AIGC Production Pipeline</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0a0d0f;
      --panel: #11171a;
      --panel-2: #151d21;
      --line: rgba(185, 238, 198, 0.16);
      --text: #edf7ef;
      --muted: #8a9890;
      --green: #93d94e;
      --cyan: #5bd8e8;
      --amber: #d9a64e;
      --red: #e46558;
      --shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    html, body { overflow-x: hidden; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(145deg, rgba(91,216,232,0.09), transparent 32%),
        linear-gradient(315deg, rgba(147,217,78,0.12), transparent 30%),
        var(--bg);
      color: var(--text);
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 22px 28px;
      border-bottom: 1px solid var(--line);
      background: rgba(10, 13, 15, 0.78);
      backdrop-filter: blur(16px);
    }
    .brand { display: flex; gap: 12px; align-items: center; font-weight: 800; letter-spacing: 0; }
    .mark {
      width: 34px; height: 34px; border-radius: 8px;
      background: linear-gradient(135deg, var(--green), var(--cyan));
      box-shadow: 0 0 26px rgba(147,217,78,0.22);
    }
    .statusline { color: var(--muted); font-size: 13px; }
    main {
      display: grid;
      grid-template-columns: minmax(300px, 370px) minmax(460px, 1fr) minmax(280px, 360px);
      gap: 18px;
      padding: 22px;
      width: 100%;
      max-width: 1500px;
      margin: 0 auto;
    }
    section {
      background: linear-gradient(180deg, rgba(21,29,33,0.96), rgba(13,18,20,0.96));
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      min-width: 0;
      max-width: 100%;
      overflow: hidden;
    }
    .panel-head { padding: 18px 18px 0; }
    h1, h2, h3 { margin: 0; letter-spacing: 0; }
    h1 { font-size: clamp(24px, 3vw, 42px); line-height: 1.05; }
    h2 { font-size: 15px; text-transform: uppercase; color: #c9f5d0; }
    .sub { margin-top: 10px; color: var(--muted); font-size: 14px; line-height: 1.55; }
    form { padding: 18px; display: grid; gap: 14px; }
    label { display: grid; gap: 7px; color: #c6d2ca; font-size: 13px; font-weight: 650; }
    input, textarea, select {
      width: 100%;
      background: #0b1012;
      color: var(--text);
      border: 1px solid rgba(185, 238, 198, 0.18);
      border-radius: 8px;
      padding: 11px 12px;
      font: inherit;
      outline: none;
    }
    textarea { min-height: 140px; resize: vertical; line-height: 1.45; white-space: pre-wrap; word-break: break-word; }
    p, textarea { overflow-wrap: anywhere; }
    input:focus, textarea:focus, select:focus { border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(91,216,232,0.12); }
    button {
      border: 0;
      border-radius: 8px;
      background: var(--green);
      color: #071007;
      font-weight: 850;
      padding: 12px 14px;
      cursor: pointer;
    }
    button.secondary { background: #202a2e; color: var(--text); border: 1px solid var(--line); }
    .queue { padding: 18px; overflow: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 640px; }
    th, td { text-align: left; padding: 13px 10px; border-bottom: 1px solid rgba(185,238,198,0.11); font-size: 13px; vertical-align: top; }
    th { color: #a7b7ad; font-size: 12px; text-transform: uppercase; }
    tr { cursor: pointer; }
    tr.active { background: rgba(91,216,232,0.08); }
    .chip { display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 9px; font-size: 12px; font-weight: 800; }
    .complete { background: rgba(147,217,78,0.15); color: #bdf486; }
    .running, .queued { background: rgba(91,216,232,0.15); color: #96edf7; }
    .warning, .stale { background: rgba(217,166,78,0.15); color: #f2c87d; }
    .failed { background: rgba(228,101,88,0.16); color: #ff9d92; }
    .bar { height: 7px; background: #20282b; border-radius: 99px; overflow: hidden; margin-top: 8px; }
    .bar span { display: block; height: 100%; width: var(--progress); background: linear-gradient(90deg, var(--cyan), var(--green)); }
    .artifact { padding: 18px; display: grid; gap: 12px; }
    .artifact a, .preview-tab {
      display: flex; justify-content: space-between; align-items: center;
      padding: 12px; border-radius: 8px; border: 1px solid var(--line);
      color: var(--text); text-decoration: none; background: rgba(255,255,255,0.025);
      font-size: 13px;
    }
    pre {
      margin: 0 18px 18px;
      max-height: 420px;
      overflow: auto;
      white-space: pre-wrap;
      color: #d8e7dc;
      background: #080c0e;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      line-height: 1.5;
      font-size: 13px;
    }
    @media (max-width: 1080px) {
      main { grid-template-columns: minmax(0, 1fr); padding: 14px; max-width: 100vw; }
      section { width: 100%; max-width: calc(100vw - 28px); }
      .panel-head, form { max-width: 330px; }
      header { padding: 18px; align-items: flex-start; gap: 8px; flex-direction: column; }
      table { min-width: 560px; }
    }
  </style>
</head>
<body>
  <header>
    <div class="brand"><span class="mark"></span><span>AIGC Production Pipeline</span></div>
    <div class="statusline" id="statusline">worker ready</div>
  </header>
  <main>
    <section>
      <div class="panel-head">
        <h1>Production Package</h1>
        <p class="sub">Submit a world concept and produce a novel, storyboard, assets, shot prompts, and QC report.</p>
      </div>
      <form id="jobForm">
        <label>Worldview
          <textarea id="worldview" maxlength="240" required>A frontier archivist follows a forbidden map into a city under the sea</textarea>
        </label>
        <label>Title
          <input id="title" maxlength="80" value="Tide Archive" />
        </label>
        <label>Shot count
          <input id="shots" type="number" min="4" max="60" value="12" />
        </label>
        <label>Access token
          <input id="token" type="password" autocomplete="off" />
        </label>
        <button type="submit">Run Workflow</button>
        <button type="button" class="secondary" id="refresh">Refresh Queue</button>
      </form>
    </section>
    <section>
      <div class="panel-head">
        <h2>Job Queue</h2>
        <p class="sub">Recent workflow jobs from this worker.</p>
      </div>
      <div class="queue">
        <table>
          <thead><tr><th>Status</th><th>Title</th><th>Progress</th><th>Updated</th></tr></thead>
          <tbody id="jobs"></tbody>
        </table>
      </div>
    </section>
    <section>
      <div class="panel-head">
        <h2>Artifacts</h2>
        <p class="sub" id="artifactHint">Select a completed job to inspect outputs.</p>
      </div>
      <div class="artifact" id="artifactList"></div>
      <pre id="preview">No artifact selected.</pre>
    </section>
  </main>
  <script>
    const artifactMap = [
      ["Complete novel", "02_novel/complete_novel.md"],
      ["Storyboard", "03_film/storyboard.md"],
      ["Asset prompts", "04_assets/asset_prompts.md"],
      ["Shot prompts", "05_shots/shot_prompts.md"],
      ["QC report", "06_qc/validation_report.md"],
      ["Manifest", "00_manifest.json"]
    ];
    let jobs = [];
    let selected = "";
    const el = (id) => document.getElementById(id);
    function headers() {
      const token = el("token").value.trim();
      return token ? {"x-aigcpp-worker-token": token} : {};
    }
    function artifactUrl(job, rel) {
      const token = el("token").value.trim();
      const suffix = token ? `?token=${encodeURIComponent(token)}` : "";
      return `/artifact/${encodeURIComponent(job.job_id)}/${rel}${suffix}`;
    }
    async function loadJobs() {
      const res = await fetch("/api/jobs", {headers: headers()});
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "failed to load jobs");
      jobs = data.jobs || [];
      if (!selected && jobs[0]) selected = jobs[0].job_id;
      renderJobs();
      renderArtifacts();
      el("statusline").textContent = `${jobs.length} jobs`;
    }
    function renderJobs() {
      const body = el("jobs");
      body.innerHTML = jobs.map((job) => `
        <tr class="${job.job_id === selected ? "active" : ""}" data-job="${job.job_id}">
          <td><span class="chip ${job.status}">${job.status}</span></td>
          <td><strong>${escapeHtml(job.title || job.project_id)}</strong><br><small>${escapeHtml(job.message || "")}</small></td>
          <td><span>${job.progress || 0}%</span><div class="bar" style="--progress:${job.progress || 0}%"><span></span></div></td>
          <td>${escapeHtml(job.updated_at || job.created_at || "")}</td>
        </tr>`).join("") || `<tr><td colspan="4">No jobs yet.</td></tr>`;
      body.querySelectorAll("tr[data-job]").forEach((row) => row.addEventListener("click", () => {
        selected = row.dataset.job;
        renderJobs();
        renderArtifacts();
      }));
    }
    function renderArtifacts() {
      const job = jobs.find((item) => item.job_id === selected);
      const list = el("artifactList");
      if (!job || !job.outputs || Object.keys(job.outputs).length === 0) {
        list.innerHTML = "";
        el("preview").textContent = job ? job.message || "Job is still running." : "No artifact selected.";
        return;
      }
      el("artifactHint").textContent = job.project_id;
      list.innerHTML = artifactMap.map(([label, rel]) => `<a href="${artifactUrl(job, rel)}" target="_blank" rel="noreferrer" data-rel="${rel}"><span>${label}</span><span>Open</span></a>`).join("");
      list.querySelectorAll("a[data-rel]").forEach((link) => link.addEventListener("click", async (event) => {
        event.preventDefault();
        const response = await fetch(artifactUrl(job, link.dataset.rel), {cache: "no-store"});
        el("preview").textContent = await response.text();
      }));
    }
    function escapeHtml(value) {
      const map = {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"};
      return String(value).replace(/[&<>"']/g, (char) => map[char]);
    }
    el("jobForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = {
        worldview: el("worldview").value.trim(),
        title: el("title").value.trim(),
        shots: Number(el("shots").value || 12)
      };
      const res = await fetch("/api/jobs", {
        method: "POST",
        headers: {"Content-Type": "application/json", ...headers()},
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        el("preview").textContent = data.error || "job submission failed";
        return;
      }
      selected = data.job.job_id;
      await loadJobs();
    });
    el("refresh").addEventListener("click", () => loadJobs().catch((error) => el("preview").textContent = error.message));
    loadJobs().catch((error) => el("preview").textContent = error.message);
    setInterval(() => loadJobs().catch(() => {}), 2500);
  </script>
</body>
</html>"""


def build_handler(store: JobStore, access_token: str = "") -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:
            return

        def authorized(self, parsed) -> bool:
            if not access_token:
                return True
            query_token = (parse_qs(parsed.query).get("token") or [""])[0]
            header_token = self.headers.get("x-aigcpp-worker-token") or ""
            if query_token == access_token or header_token == access_token:
                return True
            response_json(self, {"error": "worker access token required"}, 401)
            return False

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            if path == "/":
                response_text(self, render_page())
                return
            if not self.authorized(parsed):
                return
            if path == "/api/jobs":
                response_json(self, {"jobs": store.list_jobs()})
                return
            if path.startswith("/api/jobs/"):
                job_id = unquote(path.split("/", 3)[-1])
                job = store.get(job_id)
                if not job:
                    response_json(self, {"error": "job not found"}, 404)
                    return
                response_json(self, {"job": job})
                return
            if path.startswith("/artifact/"):
                parts = path.split("/", 3)
                if len(parts) < 4:
                    response_json(self, {"error": "artifact path required"}, 400)
                    return
                job_id = unquote(parts[2])
                rel = unquote(parts[3])
                job = store.get(job_id)
                target = safe_artifact_path(job or {}, rel)
                if not target:
                    response_json(self, {"error": "artifact not found"}, 404)
                    return
                body = target.read_bytes()
                content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                if target.suffix in {".md", ".txt", ".csv", ".json"}:
                    content_type = "text/plain; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            response_json(self, {"error": "not found"}, 404)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path.rstrip("/") != "/api/jobs":
                response_json(self, {"error": "not found"}, 404)
                return
            if not self.authorized(parsed):
                return
            try:
                data = read_body_json(self)
                worldview = str(data.get("worldview") or "").strip()
                if not worldview:
                    response_json(self, {"error": "worldview is required"}, 400)
                    return
                if len(worldview) > 240:
                    response_json(self, {"error": "worldview is too long"}, 400)
                    return
                title = str(data.get("title") or "").strip()[:80]
                shots = max(4, min(60, int(data.get("shots") or 12)))
                requested_by = str(data.get("requested_by") or "web-user")[:80]
                job = store.create(worldview=worldview, title=title, shots=shots, requested_by=html.escape(requested_by))
                response_json(self, {"job": job}, 201)
            except Exception as exc:  # noqa: BLE001
                response_json(self, {"error": str(exc)}, 500)

    return Handler


def serve(*, config: WorkflowConfig, host: str, port: int, workers: int, token: str = "") -> int:
    store = JobStore(config=config, workers=workers)
    access_token = token or config.access_token
    handler = build_handler(store, access_token=access_token)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"AIGC PP Workflow worker: http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
