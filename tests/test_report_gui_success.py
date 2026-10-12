import unittest
from unittest import mock

from PySide6.QtWidgets import QApplication

from zijinhua_tekla.gui.report_gui import ReportGUI
from zijinhua_tekla.reports.combined import CombinedExcelResult


APP = QApplication.instance() or QApplication([])


class ReportGuiSuccessTests(unittest.TestCase):
    def test_successful_excel_generation_shows_popup(self):
        app = ReportGUI()
        app.active_kind = "offline"
        try:
            result = CombinedExcelResult(None, 1, 2, 1, role_row_count=1)
            with mock.patch("zijinhua_tekla.gui.report_gui.QMessageBox.information") as popup:
                app._show_success(result)
            self.assertIn("构件角色 1 行", popup.call_args.args[2])
        finally:
            app.close()

    def test_partial_failure_and_axis_review_are_both_shown(self):
        app = ReportGUI()
        app.active_kind = "offline"
        try:
            result = CombinedExcelResult(None, 2, 2, 1, errors=[{"error": "缺快照"}], role_row_count=1, axis_review_count=1)
            with mock.patch("zijinhua_tekla.gui.report_gui.QMessageBox.warning") as warning:
                app._show_success(result)
            message = warning.call_args.args[2]
            self.assertIn("识别失败", message)
            self.assertIn("重新导出", message)
            self.assertIn("失败 1 个", message)
        finally:
            app.close()


if __name__ == "__main__":
    unittest.main()
