import unittest

from linked_demo.main import main


class LinkedDemoTests(unittest.TestCase):
    def test_entry_point_target(self):
        self.assertEqual(main(), "666DEV linked demo ready")


if __name__ == "__main__":
    unittest.main()
