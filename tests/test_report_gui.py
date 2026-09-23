import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from zijinhua_tekla.gui.report_gui import ReportGUI


class ReportGuiTests(unittest.TestCase):
    def test_error_message_is_logged_and_shown(self):
        app = ReportGUI()
        app.update_idletasks()
        with TemporaryDirectory() as temp:
            log_path = Path(temp) / "gui-errors.log"
            error = {
                "kind": "error",
                "message": "测试失败原因",
                "trace": "traceback",
                "source": "offline",
            }

            with mock.patch(
                "zijinhua_tekla.gui.report_gui.ERROR_LOG_PATH",
                log_path,
            ), mock.patch(
                "zijinhua_tekla.gui.report_gui.messagebox.showerror"
            ) as show_error:
                app._messages.put(error)
                app._poll_messages()

            self.assertIn("测试失败原因", log_path.read_text(encoding="utf-8"))
            show_error.assert_called_once()

        app.destroy()


if __name__ == "__main__":
    unittest.main()
