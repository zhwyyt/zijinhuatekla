"""Run the local Tekla selection exporter and validate its output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Callable

from .reports.combined import inspect_export_root


DEFAULT_RUNNER_PATH = Path(
    r"I:\xingcaisuanfa\TeklaSectionClassifier.Runner"
    r"\bin\Debug\net48\TeklaSectionClassifier.Runner.exe"
)


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
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> TeklaSelectionExportResult:
    output = Path(output_directory).expanduser()
    command = build_tekla_export_command(runner_path, output)
    output.mkdir(parents=True, exist_ok=True)

    try:
        completed = runner(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
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
    return TeklaSelectionExportResult(
        output_directory=output,
        bundle_path=Path(info["bundle_path"]),
        member_count=int(info["member_count"]),
    )
