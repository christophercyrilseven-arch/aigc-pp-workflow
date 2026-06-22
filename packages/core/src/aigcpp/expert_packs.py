"""Expert pack loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import REPO_ROOT


@dataclass(frozen=True)
class ExpertPack:
    pack_id: str
    version: str
    name: str
    roles: list[str]
    rules: list[str]
    path: Path


def _parse_simple_yaml(path: Path) -> dict[str, object]:
    data: dict[str, object] = {}
    current_list: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- ") and current_list:
            value = line[2:].strip()
            assert isinstance(data[current_list], list)
            data[current_list].append(value)
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                data[key] = value.strip('"')
                current_list = None
            else:
                data[key] = []
                current_list = key
    return data


def load_expert_pack(kind: str, version: str = "v1", root: Path | None = None) -> ExpertPack:
    base = root or (REPO_ROOT / "expert-packs")
    path = base / kind / version
    manifest_path = path / "expert-pack.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"expert pack not found: {kind}/{version}")
    raw = _parse_simple_yaml(manifest_path)
    pack_id = str(raw.get("id") or "").strip()
    name = str(raw.get("name") or "").strip()
    pack_version = str(raw.get("version") or "").strip()
    roles = [str(item).strip() for item in raw.get("roles", []) if str(item).strip()]
    rules = [str(item).strip() for item in raw.get("rules", []) if str(item).strip()]
    if not pack_id or not name or not pack_version:
        raise ValueError(f"expert pack metadata is incomplete: {manifest_path}")
    if not roles:
        raise ValueError(f"expert pack must define at least one role: {manifest_path}")
    if not rules:
        raise ValueError(f"expert pack must define at least one rule: {manifest_path}")
    return ExpertPack(pack_id=pack_id, version=pack_version, name=name, roles=roles, rules=rules, path=path)


def load_default_packs(root: Path | None = None) -> dict[str, ExpertPack]:
    return {
        "novel": load_expert_pack("novel", root=root),
        "film": load_expert_pack("film", root=root),
    }
