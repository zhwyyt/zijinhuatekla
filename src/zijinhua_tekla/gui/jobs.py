"""Desktop jobs and durable logs, independent of Qt widgets."""

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import traceback
from uuid import uuid4

from ..reports.combined import BUNDLE_FILENAME, export_combined_excel
from ..tekla_export import run_tekla_selection_export


@dataclass(frozen=True)
class Job:
    kind: str
    output: str
    source: str = ""
    runner: str = ""
    project: str = ""
    area: str = ""


def dataset_root(value: str) -> Path:
    if not value.strip():
        raise ValueError("请选择 Tekla 导出的数据集目录或 bundle 文件。")
    path = Path(value.strip()).expanduser().resolve()
    if path.is_file():
        if path.name != BUNDLE_FILENAME:
            raise ValueError(f"请选择 {BUNDLE_FILENAME}，不能单独选择 member 文件。")
        path = path.parent
    if not (path / BUNDLE_FILENAME).is_file():
        raise FileNotFoundError(f"数据集中未找到 {BUNDLE_FILENAME}：{path}")
    return path


def validate_job(job: Job) -> None:
    if not job.output.strip():
        raise ValueError("请选择结果存放目录。")
    output = Path(job.output).expanduser()
    if output.exists() and not output.is_dir():
        raise ValueError("结果存放位置必须是文件夹。")
    if job.kind == "tekla":
        if not Path(job.runner).is_file():
            raise FileNotFoundError("未找到 Tekla 导出程序，请重新解压完整程序或选择有效的导出程序。")
    elif job.kind == "offline":
        dataset_root(job.source)
        if not job.project.strip() or not job.area.strip():
            raise ValueError("请填写项目名称和工程区域，用于命名结果文件。")
    else:
        raise ValueError("未知任务类型")


def fallback_log_directory() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ZijinhuaTekla" / "logs"


def execute_job(job: Job, emit_log, emit_progress, emit_log_path):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    try:
        log_dir = Path(job.output).expanduser().resolve() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        handle = (log_dir / f"{job.kind}_{stamp}.log").open("w", encoding="utf-8")
    except OSError:
        log_dir = fallback_log_directory()
        log_dir.mkdir(parents=True, exist_ok=True)
        handle = (log_dir / f"{job.kind}_{stamp}.log").open("w", encoding="utf-8")
    emit_log_path(str(Path(handle.name).resolve()))
    with handle:
        def log(message):
            line = f"[{datetime.now():%H:%M:%S}] {message}"
            handle.write(line + "\n")
            handle.flush()
            emit_log(line)

        try:
            validate_job(job)
            log("开始 Tekla 选择集导出" if job.kind == "tekla" else "开始构件角色、复杂度及零件特征识别")
            log(f"结果目录：{Path(job.output).resolve()}")
            if job.kind == "tekla":
                target = Path(job.output).expanduser().resolve() / f"Tekla_{stamp}_{uuid4().hex[:6]}"
                target.mkdir(parents=True, exist_ok=False)
                log(f"请保持 Tekla 模型和当前选择集不变；数据集：{target}")
                emit_progress(0, 0)
                result = run_tekla_selection_export(job.runner, target, log=log)
                log(f"导出完成：{result.member_count} 个构件；{result.output_directory}")
            else:
                source = dataset_root(job.source)
                log(f"输入数据集：{source}")

                def progress(current, total, message):
                    emit_progress(current, total)
                    log(message)

                result = export_combined_excel(source, job.project, job.area, job.output, progress=progress)
                log(f"保存完成：{result.path}")
                log(f"构件角色 {result.role_row_count} 行；构件复杂度 {result.complexity_row_count} 行；"
                    f"零件特征 {result.feature_row_count} 行；失败 {result.error_count} 个；主轴复核 {result.axis_review_count} 个")
                if result.error_count:
                    log("[警告] 部分构件失败，请查看 Excel 的识别失败表。")
                if result.axis_review_count:
                    log("[警告] 存在主轴需复核构件，请检查主轴来源或缺失几何；旧缓存需要重新导出。")
            return result
        except Exception:
            log("[错误] 任务失败\n" + traceback.format_exc())
            raise
