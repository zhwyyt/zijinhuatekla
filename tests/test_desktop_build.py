import os
from pathlib import Path
import unittest
from unittest import mock

from scripts.build_desktop import build_environment


class DesktopBuildTests(unittest.TestCase):
    def test_unrelated_dll_directory_is_not_in_build_search_path(self):
        with mock.patch.dict(os.environ, {"PATH": r"C:\unrelated\poppler\bin", "SystemRoot": r"C:\Windows"}):
            environment = build_environment()
            self.assertNotIn("poppler", environment["PATH"])
            self.assertIn(str(Path(r"C:\Windows") / "System32"), environment["PATH"].split(os.pathsep))
            self.assertEqual(r"C:\unrelated\poppler\bin", os.environ["PATH"])


if __name__ == "__main__":
    unittest.main()
