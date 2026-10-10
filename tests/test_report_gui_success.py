import unittest
from unittest import mock

from zijinhua_tekla.gui.report_gui import ReportGUI
from zijinhua_tekla.reports.combined import CombinedExcelResult


class ReportGuiSuccessTests(unittest.TestCase):
    def test_successful_excel_generation_shows_popup(self):
        app = ReportGUI()
        app.update_idletasks()
        result = CombinedExcelResult(
            path=None,
            assembly_count=1,
            feature_row_count=2,
            complexity_row_count=1,
            errors=[],
            role_row_count=1,
        )

        try:
            with mock.patch(
                "zijinhua_tekla.gui.report_gui.messagebox.showinfo"
            ) as show_info:
                app._messages.put({"kind": "success", "result": result})
                app._poll_messages()

            show_info.assert_called_once()
            self.assertIn("构件角色 1 行", show_info.call_args.args[1])
        finally:
            app.destroy()

    def test_old_axis_cache_shows_a_reexport_warning(self):
        app = ReportGUI()
        result = CombinedExcelResult(None, 1, 2, 1, role_row_count=1, axis_review_count=1)
        try:
            with mock.patch("zijinhua_tekla.gui.report_gui.messagebox.showinfo"), mock.patch(
                "zijinhua_tekla.gui.report_gui.messagebox.showwarning"
            ) as warning:
                app._messages.put({"kind": "success", "result": result})
                app._poll_messages()
            warning.assert_called_once()
            self.assertIn("重新导出", warning.call_args.args[0])
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
