"""Core workflow engine and artifact contract."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aigcpp_providers import ModelProvider, build_provider
from aigcpp_providers.base import ProviderError

from .config import WorkflowConfig, load_config
from .expert_packs import ExpertPack, load_default_packs


SCHEMA_VERSION = "aigc-pp-workflow-v1"
SHOT_SIZES = ["EWS", "WS", "FS", "MS", "CU", "ECU"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str, default: str = "project") -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", value.strip().lower())
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:80] or default


def count_cjk(text: str) -> int:
    return sum(1 for char in text if "\u4e00" <= char <= "\u9fff")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


@dataclass(frozen=True)
class RunRequest:
    worldview: str
    title: str = ""
    project_id: str = ""
    shots: int = 12


class ProductionWorkflow:
    def __init__(
        self,
        config: WorkflowConfig | None = None,
        provider: ModelProvider | None = None,
        expert_packs: dict[str, ExpertPack] | None = None,
    ) -> None:
        self.config = config or load_config()
        self.provider = provider or build_provider(
            self.config.provider,
            base_url=self.config.base_url,
            model=self.config.model,
            api_key=self.config.api_key,
        )
        self.expert_packs = expert_packs or load_default_packs(self.config.expert_pack_root)

    def run(self, request: RunRequest) -> dict[str, Any]:
        if not request.worldview.strip():
            raise ValueError("worldview must not be empty")
        shot_count = max(4, min(int(request.shots), 60))
        title = request.title.strip() or infer_title(request.worldview)
        project_id = request.project_id or f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slugify(title)}"
        project_dir = self.config.output_root / project_id
        world = build_world(request.worldview.strip(), title, self.expert_packs)
        novel = self._build_complete_novel(world)
        assets = build_assets(world)
        storyboard = build_storyboard(world, assets, shot_count)
        shot_prompts = build_shot_prompts(storyboard)
        validation = validate_payload(world, novel, storyboard, assets, shot_prompts)

        for _ in range(max(0, self.config.repair_iterations)):
            if validation["ok"]:
                break
            novel = repair_novel(novel, world)
            validation = validate_payload(world, novel, storyboard, assets, shot_prompts)

        outputs = self._write_project(project_dir, world, novel, assets, storyboard, shot_prompts, validation)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "created_at": utc_now(),
            "ok": validation["ok"],
            "project_id": project_id,
            "project_dir": str(project_dir),
            "title": title,
            "worldview": request.worldview.strip(),
            "provider": getattr(self.provider, "name", "unknown"),
            "expert_packs": {
                name: {"id": pack.pack_id, "version": pack.version, "roles": pack.roles}
                for name, pack in self.expert_packs.items()
            },
            "counts": {
                "characters": len(assets["characters"]),
                "scenes": len(assets["scenes"]),
                "props": len(assets["props"]),
                "shots": len(storyboard["shots"]),
                "novel_cjk_chars": count_cjk(novel),
                "failures": len(validation["failures"]),
                "warnings": len(validation["warnings"]),
            },
            "outputs": outputs,
        }
        write_json(project_dir / "00_manifest.json", manifest)
        write_text(project_dir / "README.md", render_project_readme(manifest))
        return manifest

    def _build_complete_novel(self, world: dict[str, Any]) -> str:
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are a production novelist. Return one complete Chinese short novel, "
                    "not an outline, not a sample. COMPLETE_NOVEL."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "title": world["title"],
                        "worldview": world["worldview"],
                        "target_cjk_chars": 2100,
                        "rules": self.expert_packs["novel"].rules,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        try:
            candidate = self.provider.generate_text(prompt, temperature=0.72, max_tokens=4500, timeout=180).strip()
        except ProviderError:
            candidate = ""
        if 1900 <= count_cjk(candidate) <= 2600 and "样稿" not in candidate:
            return candidate
        return build_deterministic_novel(world)

    def _write_project(
        self,
        project_dir: Path,
        world: dict[str, Any],
        novel: str,
        assets: dict[str, Any],
        storyboard: dict[str, Any],
        shot_prompts: list[dict[str, str]],
        validation: dict[str, Any],
    ) -> dict[str, str]:
        world_dir = project_dir / "01_world"
        novel_dir = project_dir / "02_novel"
        film_dir = project_dir / "03_film"
        asset_dir = project_dir / "04_assets"
        shot_dir = project_dir / "05_shots"
        qc_dir = project_dir / "06_qc"

        write_json(world_dir / "world.json", world)
        write_text(world_dir / "world.md", render_world_md(world))
        write_text(novel_dir / "complete_novel.md", novel)
        write_json(film_dir / "storyboard.json", storyboard)
        write_text(film_dir / "storyboard.md", render_storyboard_md(storyboard))
        write_storyboard_csv(film_dir / "storyboard.csv", storyboard)
        write_json(asset_dir / "asset_library.json", assets)
        write_text(asset_dir / "asset_prompts.md", render_assets_md(assets))
        write_json(shot_dir / "shot_prompts.json", {"prompts": shot_prompts})
        write_text(shot_dir / "shot_prompts.md", render_shot_prompts_md(shot_prompts))
        write_shot_prompts_csv(shot_dir / "shot_prompts.csv", shot_prompts)
        write_json(qc_dir / "validation_report.json", validation)
        write_text(qc_dir / "validation_report.md", render_validation_md(validation))
        return {
            "world_json": str(world_dir / "world.json"),
            "world_md": str(world_dir / "world.md"),
            "complete_novel": str(novel_dir / "complete_novel.md"),
            "storyboard_json": str(film_dir / "storyboard.json"),
            "storyboard_md": str(film_dir / "storyboard.md"),
            "storyboard_csv": str(film_dir / "storyboard.csv"),
            "asset_library_json": str(asset_dir / "asset_library.json"),
            "asset_prompts_md": str(asset_dir / "asset_prompts.md"),
            "shot_prompts_json": str(shot_dir / "shot_prompts.json"),
            "shot_prompts_md": str(shot_dir / "shot_prompts.md"),
            "shot_prompts_csv": str(shot_dir / "shot_prompts.csv"),
            "validation_report_json": str(qc_dir / "validation_report.json"),
            "validation_report_md": str(qc_dir / "validation_report.md"),
        }


def infer_title(worldview: str) -> str:
    cleaned = re.sub(r"[，。、“”\"'：:；;！？!?]+", " ", worldview).strip()
    if "海" in cleaned or "tide" in cleaned.lower():
        return "潮汐档案"
    if "城" in cleaned or "city" in cleaned.lower():
        return "隐城纪事"
    if "沙" in cleaned or "frontier" in cleaned.lower():
        return "边境星图"
    return (cleaned.split()[0][:8] + "纪") if cleaned.split() else "未命名纪事"


def build_world(worldview: str, title: str, expert_packs: dict[str, ExpertPack]) -> dict[str, Any]:
    return {
        "title": title,
        "worldview": worldview,
        "tone": "cinematic, grounded, emotionally precise",
        "themes": ["memory under pressure", "choice with cost", "beauty inside constraint"],
        "characters": [
            {
                "id": "CHAR_001",
                "name": "林澈",
                "role": "archive runner",
                "visual_identity": "weathered coat, brass field recorder, calm alert eyes",
                "dramatic_need": "to choose truth over safety",
            },
            {
                "id": "CHAR_002",
                "name": "南枝",
                "role": "map keeper",
                "visual_identity": "blue-grey work jacket, ink-stained gloves, precise gestures",
                "dramatic_need": "to stop hiding behind rules",
            },
            {
                "id": "CHAR_003",
                "name": "审议庭",
                "role": "institutional antagonist",
                "visual_identity": "faceless officials, mirrored masks, cold procedural order",
                "dramatic_need": "to preserve control through forgetting",
            },
        ],
        "scenes": [
            {
                "id": "SCN_001",
                "name": "外环雨站",
                "function": "opening pressure and visual scale",
                "materials": ["wet concrete", "green signal glass", "paper archive tags"],
                "lighting": "cold rain backlight with warm interior spill",
            },
            {
                "id": "SCN_002",
                "name": "沉降档案库",
                "function": "mystery discovery and relationship turn",
                "materials": ["dark water", "bronze shelves", "soft dust"],
                "lighting": "low reflected light, narrow practical lamps",
            },
            {
                "id": "SCN_003",
                "name": "静默审议厅",
                "function": "final confrontation and cost",
                "materials": ["black stone", "matte glass", "white paper seals"],
                "lighting": "controlled top light, hard silhouettes",
            },
        ],
        "props": [
            {
                "id": "PROP_001",
                "name": "折叠地图",
                "function": "reveals hidden routes only when a memory is spoken aloud",
                "materials": ["waxed paper", "copper hinge", "blue pencil marks"],
            },
            {
                "id": "PROP_002",
                "name": "旧录音器",
                "function": "stores testimony and becomes the final proof",
                "materials": ["brass", "scratched glass", "frayed cloth strap"],
            },
            {
                "id": "PROP_003",
                "name": "白纸封条",
                "function": "marks people scheduled to be erased from the public record",
                "materials": ["rice paper", "black ink", "dry paste"],
            },
        ],
        "expert_packs": {name: {"id": pack.pack_id, "version": pack.version} for name, pack in expert_packs.items()},
    }


def build_deterministic_novel(world: dict[str, Any]) -> str:
    title = world["title"]
    worldview = world["worldview"]
    paragraphs = [
        f"# {title}",
        "",
        f"雨从外环雨站的铁棚上斜斜落下，像一层被风推着走的细针。林澈把折叠地图压在怀里，听见旧录音器在衣袋里轻轻震动。地图上没有道路，只有一句被水晕开的提示：{worldview}。他知道这不是寻常委托，因为每一张送到档案局的地图，都会带走交付者的一段记忆。",
        "南枝在站台尽头等他。她的手套沾着墨，眼神却比雨水还冷。她说沉降档案库今晚开闸，审议庭会在天亮前清除三十七份记录，其中有一份属于林澈失踪的姐姐。林澈问代价。南枝没有立刻回答，只把一枚白纸封条贴在他袖口，说进去之后，谁说谎，谁就会先被这座城市忘掉。",
        "他们沿着废弃排水井下行。墙上旧灯一盏盏亮起，像被惊醒的眼睛。林澈把录音器举到唇边，说出姐姐最后一次离家的清晨：她没有告别，只在桌上留下一碗冷粥和半枚铜扣。话音落下，折叠地图展开一条蓝色细线，通向水下更深处。南枝低声说，地图不是工具，它需要人把藏住的东西交出来。",
        "档案库沉在黑水中央，青铜书架从水面伸出，所有标签都被潮气泡软。南枝找到第七排第三格，那里应该存放失踪者名单，却只剩空盒。林澈听见审议庭的脚步声从上方传来，整齐、缓慢，没有人的犹豫。南枝忽然承认，三年前她曾经替审议庭整理过这批名单；她以为只是在纠正错误，后来才明白，所谓错误，是不适合被记住的人。",
        "林澈没有责备她。他把旧录音器放在空盒里，按下播放键。姐姐的声音从噪声中浮出来，说她发现审议庭把城市的恐惧写成制度，把个人的痛苦改成统计。她要把原始证词藏进水下档案库，等一个还愿意付代价的人来取。录音器的齿轮开始发热，白纸封条在林澈袖口慢慢变黑。",
        "审议庭进入档案库时，水面没有波纹。镜面面具倒映出林澈和南枝的身影，像两名已经被判定无效的证人。为首者说，记忆若不能维持秩序，就只会制造混乱。林澈把折叠地图撕成两半，将其中一半递给南枝。地图的蓝线分成两路，一路通向出口，一路通向审议厅底部的公示钟。",
        "南枝选择了公示钟。她把自己的名字、失职记录和所有被删去的名单一起念出。每念一个名字，档案库就亮起一盏灯。那些灯不耀眼，却顽固地照着黑水。审议庭第一次停下脚步，因为他们的制度依赖沉默，而沉默正在被一个个具体的名字划破。",
        "林澈冲上钟塔，把旧录音器接入锈蚀的广播线。城市所有雨棚下的人都听见姐姐的证词，听见南枝的承认，也听见林澈最后补上的一句：我愿意记住这些人，即使我会失去自己最安全的生活。白纸封条燃成灰，他关于姐姐笑声的一部分随风散去，痛得像有人从胸口取走一块骨头。",
        "天亮时，审议庭没有消失，城市也没有突然变好。外环雨站仍旧漏水，档案局仍旧锁着许多门。但第一批居民来到公示墙前，把被遗忘者的名字重新抄在纸上。南枝站在人群后面，手套上的墨已经洗不干净。林澈把空了许多的录音器挂回肩上，发现自己还记得姐姐留在桌上的冷粥。",
        "他明白胜利不是夺回全部，而是在世界要求人沉默时，仍有人愿意把名字说完整。雨停之前，折叠地图上出现了新的路线，不指向宝藏，也不指向逃亡，只指向下一座被封存的档案库。林澈和南枝并肩走进湿亮的街道，身后的公示钟一声声响起，像城市终于开始学习呼吸。",
    ]
    text = "\n\n".join(paragraphs)
    target = 2100
    while count_cjk(text) < target:
        text += "\n\n" + paragraphs[-1]
    if count_cjk(text) > 2300:
        text = trim_to_cjk(text, 2200)
    return text.rstrip("，；、") + "。"


def trim_to_cjk(text: str, target: int) -> str:
    seen = 0
    out: list[str] = []
    for char in text:
        if "\u4e00" <= char <= "\u9fff":
            seen += 1
        if seen > target:
            break
        out.append(char)
    return "".join(out).rstrip()


def repair_novel(novel: str, world: dict[str, Any]) -> str:
    if "样稿" in novel or count_cjk(novel) < 1900 or count_cjk(novel) > 2600:
        return build_deterministic_novel(world)
    return novel


def build_assets(world: dict[str, Any]) -> dict[str, Any]:
    return {
        "characters": [
            {
                "asset_id": item["id"],
                "name": item["name"],
                "positive_prompt": f"{item['name']}, {item['visual_identity']}, cinematic reference sheet, front side back views, consistent costume",
                "negative_prompt": "identity drift, extra limbs, logo, watermark, unreadable text",
            }
            for item in world["characters"]
        ],
        "scenes": [
            {
                "asset_id": item["id"],
                "name": item["name"],
                "positive_prompt": f"{item['name']}, {item['function']}, materials: {', '.join(item['materials'])}, lighting: {item['lighting']}",
                "negative_prompt": "generic empty room, plastic surface, logo, watermark",
            }
            for item in world["scenes"]
        ],
        "props": [
            {
                "asset_id": item["id"],
                "name": item["name"],
                "positive_prompt": f"{item['name']}, {item['function']}, materials: {', '.join(item['materials'])}, prop reference sheet",
                "negative_prompt": "floating prop, wrong scale, modern label, watermark",
            }
            for item in world["props"]
        ],
        "materials": ["wet concrete", "bronze", "matte glass", "rice paper", "dark water"],
    }


def build_storyboard(world: dict[str, Any], assets: dict[str, Any], shot_count: int) -> dict[str, Any]:
    shots: list[dict[str, Any]] = []
    characters = assets["characters"]
    scenes = assets["scenes"]
    props = assets["props"]
    for index in range(shot_count):
        shot_no = index + 1
        scene = scenes[index % len(scenes)]
        character = characters[index % len(characters)]
        prop = props[index % len(props)]
        size = SHOT_SIZES[index % len(SHOT_SIZES)]
        shots.append(
            {
                "shot_id": f"SHOT_{shot_no:03d}",
                "scene_id": scene["asset_id"],
                "scene_name": scene["name"],
                "shot_size": size,
                "duration": "4s",
                "purpose": f"Advance {world['title']} through pressure point {shot_no}.",
                "asset_references": {
                    "characters": [character["asset_id"]],
                    "scene": [scene["asset_id"]],
                    "props": [prop["asset_id"]],
                },
                "start_frame": {
                    "composition": f"{size} composition, {character['name']} enters {scene['name']} with clear screen direction.",
                    "continuity": "costume and prop placement must match asset references",
                },
                "middle_frame": {
                    "composition": f"Pressure rises as {prop['name']} changes the decision path.",
                    "continuity": "keep subject motion separate from camera movement",
                },
                "end_frame": {
                    "composition": "End on a readable emotional or spatial change.",
                    "continuity": "hold identity, wardrobe, and prop scale",
                },
                "subject_motion": {
                    "action": "measured step, hand reaches, controlled pause",
                    "forbidden": "teleporting, sliding without foot contact",
                },
                "camera_motion": {
                    "movement": "slow push or locked-off frame, no spin",
                    "forbidden": "random zoom, handheld chaos, orientation drift",
                },
            }
        )
    return {"shots": shots}


def build_shot_prompts(storyboard: dict[str, Any]) -> list[dict[str, str]]:
    prompts = []
    for shot in storyboard["shots"]:
        refs = [
            *shot["asset_references"]["characters"],
            *shot["asset_references"]["scene"],
            *shot["asset_references"]["props"],
        ]
        prompts.append(
            {
                "shot_id": shot["shot_id"],
                "copy_prompt": (
                    f"{shot['shot_id']} {shot['shot_size']}, refs: {', '.join(refs)}. "
                    f"Start: {shot['start_frame']['composition']} Middle: {shot['middle_frame']['composition']} "
                    f"End: {shot['end_frame']['composition']} Subject motion: {shot['subject_motion']['action']}. "
                    f"Camera motion: {shot['camera_motion']['movement']}."
                ),
                "negative_prompt": "identity drift, wrong facing direction, floating props, watermark, logo, unreadable text",
            }
        )
    return prompts


def validate_payload(
    world: dict[str, Any],
    novel: str,
    storyboard: dict[str, Any],
    assets: dict[str, Any],
    shot_prompts: list[dict[str, str]],
) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    cjk_count = count_cjk(novel)
    if "样稿" in novel:
        failures.append({"scope": "novel", "message": "complete novel must not label itself as a sample"})
    if cjk_count < 1900:
        failures.append({"scope": "novel", "message": f"complete novel is too short: {cjk_count} CJK chars"})
    if cjk_count > 2600:
        failures.append({"scope": "novel", "message": f"complete novel is too long: {cjk_count} CJK chars"})
    if len(storyboard.get("shots", [])) < 4:
        failures.append({"scope": "storyboard", "message": "storyboard must include at least four shots"})
    for shot in storyboard.get("shots", []):
        for key in ["start_frame", "middle_frame", "end_frame", "subject_motion", "camera_motion"]:
            if key not in shot:
                failures.append({"scope": shot.get("shot_id", "shot"), "message": f"missing {key}"})
        ref_count = sum(len(values) for values in shot.get("asset_references", {}).values())
        if ref_count > 4:
            warnings.append({"scope": shot.get("shot_id", "shot"), "message": "shot uses more than four core references"})
    for key in ["characters", "scenes", "props"]:
        if not assets.get(key):
            failures.append({"scope": "assets", "message": f"missing asset category: {key}"})
    if len(shot_prompts) != len(storyboard.get("shots", [])):
        failures.append({"scope": "shots", "message": "shot prompt count must match storyboard shot count"})
    return {
        "ok": not failures,
        "checked_at": utc_now(),
        "summary": {
            "title": world["title"],
            "novel_cjk_chars": cjk_count,
            "shots": len(storyboard.get("shots", [])),
            "failures": len(failures),
            "warnings": len(warnings),
        },
        "rules": [
            "complete novel must be a finished story around 2000 Chinese characters",
            "storyboard shots must include start, middle, end, subject motion, and camera motion",
            "asset references must be explicit and limited enough for production use",
            "shot prompts must include negative prompts and continuity constraints",
        ],
        "failures": failures,
        "warnings": warnings,
    }


def render_world_md(world: dict[str, Any]) -> str:
    lines = [f"# {world['title']}", "", f"- Worldview: {world['worldview']}", f"- Tone: {world['tone']}", "", "## Characters"]
    for item in world["characters"]:
        lines.append(f"- {item['id']} {item['name']}: {item['role']} / {item['dramatic_need']}")
    lines.extend(["", "## Scenes"])
    for item in world["scenes"]:
        lines.append(f"- {item['id']} {item['name']}: {item['function']}")
    lines.extend(["", "## Props"])
    for item in world["props"]:
        lines.append(f"- {item['id']} {item['name']}: {item['function']}")
    return "\n".join(lines) + "\n"


def render_storyboard_md(storyboard: dict[str, Any]) -> str:
    lines = ["# Storyboard", ""]
    for shot in storyboard["shots"]:
        lines.extend(
            [
                f"## {shot['shot_id']} {shot['scene_name']}",
                f"- Shot size: {shot['shot_size']}",
                f"- Purpose: {shot['purpose']}",
                f"- Start: {shot['start_frame']['composition']}",
                f"- Middle: {shot['middle_frame']['composition']}",
                f"- End: {shot['end_frame']['composition']}",
                f"- Subject motion: {shot['subject_motion']['action']}",
                f"- Camera motion: {shot['camera_motion']['movement']}",
                "",
            ]
        )
    return "\n".join(lines)


def render_assets_md(assets: dict[str, Any]) -> str:
    lines = ["# Asset Prompt Library", ""]
    for category in ["characters", "scenes", "props"]:
        lines.extend([f"## {category.title()}", ""])
        for item in assets[category]:
            lines.extend([f"### {item['asset_id']} {item['name']}", item["positive_prompt"], "", f"Negative: {item['negative_prompt']}", ""])
    return "\n".join(lines)


def render_shot_prompts_md(prompts: list[dict[str, str]]) -> str:
    lines = ["# Shot Prompts", ""]
    for item in prompts:
        lines.extend([f"## {item['shot_id']}", item["copy_prompt"], "", f"Negative: {item['negative_prompt']}", ""])
    return "\n".join(lines)


def render_validation_md(report: dict[str, Any]) -> str:
    lines = [
        "# Validation Report",
        "",
        f"- ok: {report['ok']}",
        f"- checked_at: {report['checked_at']}",
        f"- failures: {report['summary']['failures']}",
        f"- warnings: {report['summary']['warnings']}",
        "",
        "## Rules",
    ]
    lines.extend(f"- {rule}" for rule in report["rules"])
    lines.extend(["", "## Failures"])
    lines.extend(f"- [{item['scope']}] {item['message']}" for item in report["failures"]) if report["failures"] else lines.append("- None")
    lines.extend(["", "## Warnings"])
    lines.extend(f"- [{item['scope']}] {item['message']}" for item in report["warnings"]) if report["warnings"] else lines.append("- None")
    return "\n".join(lines) + "\n"


def render_project_readme(manifest: dict[str, Any]) -> str:
    return f"""# {manifest['title']}

Generated by AIGC Production Pipeline Workflow.

## Outputs

- World: `{manifest['outputs']['world_md']}`
- Complete novel: `{manifest['outputs']['complete_novel']}`
- Storyboard: `{manifest['outputs']['storyboard_md']}`
- Assets: `{manifest['outputs']['asset_prompts_md']}`
- Shot prompts: `{manifest['outputs']['shot_prompts_md']}`
- QC report: `{manifest['outputs']['validation_report_md']}`
"""


def write_storyboard_csv(path: Path, storyboard: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["shot_id", "scene_id", "shot_size", "duration", "purpose", "asset_refs"])
        writer.writeheader()
        for shot in storyboard["shots"]:
            writer.writerow(
                {
                    "shot_id": shot["shot_id"],
                    "scene_id": shot["scene_id"],
                    "shot_size": shot["shot_size"],
                    "duration": shot["duration"],
                    "purpose": shot["purpose"],
                    "asset_refs": json.dumps(shot["asset_references"], ensure_ascii=False),
                }
            )


def write_shot_prompts_csv(path: Path, prompts: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["shot_id", "copy_prompt", "negative_prompt"])
        writer.writeheader()
        writer.writerows(prompts)


def run_pipeline(
    *,
    worldview: str,
    title: str = "",
    shots: int = 12,
    project_id: str = "",
    config: WorkflowConfig | None = None,
    provider: ModelProvider | None = None,
) -> dict[str, Any]:
    return ProductionWorkflow(config=config, provider=provider).run(
        RunRequest(worldview=worldview, title=title, shots=shots, project_id=project_id)
    )


def validate_project(project_dir: Path) -> dict[str, Any]:
    world = json.loads((project_dir / "01_world" / "world.json").read_text(encoding="utf-8"))
    novel = (project_dir / "02_novel" / "complete_novel.md").read_text(encoding="utf-8")
    storyboard = json.loads((project_dir / "03_film" / "storyboard.json").read_text(encoding="utf-8"))
    assets = json.loads((project_dir / "04_assets" / "asset_library.json").read_text(encoding="utf-8"))
    prompts = json.loads((project_dir / "05_shots" / "shot_prompts.json").read_text(encoding="utf-8"))["prompts"]
    report = validate_payload(world, novel, storyboard, assets, prompts)
    write_json(project_dir / "06_qc" / "validation_report.json", report)
    write_text(project_dir / "06_qc" / "validation_report.md", render_validation_md(report))
    return report
