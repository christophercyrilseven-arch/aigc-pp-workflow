from __future__ import annotations

import unittest

from aigcpp.expert_packs import load_default_packs


class ExpertPackTest(unittest.TestCase):
    def test_default_packs_have_roles_and_rules(self) -> None:
        packs = load_default_packs()
        self.assertEqual({"novel", "film"}, set(packs))
        for pack in packs.values():
            self.assertEqual("v1", pack.version)
            self.assertGreaterEqual(len(pack.roles), 4)
            self.assertGreaterEqual(len(pack.rules), 4)


if __name__ == "__main__":
    unittest.main()
