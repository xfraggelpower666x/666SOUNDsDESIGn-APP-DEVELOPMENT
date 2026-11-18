import subprocess
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from demo_app.main import main


class DemoAppTests(unittest.TestCase):
    def test_declared_entry_point_target(self):
        self.assertEqual(main(), "666DEV monorepo demo ready")

    def test_start_script(self):
        script = Path(__file__).resolve().parents[1] / "src" / "demo_app" / "main.py"
        process = subprocess.run([sys.executable, str(script)], capture_output=True,
                                 text=True, check=True, timeout=10)
        self.assertEqual(process.stdout.strip(), "666DEV monorepo demo ready")


if __name__ == "__main__":
    unittest.main()
