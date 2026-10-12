"""Build the Qt6 single-file Windows application with the accepted Tekla runner."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
RUNNER_FILES = ("TeklaSectionClassifier.Runner.exe", "TeklaSectionClassifier.Runner.exe.config",
                "TeklaSectionClassifier.dll")


def build_environment():
    """Do not resolve Qt DLLs from unrelated tools in the caller's PATH."""
    environment = os.environ.copy()
    python_dir = Path(sys.executable).resolve().parent
    windows = Path(environment.get("SystemRoot", r"C:\Windows"))
    environment["PATH"] = os.pathsep.join(map(str, (python_dir, windows / "System32", windows)))
    return environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner-dir", type=Path, required=True)
    args = parser.parse_args()
    for name in RUNNER_FILES:
        if not (args.runner_dir / name).is_file():
            parser.error(f"Missing runner dependency: {args.runner_dir / name}")
    output = ROOT / "dist" / "ZijinhuaTekla"
    output.mkdir(parents=True, exist_ok=True)
    work = ROOT / "build" / "qt6-desktop"
    work.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
               "--name", "ZijinhuaTekla", "--paths", str(ROOT / "src"),
               "--distpath", str(output), "--workpath", str(work / "work"), "--specpath", str(work),
               "--exclude-module", "tkinter", "--exclude-module", "PyQt5", "--exclude-module", "PyQt6",
               "--exclude-module", "PySide2"]
    # Pandas hooks discover optional packages installed on the build machine.
    # Recognition uses none of these plotting/ML/notebook dependencies.
    for module in ("torch", "tensorflow", "scipy", "matplotlib", "IPython", "jupyter",
                   "numba", "sympy", "sklearn", "cv2", "bokeh", "plotly", "pyarrow", "tables"):
        command.extend(["--exclude-module", module])
    for name in RUNNER_FILES:
        command.extend(["--add-data", f"{(args.runner_dir / name).resolve()};tekla_runner"])
    command.append(str(ROOT / "scripts" / "desktop_entry.py"))
    subprocess.run(command, cwd=ROOT, env=build_environment(), check=True)
    exe = output / "ZijinhuaTekla.exe"
    # This must run the frozen application, not Python from the build environment.
    startup_report = work / "startup-verification.json"
    if startup_report.exists():
        startup_report.unlink()
    subprocess.run([str(exe), "--verify-startup", str(startup_report)], cwd=output,
                   env=build_environment(), check=True, timeout=90)
    startup = json.loads(startup_report.read_text(encoding="utf-8"))
    if not startup.get("window_visible") or startup.get("qt_platform") != "windows":
        raise RuntimeError(f"Packaged Qt window verification failed: {startup}")
    manifest = {"file": exe.name, "bytes": exe.stat().st_size,
                "sha256": hashlib.sha256(exe.read_bytes()).hexdigest(), "startup_verified": startup,
                "runner_files": {name: hashlib.sha256((args.runner_dir / name).read_bytes()).hexdigest()
                                 for name in RUNNER_FILES}}
    (output / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    shutil.copyfile(ROOT / "docs" / "desktop-user-guide.md", output / "使用说明.md")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
