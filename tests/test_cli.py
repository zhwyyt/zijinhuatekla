import unittest
from unittest import mock
from pathlib import Path
from zijinhua_tekla.reports.combined import CombinedExcelResult

from zijinhua_tekla.cli import build_parser, main


class CliTests(unittest.TestCase):
    def test_gui_command_does_not_require_model_arguments(self):
        args = build_parser().parse_args(["gui"])

        self.assertEqual("gui", args.command)

    def test_gui_command_launches_gui(self):
        with mock.patch("zijinhua_tekla.gui.report_gui.main") as run_gui:
            main(["gui"])

        run_gui.assert_called_once_with()

    def test_batch_command_uses_the_gui_report_entrypoint(self):
        result = CombinedExcelResult(Path("report.xlsx"), 1, 2, 1, role_row_count=1)
        with mock.patch("zijinhua_tekla.cli.export_combined_excel", return_value=result) as export, mock.patch("builtins.print"):
            main(["export-excel", "--root", "cache", "--project-name", "项目", "--project-area", "区域", "--out", "outputs"])
        export.assert_called_once_with(Path("cache"), "项目", "区域", Path("outputs"))

    def test_batch_command_returns_failure_when_an_assembly_failed(self):
        result = CombinedExcelResult(Path("report.xlsx"), 2, 2, 1, errors=[{"error": "failed"}], role_row_count=1)
        with mock.patch("zijinhua_tekla.cli.export_combined_excel", return_value=result), mock.patch("builtins.print"):
            with self.assertRaises(SystemExit) as raised:
                main(["export-excel", "--root", "cache", "--project-name", "项目", "--project-area", "区域"])
        self.assertEqual(1, raised.exception.code)


if __name__ == "__main__":
    unittest.main()
