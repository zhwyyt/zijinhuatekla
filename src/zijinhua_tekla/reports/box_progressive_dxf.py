from __future__ import annotations

from typing import Any


def build_box_assembly_drawing_steps_dxf(payload: dict[str, Any]) -> str:
    member_id = str(payload.get("member_id") or "")
    steps = [step for step in payload.get("steps", []) if isinstance(step, dict)]
    writer = _DxfWriter()
    writer.start()
    writer.text(0, 0, 4.0, f"{member_id} BOX progressive drawing steps", "TITLE")

    for index, step in enumerate(steps):
        y = -20.0 - index * 85.0
        _draw_step(writer, step, y)

    writer.finish()
    return writer.content()


def _draw_step(writer: "_DxfWriter", step: dict[str, Any], y: float) -> None:
    step_no = step.get("step_no", "")
    step_type = str(step.get("step_type") or "")
    title = str(step.get("title") or "")
    station_range = str(step.get("station_range") or "")
    mark_targets = [target for target in step.get("part_mark_targets", []) if isinstance(target, dict)]
    dimension_targets = [target for target in step.get("dimension_targets", []) if isinstance(target, dict)]

    writer.rectangle(0, y, 260, y - 70, "SHEET")
    writer.text(5, y - 8, 3.0, f"Step {step_no} {step_type} {title}", "TITLE")
    writer.text(5, y - 15, 2.4, f"station {station_range}", "DIM")

    writer.line(12, y - 25, 210, y - 25, "AXIS")
    writer.line(12, y - 22, 12, y - 28, "AXIS")
    writer.line(210, y - 22, 210, y - 28, "AXIS")
    writer.text(12, y - 32, 2.0, "member_start", "DIM")
    writer.text(180, y - 32, 2.0, "member_end", "DIM")

    if dimension_targets:
        dimension_text = "dimensions: " + "; ".join(str(target.get("kind") or "") for target in dimension_targets)
        writer.text(5, y - 39, 2.0, dimension_text, "DIM")

    x = 8.0
    block_y = y - 52.0
    for target in mark_targets:
        label = " / ".join(
            value
            for value in [
                str(target.get("part_position") or ""),
                str(target.get("profile") or ""),
                str(target.get("name") or ""),
            ]
            if value
        )
        width = min(58.0, max(28.0, len(label) * 1.6))
        writer.rectangle(x, block_y + 8, x + width, block_y - 8, "NEW_PART")
        writer.text(x + 2, block_y + 1.5, 1.8, label, "PART_MARK")
        x += width + 5.0
        if x > 220:
            x = 8.0
            block_y -= 16.0


class _DxfWriter:
    def __init__(self) -> None:
        self._lines: list[str] = []

    def start(self) -> None:
        self._lines.extend(
            [
                "0",
                "SECTION",
                "2",
                "HEADER",
                "0",
                "ENDSEC",
                "0",
                "SECTION",
                "2",
                "ENTITIES",
            ]
        )

    def finish(self) -> None:
        self._lines.extend(["0", "ENDSEC", "0", "EOF"])

    def content(self) -> str:
        return "\n".join(self._lines) + "\n"

    def line(self, x1: float, y1: float, x2: float, y2: float, layer: str) -> None:
        self._lines.extend(
            [
                "0",
                "LINE",
                "8",
                layer,
                "10",
                _num(x1),
                "20",
                _num(y1),
                "11",
                _num(x2),
                "21",
                _num(y2),
            ]
        )

    def rectangle(self, x1: float, y1: float, x2: float, y2: float, layer: str) -> None:
        self.line(x1, y1, x2, y1, layer)
        self.line(x2, y1, x2, y2, layer)
        self.line(x2, y2, x1, y2, layer)
        self.line(x1, y2, x1, y1, layer)

    def text(self, x: float, y: float, height: float, value: str, layer: str) -> None:
        self._lines.extend(
            [
                "0",
                "TEXT",
                "8",
                layer,
                "10",
                _num(x),
                "20",
                _num(y),
                "40",
                _num(height),
                "1",
                _clean_text(value),
            ]
        )


def _num(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _clean_text(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ").strip()
