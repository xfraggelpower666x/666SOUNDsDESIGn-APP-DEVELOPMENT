import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from demo_app.main import main


class DemoAppTests(unittest.TestCase):
    def test_declared_entry_point_target(self):
        self.assertEqual(main(), "666DEV monorepo demo ready")


if __name__ == "__main__":
    unittest.main()
