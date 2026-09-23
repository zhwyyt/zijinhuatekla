import unittest
from unittest import mock

from zijinhua_tekla.cli import build_parser, main


class CliTests(unittest.TestCase):
    def test_gui_command_does_not_require_model_arguments(self):
        args = build_parser().parse_args(["gui"])

        self.assertEqual("gui", args.command)

    def test_gui_command_launches_gui(self):
        with mock.patch("zijinhua_tekla.gui.report_gui.main") as run_gui:
            main(["gui"])

        run_gui.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
