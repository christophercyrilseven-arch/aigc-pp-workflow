from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "worldbuilding-novel-expert"


class SkillPackageTest(unittest.TestCase):
    def test_worldbuilding_novel_skill_is_installable(self) -> None:
        skill_md = SKILL / "SKILL.md"
        agents_yaml = SKILL / "agents" / "openai.yaml"
        reference = SKILL / "references" / "methodology.md"

        self.assertTrue(skill_md.exists())
        self.assertTrue(agents_yaml.exists())
        self.assertTrue(reference.exists())

        skill_text = skill_md.read_text(encoding="utf-8")
        self.assertNotIn("TODO", skill_text)
        self.assertIn("name: worldbuilding-novel-expert", skill_text)
        self.assertRegex(skill_text, re.compile(r"^description: .{80,}$", re.MULTILINE))
        self.assertIn("complete short novel", skill_text)
        self.assertIn("references/methodology.md", skill_text)

        agents_text = agents_yaml.read_text(encoding="utf-8")
        self.assertIn("display_name: \"Worldbuilding Novel Expert\"", agents_text)
        self.assertIn("$worldbuilding-novel-expert", agents_text)


if __name__ == "__main__":
    unittest.main()
