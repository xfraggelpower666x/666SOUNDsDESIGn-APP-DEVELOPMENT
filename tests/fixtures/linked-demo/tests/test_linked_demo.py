import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from linked_demo.main import main


class LinkedDemoTests(unittest.TestCase):
    def test_entry_point_target(self):
        self.assertEqual(main(), "666DEV linked demo ready")


if __name__ == "__main__":
    unittest.main()
