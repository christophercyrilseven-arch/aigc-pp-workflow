from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OpenSourceHygieneTest(unittest.TestCase):
    def test_repository_does_not_contain_private_machine_or_project_markers(self) -> None:
        banned = [
            "z" + "hinv",
            "织" + "女",
            "/" + "Users/",
            "wang" + "yu",
            "127." + "0.0.1",
            "local" + "host",
            "Play" + "ground 13",
            "Qwen" + "3.6",
        ]
        ignored_dirs = {".git", ".next", ".venv", "node_modules", "__pycache__", ".pytest_cache", "outputs", "tmp"}
        checked = 0
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if any(part in ignored_dirs for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            checked += 1
            lower_text = text.lower()
            for marker in banned:
                self.assertNotIn(marker.lower(), lower_text, f"{marker} found in {path.relative_to(ROOT)}")
        self.assertGreater(checked, 20)


if __name__ == "__main__":
    unittest.main()
