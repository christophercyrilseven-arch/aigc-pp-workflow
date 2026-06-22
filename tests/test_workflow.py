from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aigcpp.config import WorkflowConfig
from aigcpp.workflow import count_cjk, run_pipeline, validate_project
from aigcpp_providers import FakeProvider


class WorkflowTest(unittest.TestCase):
    def test_pipeline_writes_required_delivery_files_and_passes_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = WorkflowConfig(output_root=Path(tmp))
            manifest = run_pipeline(
                worldview="A frontier archivist follows a forbidden map into a city under the sea",
                title="Tide Archive",
                project_id="smoke",
                shots=12,
                config=config,
                provider=FakeProvider(),
            )
            self.assertTrue(manifest["ok"])
            project_dir = Path(manifest["project_dir"])
            expected = [
                "world_json",
                "world_md",
                "complete_novel",
                "storyboard_json",
                "storyboard_md",
                "storyboard_csv",
                "asset_library_json",
                "asset_prompts_md",
                "shot_prompts_json",
                "shot_prompts_md",
                "shot_prompts_csv",
                "validation_report_json",
                "validation_report_md",
            ]
            for key in expected:
                self.assertTrue(Path(manifest["outputs"][key]).exists(), key)

            novel = (project_dir / "02_novel" / "complete_novel.md").read_text(encoding="utf-8")
            self.assertNotIn("样稿", novel)
            self.assertGreaterEqual(count_cjk(novel), 1900)
            self.assertLessEqual(count_cjk(novel), 2600)

            storyboard = json.loads((project_dir / "03_film" / "storyboard.json").read_text(encoding="utf-8"))
            self.assertEqual(len(storyboard["shots"]), 12)
            for shot in storyboard["shots"]:
                self.assertIn("start_frame", shot)
                self.assertIn("middle_frame", shot)
                self.assertIn("end_frame", shot)
                self.assertIn("subject_motion", shot)
                self.assertIn("camera_motion", shot)

            report = validate_project(project_dir)
            self.assertTrue(report["ok"])


if __name__ == "__main__":
    unittest.main()
