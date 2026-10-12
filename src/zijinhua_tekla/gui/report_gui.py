"""Qt6 desktop for Tekla selection export and offline recognition."""

from __future__ import annotations

from pathlib import Path
import sys
import traceback

from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from ..reports.combined import BUNDLE_FILENAME
from ..tekla_export import default_runner_path
from .jobs import Job, execute_job, fallback_log_directory, validate_job


class JobThread(QThread):
    log_line = Signal(str)
    log_path = Signal(str)
    progress = Signal(int, int)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, job: Job, parent=None):
        super().__init__(parent)
        self.job = job

    def run(self):
        try:
            result = execute_job(self.job, self.log_line.emit, self.progress.emit, self.log_path.emit)
            self.succeeded.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class ReportGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("紫金花 · Tekla 构件识别")
        self.resize(960, 760)
        self.setMinimumSize(820, 680)
        self.worker = None
        self.active_kind = ""
        self.current_log = ""
        self.result_directory = ""
        self.pending_result = None
        self.pending_error = None
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        title = QLabel("Tekla 构件识别")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)
        layout.addWidget(QLabel("构件角色 · 构件复杂度 · 零件特征"))
        self.tabs = QTabWidget()
        self.tabs.setObjectName("modules")
        layout.addWidget(self.tabs)
        self._build_export_tab()
        self._build_offline_tab()
        self.status = QLabel("就绪：请选择模块并填写输入、输出位置。")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setObjectName("runLog")
        self.log_view.setMaximumBlockCount(5000)
        self.log_view.setMinimumHeight(170)
        log_layout.addWidget(self.log_view)
        self.log_label = QLabel("任务开始后，完整日志保存在所选结果目录的 logs 文件夹。")
        self.log_label.setWordWrap(True)
        log_layout.addWidget(self.log_label)
        buttons = QHBoxLayout()
        self.open_result = QPushButton("打开结果文件夹")
        self.open_result.setEnabled(False)
        self.open_result.clicked.connect(lambda: self._open_path(self.result_directory))
        self.open_log = QPushButton("打开日志")
        self.open_log.setEnabled(False)
        self.open_log.clicked.connect(lambda: self._open_path(self.current_log))
        buttons.addWidget(self.open_result)
        buttons.addWidget(self.open_log)
        buttons.addStretch()
        log_layout.addLayout(buttons)
        layout.addWidget(log_group, 1)

    def _path_row(self, name, *, file=False, bundle=False):
        edit = QLineEdit()
        edit.setObjectName(name)
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(edit, 1)
        button = QPushButton("选择程序" if file else "选择文件夹")
        button.clicked.connect(lambda: self._browse(edit, file=file))
        layout.addWidget(button)
        if bundle:
            pick = QPushButton("选择 bundle 文件")
            pick.clicked.connect(lambda: self._browse(edit, bundle=True))
            layout.addWidget(pick)
        return edit, row

    def _build_export_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        hint = QLabel("1. 在 Tekla 2017 中打开模型并选中要导出的构件或零件。\n"
                      "2. 选择存放目录，点击开始导出。每次自动新建独立数据集文件夹。")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        form = QFormLayout()
        self.tekla_output, row = self._path_row("teklaOutput")
        form.addRow("数据集存放目录", row)
        layout.addLayout(form)
        advanced = QGroupBox("高级：使用自定义导出程序")
        advanced.setCheckable(True)
        advanced.setChecked(False)
        advanced_layout = QFormLayout(advanced)
        self.runner_path, row = self._path_row("runnerPath", file=True)
        self.runner_path.setText(str(default_runner_path()))
        advanced_layout.addRow("导出程序", row)
        self.custom_runner = advanced
        layout.addWidget(advanced)
        layout.addStretch()
        self.export_button = QPushButton("开始导出")
        self.export_button.setObjectName("startExport")
        self.export_button.clicked.connect(self._start_export)
        layout.addWidget(self.export_button)
        self.tabs.addTab(tab, "模块 1 · Tekla 模型导出")

    def _build_offline_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        hint = QLabel("选择包含 bundle 和 members 的完整数据集，生成构件角色、构件复杂度及零件特征 Excel。")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        form = QFormLayout()
        self.source, row = self._path_row("datasetSource", bundle=True)
        form.addRow("输入数据集", row)
        self.project = QLineEdit()
        self.project.setObjectName("projectName")
        self.project.setPlaceholderText("用于结果文件名，例如：徐汇T3")
        form.addRow("项目名称", self.project)
        self.area = QLineEdit()
        self.area.setObjectName("projectArea")
        self.area.setPlaceholderText("例如：当前选择集")
        form.addRow("工程区域", self.area)
        self.output, row = self._path_row("reportOutput")
        form.addRow("结果存放目录", row)
        layout.addLayout(form)
        layout.addWidget(QLabel("结果命名：项目名称_工程区域.xlsx；同名文件自动保留并另存。"))
        layout.addStretch()
        self.generate_button = QPushButton("开始运算并生成结果")
        self.generate_button.setObjectName("startRecognition")
        self.generate_button.clicked.connect(self._start_generate)
        layout.addWidget(self.generate_button)
        self.tabs.addTab(tab, "模块 2 · 数据集识别")

    def _browse(self, edit, *, file=False, bundle=False):
        if file or bundle:
            selected, _ = QFileDialog.getOpenFileName(
                self, "选择导出程序" if file else "选择 Tekla 数据集",
                edit.text(), "可执行程序 (*.exe)" if file else f"Tekla 数据集 ({BUNDLE_FILENAME})",
            )
        else:
            selected = QFileDialog.getExistingDirectory(self, "选择存放或输入文件夹", edit.text())
        if selected:
            edit.setText(selected)

    def _start_export(self):
        runner = self.runner_path.text().strip() if self.custom_runner.isChecked() else str(default_runner_path())
        self.start_job(Job("tekla", self.tekla_output.text().strip(), runner=runner))

    def _start_generate(self):
        self.start_job(Job("offline", self.output.text().strip(), source=self.source.text().strip(),
                           project=self.project.text().strip(), area=self.area.text().strip()))

    def start_job(self, job):
        if self.worker is not None:
            return
        try:
            validate_job(job)
        except Exception as exc:
            self.status.setText(f"输入错误：{exc}")
            self.log_view.appendPlainText(f"[输入错误] {exc}")
            QMessageBox.warning(self, "请检查输入", str(exc))
            return
        self.active_kind = job.kind
        self.current_log = ""
        self.pending_result = None
        self.pending_error = None
        self.result_directory = str(Path(job.output).expanduser().resolve())
        self.tabs.setEnabled(False)
        self.open_result.setEnabled(False)
        self.open_log.setEnabled(False)
        self.log_view.clear()
        self.progress.setRange(0, 0)
        self.status.setText("正在导出 Tekla 选择集…" if job.kind == "tekla" else "正在读取数据集并识别…")
        self.worker = JobThread(job, self)
        self.worker.log_line.connect(self.log_view.appendPlainText)
        self.worker.log_path.connect(self._set_log_path)
        self.worker.progress.connect(self._set_progress)
        self.worker.succeeded.connect(self._receive_result)
        self.worker.failed.connect(self._receive_error)
        self.worker.finished.connect(self._finish_job)
        self.worker.start()

    def _set_log_path(self, path):
        self.current_log = path
        self.log_label.setText(f"完整日志：{path}")
        self.open_log.setEnabled(True)

    def _set_progress(self, current, total):
        self.progress.setRange(0, total if total else 0)
        self.progress.setValue(current)
        if total:
            self.status.setText(f"正在识别：已处理 {current}/{total} 个构件；请等待结果保存完成。")

    def _receive_result(self, result):
        self.pending_result = result

    def _receive_error(self, error):
        self.pending_error = error

    def _finish_job(self):
        worker = self.worker
        self.worker = None
        if worker:
            worker.deleteLater()
        self.tabs.setEnabled(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0 if self.pending_error else 100)
        self.open_result.setEnabled(Path(self.result_directory).is_dir())
        if self.pending_error:
            self.status.setText(f"任务失败：{self.pending_error}")
            QMessageBox.critical(self, "任务失败", f"{self.pending_error}\n\n详细日志：{self.current_log or '未能创建日志，请检查目录权限。'}")
        elif self.pending_result is not None:
            self._show_success(self.pending_result)

    def _show_success(self, result):
        if self.active_kind == "tekla":
            self.source.setText(str(result.output_directory))
            self.result_directory = str(result.output_directory)
            self.tabs.setCurrentIndex(1)
            self.status.setText(f"导出完成：{result.member_count} 个构件，数据源已填入模块 2。")
            QMessageBox.information(self, "Tekla 导出完成", f"已导出 {result.member_count} 个构件。\n{result.output_directory}\n可在模块 2 指定结果目录后开始运算。")
            return
        summary = (f"构件角色 {result.role_row_count} 行，构件复杂度 {result.complexity_row_count} 行，"
                   f"零件特征 {result.feature_row_count} 行。\n"
                   f"失败 {result.error_count} 个；主轴复核 {result.axis_review_count} 个；"
                   f"连接复核 {result.connection_review_count} 条。\n输出：{result.path}")
        self.status.setText(f"{'完成，存在复核项' if result.error_count or result.axis_review_count else '完成'}：{result.path}")
        if result.error_count or result.axis_review_count:
            detail = "\n请查看识别失败表和日志。" if result.error_count else ""
            if result.axis_review_count:
                detail += "\n存在主轴来源或几何需复核的构件；旧缓存请使用当前导出器重新导出。"
            QMessageBox.warning(self, "结果已生成，请复核", summary + detail)
        else:
            QMessageBox.information(self, "结果生成完成", summary)

    def _open_path(self, path):
        if path and not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            QMessageBox.warning(self, "无法打开", f"请手动打开：{path}")

    def closeEvent(self, event):
        if self.worker is not None:
            QMessageBox.warning(self, "任务仍在运行", "请等待任务完成后关闭窗口，避免中断数据导出或结果保存。")
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("ZijinhuaTekla")
    app.setOrganizationName("Zijinhua")
    app.setStyle("Fusion")
    app.setStyleSheet("QWidget { font-family: 'Microsoft YaHei UI'; font-size: 13px; }"
                     "QLineEdit, QPushButton { min-height: 28px; }"
                     "QTabWidget::pane { border: 1px solid #ccd4dc; }"
                     "QGroupBox { margin-top: 12px; padding-top: 12px; }"
                     "QGroupBox::title { subcontrol-origin: margin; left: 8px; }")

    def report_unhandled(exc_type, value, tb):
        detail = "".join(traceback.format_exception(exc_type, value, tb))
        try:
            log_dir = fallback_log_directory()
            log_dir.mkdir(parents=True, exist_ok=True)
            path = log_dir / "application-errors.log"
            with path.open("a", encoding="utf-8") as handle:
                handle.write(detail + "\n")
            message = f"{value}\n详细日志：{path}"
        except OSError:
            message = detail
        QMessageBox.critical(None, "程序错误", message)

    sys.excepthook = report_unhandled
    window = ReportGUI()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
