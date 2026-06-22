"""Command line interface for AIGC PP Workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aigcpp_providers import ProviderError, build_provider

from .config import WorkflowConfig, load_config
from .expert_packs import load_default_packs
from .web import serve
from .workflow import run_pipeline, validate_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aigcpp", description="AIGC Production Pipeline Workflow")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create a local config template in the current project.")

    doctor = sub.add_parser("doctor", help="Check provider config and expert packs.")
    add_common_config(doctor)

    run = sub.add_parser("run", help="Run the workflow once.")
    add_common_config(run)
    run.add_argument("--worldview", required=True)
    run.add_argument("--title", default="")
    run.add_argument("--project-id", default="")
    run.add_argument("--shots", type=int, default=12)

    serve_parser = sub.add_parser("serve", help="Start the local multi-user web worker.")
    add_common_config(serve_parser)
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8897)
    serve_parser.add_argument("--workers", type=int, default=4)
    serve_parser.add_argument("--token", default="")

    validate = sub.add_parser("validate", help="Validate an existing project directory.")
    validate.add_argument("project_dir", type=Path)
    return parser


def add_common_config(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--expert-pack-root", type=Path, default=None)


def merged_config(args: argparse.Namespace) -> WorkflowConfig:
    env = load_config()
    return WorkflowConfig(
        provider=args.provider or env.provider,
        base_url=args.base_url or env.base_url,
        model=args.model or env.model,
        api_key=args.api_key if args.api_key is not None else env.api_key,
        output_root=args.output_root or env.output_root,
        expert_pack_root=args.expert_pack_root or env.expert_pack_root,
        access_token=getattr(args, "token", "") or env.access_token,
        repair_iterations=env.repair_iterations,
    )


def command_init() -> int:
    target = Path("aigcpp.config.json")
    if target.exists():
        print(f"{target} already exists")
        return 0
    template = {
        "provider": "fake",
        "base_url": "https://model-server.example/v1",
        "model": "example-model",
        "output_root": "outputs",
        "expert_pack_root": "expert-packs",
    }
    target.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
    print(f"created {target}")
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    config = merged_config(args)
    issues: list[str] = []
    try:
        packs = load_default_packs(config.expert_pack_root)
    except Exception as exc:  # noqa: BLE001
        issues.append(f"expert packs: {exc}")
        packs = {}
    try:
        build_provider(config.provider, base_url=config.base_url, model=config.model, api_key=config.api_key)
    except ProviderError as exc:
        issues.append(f"provider: {exc}")
    config.output_root.mkdir(parents=True, exist_ok=True)
    result = {
        "ok": not issues,
        "provider": config.provider,
        "output_root": str(config.output_root),
        "expert_packs": {name: {"id": pack.pack_id, "version": pack.version} for name, pack in packs.items()},
        "issues": issues,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not issues else 2


def command_run(args: argparse.Namespace) -> int:
    config = merged_config(args)
    manifest = run_pipeline(
        worldview=args.worldview,
        title=args.title,
        project_id=args.project_id,
        shots=args.shots,
        config=config,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["ok"] else 2


def command_validate(args: argparse.Namespace) -> int:
    report = validate_project(args.project_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        return command_init()
    if args.command == "doctor":
        return command_doctor(args)
    if args.command == "run":
        return command_run(args)
    if args.command == "serve":
        config = merged_config(args)
        return serve(config=config, host=args.host, port=args.port, workers=args.workers, token=args.token)
    if args.command == "validate":
        return command_validate(args)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
