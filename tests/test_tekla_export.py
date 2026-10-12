import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from zijinhua_tekla.reports.combined import BUNDLE_FILENAME
from zijinhua_tekla.tekla_export import (
    build_tekla_export_command,
    run_tekla_selection_export,
    _stream_runner,
)


def fake_runner(
    command,
    check,
    capture_output,
    text,
    encoding,
    errors,
    timeout,
):
    assert check is True
    assert capture_output is True
    output = Path(command[2])
    output.mkdir(parents=True, exist_ok=True)
    (output / BUNDLE_FILENAME).write_text(
        json.dumps({"assemblies": [{"assemblyId": "A"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (output / "members").mkdir(exist_ok=True)
    (output / "members" / "member_1.json").write_text("{}", encoding="utf-8")
    return subprocess.CompletedProcess(command, 0, "完成", "")


class TeklaExportTests(unittest.TestCase):
    def test_streams_child_output_and_reports_nonzero_exit(self):
        lines = []
        with self.assertRaises(subprocess.CalledProcessError) as error:
            _stream_runner([sys.executable, "-u", "-c", "print('progress', flush=True); raise SystemExit(7)"],
                           check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=5, log=lines.append)
        self.assertEqual(["progress"], lines)
        self.assertEqual(7, error.exception.returncode)

    def test_silent_child_timeout_is_enforced(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            _stream_runner([sys.executable, "-c", "import time; time.sleep(5)"],
                           check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=0.2)

    def test_empty_selection_is_not_success(self):
        with TemporaryDirectory() as temp:
            runner = Path(temp) / "runner.exe"
            runner.touch()

            def empty(*args, **kwargs):
                result = fake_runner(*args, **kwargs)
                (Path(args[0][2]) / BUNDLE_FILENAME).write_text('{"assemblies": []}')
                return result

            with self.assertRaisesRegex(RuntimeError, "未导出任何构件"):
                run_tekla_selection_export(runner, Path(temp) / "out", runner=empty)

    def test_builds_output_argument(self):
        with TemporaryDirectory() as temp:
            runner = Path(temp) / "runner.exe"
            runner.write_text("", encoding="utf-8")
            output = Path(temp) / "export"

            command = build_tekla_export_command(runner, output)

            self.assertEqual([str(runner), "--output", str(output)], command)

    def test_missing_runner_is_rejected(self):
        with TemporaryDirectory() as temp:
            runner = Path(temp) / "missing.exe"

            with self.assertRaises(FileNotFoundError):
                build_tekla_export_command(runner, Path(temp) / "export")

    def test_empty_output_is_rejected(self):
        with TemporaryDirectory() as temp:
            runner = Path(temp) / "runner.exe"
            runner.write_text("", encoding="utf-8")

            with self.assertRaises(ValueError):
                build_tekla_export_command(runner, "   ")

    def test_validates_selection_export_result(self):
        with TemporaryDirectory() as temp:
            runner = Path(temp) / "runner.exe"
            runner.write_text("", encoding="utf-8")
            output = Path(temp) / "export"

            result = run_tekla_selection_export(
                runner,
                output,
                timeout_seconds=5,
                runner=fake_runner,
            )

            self.assertEqual(output, result.output_directory)
            self.assertEqual(1, result.member_count)


if __name__ == "__main__":
    unittest.main()
