import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from zijinhua_tekla.reports.combined import BUNDLE_FILENAME
from zijinhua_tekla.tekla_export import (
    build_tekla_export_command,
    run_tekla_selection_export,
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
        json.dumps({"assemblies": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    (output / "members").mkdir(exist_ok=True)
    (output / "members" / "member_1.json").write_text("{}", encoding="utf-8")
    return subprocess.CompletedProcess(command, 0, "完成", "")


class TeklaExportTests(unittest.TestCase):
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
