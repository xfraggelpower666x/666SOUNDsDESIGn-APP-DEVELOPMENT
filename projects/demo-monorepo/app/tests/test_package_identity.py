from pathlib import Path
import unittest


class PackageIdentityTests(unittest.TestCase):
    def test_package_description(self):
        initializer = Path(__file__).resolve().parents[1] / "src" / "demo_app" / "__init__.py"
        self.assertIn("666DEV monorepo profile", initializer.read_text(encoding="utf-8"))
