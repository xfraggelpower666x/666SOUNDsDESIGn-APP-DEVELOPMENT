import unittest

from demo_app.main import main


class DemoAppTests(unittest.TestCase):
    def test_declared_entry_point_target(self):
        self.assertEqual(main(), "666DEV monorepo demo ready")


if __name__ == "__main__":
    unittest.main()
