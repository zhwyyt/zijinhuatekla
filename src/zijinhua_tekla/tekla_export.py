"""Run the local Tekla selection exporter and validate its output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections import deque
import json
import os
import queue
import subprocess
import sys
import threading
import time
from typing import Callable

from .reports.combined import inspect_export_root


DEFAULT_RUNNER_PATH = Path(
    r"I:\xingcaisuanfa\TeklaSectionClassifier.Runner"
    r"\bin\Debug\net48\TeklaSectionClassifier.Runner.exe"
)


def default_runner_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "tekla_runner" / "TeklaSectionClassifier.Runner.exe"
    return DEFAULT_RUNNER_PATH


@dataclass(frozen=True)
class TeklaSelectionExportResult:
    output_directory: Path
    bundle_path: Path
    member_count: int


def build_tekla_export_command(
    runner_path: Path | str,
    output_directory: Path | str,
) -> list[str]:
    runner = Path(runner_path).expanduser()
    if not str(output_directory).strip():
        raise ValueError("输出目录不能为空")
    output = Path(output_directory).expanduser()
    if not runner.is_file():
        raise FileNotFoundError(f"Tekla 导出程序不存在: {runner}")
    if not str(output).strip():
        raise ValueError("输出目录不能为空")
    return [str(runner), "--output", str(output)]


def run_tekla_selection_export(
    runner_path: Path | str,
    output_directory: Path | str,
    timeout_seconds: float | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    log: Callable[[str], None] | None = None,
) -> TeklaSelectionExportResult:
    command = build_tekla_export_command(runner_path, output_directory)
    output = Path(output_directory).expanduser()
    output.mkdir(parents=True, exist_ok=True)

    try:
        completed = (runner or _stream_runner)(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="mbcs" if os.name == "nt" else "utf-8",
            errors="replace",
            timeout=timeout_seconds,
            **({"log": log} if runner is None else {}),
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"Tekla 导出失败（退出码 {exc.returncode}）：{detail}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Tekla 导出超时（{timeout_seconds} 秒）") from exc

    info = inspect_export_root(output)
    if not info["valid"]:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"Tekla 导出完成，但导出结果无效：{detail}")
    bundle = json.loads(Path(info["bundle_path"]).read_text(encoding="utf-8-sig"))
    assemblies = bundle.get("assemblies") or []
    if not assemblies:
        raise RuntimeError("未导出任何构件。请在已打开的 Tekla 模型中选中构件或零件后重试。")
    return TeklaSelectionExportResult(
        output_directory=output,
        bundle_path=Path(info["bundle_path"]),
        member_count=len(assemblies),
    )


def _stream_runner(command, *, check, capture_output, text, encoding, errors, timeout, log=None):
    """Drain merged output continuously; keep a bounded error tail and support timeouts."""
    # Frozen Python adds its DLL directory; a separate .NET process must use its own.
    reset_dll_directory = os.name == "nt" and getattr(sys, "frozen", False)
    if reset_dll_directory:
        import ctypes
        ctypes.windll.kernel32.SetDllDirectoryW(None)
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, text=True, encoding=encoding, errors=errors,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    finally:
        if reset_dll_directory:
            ctypes.windll.kernel32.SetDllDirectoryW(sys._MEIPASS)
    messages: queue.Queue[str | None] = queue.Queue()

    def read_output():
        try:
            for line in process.stdout:
                messages.put(line.rstrip())
        finally:
            messages.put(None)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    tail: deque[str] = deque(maxlen=80)
    started = time.monotonic()
    try:
        while True:
            if timeout is not None and time.monotonic() - started > timeout:
                raise subprocess.TimeoutExpired(command, timeout)
            try:
                line = messages.get(timeout=0.1)
            except queue.Empty:
                continue
            if line is None:
                break
            tail.append(line)
            if log:
                log(line)
        remaining = None if timeout is None else max(0.01, timeout - (time.monotonic() - started))
        code = process.wait(timeout=remaining)
        output = "\n".join(tail)
        if code and check:
            raise subprocess.CalledProcessError(code, command, output=output)
        return subprocess.CompletedProcess(command, code, output, "")
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        reader.join(timeout=2)
        process.stdout.close()
