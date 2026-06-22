from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aigcpp.web import safe_artifact_path


class WebSecurityTest(unittest.TestCase):
    def test_safe_artifact_path_blocks_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            artifact = root / "00_manifest.json"
            artifact.write_text("{}", encoding="utf-8")
            outside = Path(tmp) / "outside.txt"
            outside.write_text("blocked", encoding="utf-8")
            job = {"project_dir": str(root)}

            self.assertEqual(artifact.resolve(), safe_artifact_path(job, "00_manifest.json"))
            self.assertIsNone(safe_artifact_path(job, "../outside.txt"))


if __name__ == "__main__":
    unittest.main()
