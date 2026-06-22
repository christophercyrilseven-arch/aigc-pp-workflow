"""Runtime configuration for the workflow."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class WorkflowConfig:
    provider: str = "fake"
    base_url: str = "https://model-server.example/v1"
    model: str = "example-model"
    api_key: str = ""
    output_root: Path = Path("outputs")
    expert_pack_root: Path = REPO_ROOT / "expert-packs"
    access_token: str = ""
    repair_iterations: int = 2


def load_config() -> WorkflowConfig:
    return WorkflowConfig(
        provider=os.environ.get("AIGCPP_PROVIDER", "fake"),
        base_url=os.environ.get("AIGCPP_BASE_URL", "https://model-server.example/v1"),
        model=os.environ.get("AIGCPP_MODEL", "example-model"),
        api_key=os.environ.get("AIGCPP_API_KEY", ""),
        output_root=Path(os.environ.get("AIGCPP_OUTPUT_ROOT", "outputs")),
        expert_pack_root=Path(os.environ.get("AIGCPP_EXPERT_PACK_ROOT", str(REPO_ROOT / "expert-packs"))),
        access_token=os.environ.get("AIGCPP_ACCESS_TOKEN", ""),
        repair_iterations=int(os.environ.get("AIGCPP_REPAIR_ITERATIONS", "2")),
    )
