from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time
import unittest
from unittest import mock

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from zijinhua_tekla.gui.jobs import Job, dataset_root, execute_job
from zijinhua_tekla.gui.report_gui import ReportGUI
from zijinhua_tekla.reports.combined import BUNDLE_FILENAME, CombinedExcelResult
from zijinhua_tekla.tekla_export import TeklaSelectionExportResult


APP = QApplication.instance() or QApplication([])


class ReportGuiTests(unittest.TestCase):
    def setUp(self):
        self.app = ReportGUI()
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root / BUNDLE_FILENAME).write_text('{"assemblies": []}', encoding="utf-8")
        self.app.source.setText(str(self.root))
        self.app.output.setText(str(self.root / "out"))
        self.app.project.setText("项目")
        self.app.area.setText("区域")
        self.app.active_kind = "offline"

    def tearDown(self):
        if self.app.worker:
            self.app.worker.wait(5000)
            APP.processEvents()
        self.app.close()
        self.temp.cleanup()

    def wait_job(self):
        deadline = time.monotonic() + 8
        while self.app.worker is not None and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertIsNone(self.app.worker)

    def test_empty_output_is_rejected_before_worker_starts(self):
        self.app.output.clear()
        with mock.patch("zijinhua_tekla.gui.report_gui.QMessageBox.warning") as warning:
            self.app._start_generate()
        self.assertIsNone(self.app.worker)
        self.assertIn("结果存放目录", warning.call_args.args[2])

    def test_error_is_logged_displayed_and_buttons_recover(self):
        with mock.patch("zijinhua_tekla.gui.jobs.export_combined_excel", side_effect=PermissionError("文件无法写入")), mock.patch(
            "zijinhua_tekla.gui.report_gui.QMessageBox.critical"
        ) as error:
            self.app._start_generate()
            self.wait_job()
        self.assertTrue(self.app.tabs.isEnabled())
        self.assertIn("文件无法写入", error.call_args.args[2])
        log = Path(self.app.current_log).read_text(encoding="utf-8")
        self.assertIn("Traceback", log)
        self.assertIn("PermissionError", log)
        self.assertEqual(0, self.app.progress.value())

    def test_background_job_locks_inputs_and_forwards_paths(self):
        release = threading.Event()
        result = CombinedExcelResult(self.root / "out.xlsx", 1, 2, 1, role_row_count=1)

        def run(*args, progress):
            progress(1, 1, "已处理构件")
            release.wait(5)
            return result

        with mock.patch("zijinhua_tekla.gui.jobs.export_combined_excel", side_effect=run) as export, mock.patch(
            "zijinhua_tekla.gui.report_gui.QMessageBox.information"
        ) as popup:
            try:
                self.app._start_generate()
                original = self.app.worker
                self.app._start_generate()
                self.assertIs(original, self.app.worker)
                self.assertFalse(self.app.tabs.isEnabled())
                QTest.qWait(30)
            finally:
                release.set()
            self.wait_job()
        self.assertEqual((self.root, "项目", "区域", str(self.root / "out")), export.call_args.args)
        self.assertIn("已处理构件", self.app.log_view.toPlainText())
        self.assertIn("构件角色 1 行", popup.call_args.args[2])
        self.assertEqual(100, self.app.progress.value())

    def test_tekla_result_fills_offline_source(self):
        runner = self.root / "runner.exe"
        runner.touch()
        self.app.custom_runner.setChecked(True)
        self.app.runner_path.setText(str(runner))
        self.app.tekla_output.setText(str(self.root / "exports"))

        def export(runner_path, target, log):
            log("导出日志")
            return TeklaSelectionExportResult(target, target / BUNDLE_FILENAME, 3)

        with mock.patch("zijinhua_tekla.gui.jobs.run_tekla_selection_export", side_effect=export), mock.patch(
            "zijinhua_tekla.gui.report_gui.QMessageBox.information"
        ):
            self.app._start_export()
            self.wait_job()
        self.assertEqual(1, self.app.tabs.currentIndex())
        self.assertEqual(self.root / "exports", Path(self.app.source.text()).parent)
        self.assertIn("导出日志", Path(self.app.current_log).read_text(encoding="utf-8"))

    def test_bundle_file_is_normalized_but_member_file_is_rejected(self):
        self.assertEqual(self.root, dataset_root(str(self.root / BUNDLE_FILENAME)))
        member = self.root / "member_1.json"
        member.write_text("{}")
        with self.assertRaises(ValueError):
            dataset_root(str(member))

    def test_each_export_uses_a_new_directory(self):
        runner = self.root / "runner.exe"
        runner.touch()
        targets = []

        def export(runner_path, target, log):
            targets.append(target)
            return TeklaSelectionExportResult(target, target / BUNDLE_FILENAME, 1)

        with mock.patch("zijinhua_tekla.gui.jobs.run_tekla_selection_export", side_effect=export):
            for _ in range(2):
                execute_job(Job("tekla", str(self.root), runner=str(runner)), lambda _: None,
                            lambda *_: None, lambda _: None)
        self.assertNotEqual(*targets)
        self.assertTrue(all(path.is_dir() for path in targets))


if __name__ == "__main__":
    unittest.main()
