"""Tkinter GUI for the combined Tekla export Excel."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
import queue
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..reports.combined import BUNDLE_FILENAME, export_combined_excel, inspect_export_root
from ..tekla_export import DEFAULT_RUNNER_PATH, run_tekla_selection_export


ERROR_LOG_PATH = Path("outputs/gui-errors.log")


class ReportGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Tekla 选择集导出与识别")
        self.geometry("780x470")
        self.minsize(700, 420)

        self.export_root = tk.StringVar()
        self.tekla_output_dir = tk.StringVar()
        self.runner_path = tk.StringVar(value=str(DEFAULT_RUNNER_PATH))
        self.output_dir = tk.StringVar()
        self.project_name = tk.StringVar()
        self.project_area = tk.StringVar()
        self.source_status = tk.StringVar(value="请选择包含 bundle.json 的导出根目录")
        self.export_status = tk.StringVar(value="请选择 Tekla 导出输出文件夹")
        self.run_status = tk.StringVar(value="等待生成")

        self._messages: queue.Queue[dict[str, object]] = queue.Queue()
        self._worker: threading.Thread | None = None

        self._build_notebook()
        self._build_status_group()
        self.after(100, self._poll_messages)

    def _build_notebook(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(16, 8))

        tekla_tab = ttk.Frame(self.notebook)
        offline_tab = ttk.Frame(self.notebook)
        self.notebook.add(tekla_tab, text="模式1：Tekla 在线导出")
        self.notebook.add(offline_tab, text="模式2：已导出文件分析")
        self._build_tekla_group(tekla_tab)
        self._build_source_group(offline_tab)
        self._build_output_group(offline_tab)

    def _build_tekla_group(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        group = ttk.LabelFrame(parent, text="导出 Tekla 当前选择集")
        group.pack(fill="both", expand=True, padx=8, pady=8)
        group.columnconfigure(1, weight=1)

        ttk.Label(group, text="输出文件夹").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
        ttk.Entry(group, textvariable=self.tekla_output_dir).grid(
            row=0, column=1, sticky="ew", padx=6, pady=(12, 6)
        )
        ttk.Button(group, text="选择文件夹", command=self._choose_tekla_output_dir).grid(
            row=0, column=2, sticky="e", padx=12, pady=(12, 6)
        )

        ttk.Label(group, text="导出程序").grid(row=1, column=0, sticky="w", padx=12, pady=6)
        ttk.Entry(group, textvariable=self.runner_path).grid(row=1, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(group, text="选择程序", command=self._choose_runner).grid(
            row=1, column=2, sticky="e", padx=12, pady=6
        )

        ttk.Label(
            group,
            text="前提：Tekla 已打开模型，且构件集/构件已选中。导出包含 bundle 和 members。",
        ).grid(row=2, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 6))

        self.tekla_export_button = ttk.Button(
            group,
            text="开始导出",
            command=self._start_tekla_export,
        )
        self.tekla_export_button.grid(row=3, column=2, sticky="e", padx=12, pady=(8, 12))
        ttk.Label(group, textvariable=self.export_status).grid(
            row=4, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 12)
        )

    def _build_source_group(self, parent: ttk.Frame) -> None:
        group = ttk.LabelFrame(parent, text="1. 选择已导出的 Tekla 文件")
        group.pack(fill="x", padx=8, pady=8)
        group.columnconfigure(1, weight=1)

        ttk.Label(group, text="导出根目录").grid(
            row=0,
            column=0,
            sticky="w",
            padx=12,
            pady=12,
        )
        root_entry = ttk.Entry(group, textvariable=self.export_root)
        root_entry.grid(row=0, column=1, sticky="ew", padx=6, pady=12)
        folder_button = ttk.Button(
            group,
            text="选择文件夹",
            command=self._choose_export_root,
        )
        folder_button.grid(row=0, column=2, padx=6, pady=12)
        file_button = ttk.Button(
            group,
            text="选择 bundle 文件",
            command=self._choose_bundle_file,
        )
        file_button.grid(row=0, column=3, padx=(0, 12), pady=12)
        ttk.Label(group, textvariable=self.source_status).grid(
            row=1,
            column=0,
            columnspan=4,
            sticky="ew",
            padx=12,
            pady=(0, 12),
        )

    def _build_output_group(self, parent: ttk.Frame) -> None:
        group = ttk.LabelFrame(parent, text="2. 分析导出文件并生成 Excel")
        group.pack(fill="both", expand=True, padx=8, pady=8)
        group.columnconfigure(1, weight=1)

        ttk.Label(group, text="项目名称").grid(
            row=0,
            column=0,
            sticky="w",
            padx=12,
            pady=(12, 6),
        )
        ttk.Entry(group, textvariable=self.project_name).grid(
            row=0,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=12,
            pady=(12, 6),
        )
        ttk.Label(group, text="工程区域").grid(
            row=1,
            column=0,
            sticky="w",
            padx=12,
            pady=6,
        )
        ttk.Entry(group, textvariable=self.project_area).grid(
            row=1,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=12,
            pady=6,
        )
        ttk.Label(group, text="输出目录").grid(
            row=2,
            column=0,
            sticky="w",
            padx=12,
            pady=6,
        )
        ttk.Entry(group, textvariable=self.output_dir).grid(
            row=2,
            column=1,
            columnspan=2,
            sticky="ew",
            padx=12,
            pady=6,
        )
        ttk.Button(
            group,
            text="选择输出目录",
            command=self._choose_output_dir,
        ).grid(row=2, column=3, sticky="e", padx=12, pady=6)
        ttk.Label(
            group,
            text="输出文件名：项目名称_工程区域.xlsx；已存在时自动加时间戳。",
        ).grid(row=3, column=1, columnspan=3, sticky="w", padx=12)

        self.generate_button = ttk.Button(
            group,
            text="生成 Excel",
            command=self._start_generate,
        )
        self.generate_button.grid(row=4, column=3, sticky="e", padx=12, pady=(8, 12))

    def _build_status_group(self) -> None:
        group = ttk.LabelFrame(self, text="执行状态")
        group.pack(fill="x", padx=16, pady=(8, 16))
        group.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(group, mode="indeterminate")
        self.progress.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        ttk.Label(group, textvariable=self.run_status).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=12,
            pady=(0, 12),
        )

    def _choose_export_root(self) -> None:
        selected = filedialog.askdirectory(title="选择 Tekla 导出根目录")
        if selected:
            self.export_root.set(selected)
            self._maybe_set_default_output(selected)
            self._refresh_source()

    def _choose_tekla_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="选择 Tekla 选择集导出文件夹")
        if selected:
            self.tekla_output_dir.set(selected)

    def _choose_runner(self) -> None:
        selected = filedialog.askopenfilename(
            title="选择 TeklaSectionClassifier.Runner.exe",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")],
        )
        if selected:
            self.runner_path.set(selected)

    def _choose_bundle_file(self) -> None:
        selected = filedialog.askopenfilename(
            title=f"选择 {BUNDLE_FILENAME}",
            filetypes=[("Tekla 导出包", BUNDLE_FILENAME), ("JSON", "*.json")],
        )
        if selected:
            root = str(Path(selected).parent)
            self.export_root.set(root)
            self._maybe_set_default_output(root)
            self._refresh_source()

    def _choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="选择 Excel 输出目录")
        if selected:
            self.output_dir.set(selected)

    def _maybe_set_default_output(self, export_root: str) -> None:
        if not self.output_dir.get().strip():
            self.output_dir.set(export_root)

    def _start_tekla_export(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        output_dir = self.tekla_output_dir.get().strip()
        if not output_dir:
            messagebox.showerror("输入错误", "请先选择 Tekla 导出输出文件夹。", parent=self)
            return

        arguments = (self.runner_path.get(), output_dir)
        self.tekla_export_button.config(state="disabled")
        self.progress.start(12)
        self.export_status.set("正在从打开的 Tekla 模型导出当前选择集...")
        self._worker = threading.Thread(
            target=self._export_tekla_selection,
            args=arguments,
            daemon=True,
        )
        self._worker.start()

    def _export_tekla_selection(self, runner_path: str, output_dir: str) -> None:
        try:
            result = run_tekla_selection_export(runner_path, output_dir)
            self._messages.put({"kind": "tekla-success", "result": result})
        except Exception as exc:
            self._messages.put(
                {
                    "kind": "error",
                    "message": str(exc),
                    "trace": traceback.format_exc(),
                    "source": "tekla",
                }
            )

    def _refresh_source(self) -> None:
        info = inspect_export_root(self.export_root.get())
        if info["valid"]:
            self.source_status.set(
                f"导出信息有效；bundle 已找到，构件文件 {info['member_count']} 个"
            )
        elif info["bundle_found"]:
            self.source_status.set("bundle 已找到，但未找到 members/member_*.json")
        else:
            self.source_status.set(f"无效：未找到 {BUNDLE_FILENAME}")

    def _start_generate(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        try:
            export_root = str(Path(self.export_root.get()).expanduser())
            output_dir = self.output_dir.get().strip()
            if not output_dir:
                output_dir = export_root
            arguments = (
                export_root,
                self.project_name.get(),
                self.project_area.get(),
                str(Path(output_dir).expanduser()),
            )
        except Exception as exc:
            messagebox.showerror("输入错误", str(exc), parent=self)
            return

        self.generate_button.config(state="disabled")
        self.progress.start(12)
        self.run_status.set("正在读取 Tekla 导出并识别，请等待...")
        self._worker = threading.Thread(
            target=self._generate,
            args=arguments,
            daemon=True,
        )
        self._worker.start()

    def _generate(
        self,
        export_root: str,
        project_name: str,
        project_area: str,
        output_dir: str,
    ) -> None:
        try:
            result = export_combined_excel(
                export_root,
                project_name,
                project_area,
                output_dir,
            )
            self._messages.put({"kind": "success", "result": result})
        except Exception as exc:
            self._messages.put(
                {
                    "kind": "error",
                    "message": str(exc),
                    "trace": traceback.format_exc(),
                    "source": "offline",
                }
            )

    def _log_error(self, message: dict[str, object]) -> None:
        try:
            ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            title = "Tekla export" if message.get("source") == "tekla" else "Excel generation"
            with ERROR_LOG_PATH.open("a", encoding="utf-8") as log_file:
                log_file.write(
                    f"\n[{timestamp}] {title}\n"
                    f"{message.get('message')}\n"
                    f"{message.get('trace')}\n"
                )
        except Exception:
            pass

    def _poll_messages(self) -> None:
        try:
            message = self._messages.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_messages)
            return

        source = message.get("source")
        if message.get("kind") == "tekla-success":
            result = message["result"]
            self.tekla_output_dir.set(str(result.output_directory))
            self.export_root.set(str(result.output_directory))
            self._maybe_set_default_output(str(result.output_directory))
            self._refresh_source()
            self.export_status.set(
                f"导出完成：构件 {result.member_count} 个；输出 {result.output_directory}"
            )
            messagebox.showinfo(
                "Tekla 导出完成",
                f"已导出 {result.member_count} 个构件。\n可切换到模式2生成 Excel。",
                parent=self,
            )
        elif message.get("kind") == "success":
            result = message["result"]
            self.run_status.set(
                f"已完成：{result.complexity_row_count} 构件 / "
                f"{result.feature_row_count} 零件 / 错误 {result.error_count}；"
                f"输出 {result.path}"
            )
            messagebox.showinfo(
                "Excel 生成完成",
                f"构件 {result.complexity_row_count} 个，零件 {result.feature_row_count} 行。\n"
                f"输出：{result.path}",
                parent=self,
            )
            if result.error_count:
                messagebox.showwarning(
                    "部分构件失败",
                    f"Excel 已生成，但有 {result.error_count} 个构件失败。",
                    parent=self,
                )
        else:
            is_export_error = message.get("source") == "tekla"
            title = "Tekla 导出失败" if is_export_error else "Excel 生成失败"
            prefix = "导出失败" if is_export_error else "生成失败"
            self._log_error(message)
            self.run_status.set(
                f"{prefix}：{message.get('message')}\n详细日志：{ERROR_LOG_PATH}"
            )
            messagebox.showerror(
                title,
                str(message.get("message")),
                parent=self,
            )

        if source == "offline":
            self.generate_button.config(state="normal")
        elif source == "tekla":
            self.tekla_export_button.config(state="normal")
        else:
            self.tekla_export_button.config(state="normal")
            self.generate_button.config(state="normal")
        self.after(100, self._poll_messages)


def main() -> None:
    ReportGUI().mainloop()


if __name__ == "__main__":
    main()
