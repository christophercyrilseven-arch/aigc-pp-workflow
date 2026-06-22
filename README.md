# AIGC Production Pipeline Workflow

`aigc-pp-workflow` is a local-first open-source workflow for turning a short
world concept into a complete creative production package:

- world rules and creative bible
- complete short novel
- film storyboard
- character, scene, prop, and material assets
- shot-level generation prompts
- quality checks and limited automatic repair

The public methodology is documented in
[`docs/methodology.md`](docs/methodology.md). It focuses on world rules,
character choice with cost, scene pressure, complete-novel delivery, continuity
state, film translation, and QC-to-repair loops.

The project is designed so each user can connect their own local model or their
own API endpoint. The public web entry is only a proxy and interface; generation
stays on the user's worker.

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
aigcpp doctor
aigcpp run --worldview "A frontier archivist follows a forbidden map into a city under the sea" --title "Tide Archive" --shots 12
aigcpp serve --host 0.0.0.0 --port 8897 --workers 4
```

The default provider is `fake` so the workflow can be tested without a model.
For real generation, configure a provider:

```bash
export AIGCPP_PROVIDER=openai-compatible
export AIGCPP_BASE_URL=https://model-server.example/v1
export AIGCPP_MODEL=your-model-name
export AIGCPP_API_KEY=
```

Ollama-compatible usage:

```bash
export AIGCPP_PROVIDER=ollama
export AIGCPP_BASE_URL=https://ollama-server.example
export AIGCPP_MODEL=your-model-name
```

## Repository Layout

- `packages/core/` - workflow engine, CLI, artifact contract, validation, local web worker
- `packages/providers/` - OpenAI-compatible and Ollama provider adapters
- `expert-packs/novel/v1/` - versioned novel expert pack
- `expert-packs/film/v1/` - versioned film expert pack
- `skills/worldbuilding-novel-expert/` - installable Codex skill for the novel methodology
- `docs/` - public methodology and operating notes
- `apps/local-web/` - local web worker notes
- `apps/public-entry/` - optional Vercel-ready public entry
- `tests/` - workflow, provider, web, expert-pack, and hygiene tests

## Codex Skill

The worldbuilding novel expert is also packaged as a Codex skill:

```text
skills/worldbuilding-novel-expert/
```

To install it from this repository, copy that folder into your Codex skills
directory, for example:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/worldbuilding-novel-expert "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Then invoke it with `$worldbuilding-novel-expert` when turning a worldview or
story-world concept into a complete short novel package.

## CLI

```bash
aigcpp init
aigcpp doctor
aigcpp run --worldview "..." --title "..." --shots 12
aigcpp serve --host 0.0.0.0 --port 8897 --workers 4 --token "change-me"
aigcpp validate outputs/<project-id>
```

## Artifact Contract

Each run creates a project directory with:

```text
00_manifest.json
01_world/
02_novel/complete_novel.md
03_film/storyboard.json
03_film/storyboard.md
03_film/storyboard.csv
04_assets/
05_shots/
06_qc/validation_report.json
06_qc/validation_report.md
```

## Public Entry Shape

`apps/public-entry` is a Next.js app intended for deployment on Vercel or a
similar platform. It does not run generation itself. Configure:

- `AIGCPP_WORKER_URL` - HTTPS URL for the user's worker
- `AIGCPP_ACCESS_TOKEN` - optional token required by the public entry
- `AIGCPP_WORKER_TOKEN` - optional backend token sent from the public entry to the worker

Do not expose a worker publicly without access control.

## License

Apache-2.0.
