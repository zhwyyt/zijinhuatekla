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
        )

        try:
            with mock.patch(
                "zijinhua_tekla.gui.report_gui.messagebox.showinfo"
            ) as show_info:
                app._messages.put({"kind": "success", "result": result})
                app._poll_messages()

            show_info.assert_called_once()
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
