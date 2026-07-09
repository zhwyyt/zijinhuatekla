# Process Drawing Annotation Layout Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable annotation intent and layout layer for BOX process drawings, then route the Tekla U-stage clean drawing through it without Tekla native dimension artifacts.

**Architecture:** Add a pure Python annotation/layout core for deterministic tests and DXF reuse. Add a small matching DTO/layout adapter inside the Tekla 2017 POC so the live Tekla smoke can consume the same contract shape. Renderers consume pre-placed line/text items and report layout status/collisions in JSON evidence.

**Tech Stack:** Python 3 dataclasses/unittest, existing `ezdxf` DXF writer path, C# .NET Framework 4.8 Tekla Open API POC, Tekla Structures 2017 Drawing API.

---

## File Structure

- Create: `I:\zijinhuatekla\src\zijinhua_tekla\reports\annotation_layout.py`
  - Pure dataclasses and deterministic functions for `ProjectionScene`, `AnnotationIntent`, `AnnotationLayout`, collision checks, and U-stage intent/layout generation.
- Create: `I:\zijinhuatekla\tests\test_process_drawing_annotation_layout.py`
  - Unit tests for U-stage intents, collision-free first layout, dense PartMark overflow/detail request, and layout JSON shape.
- Modify: `I:\zijinhuatekla\src\zijinhua_tekla\reports\box_progressive_dxf.py`
  - Add a narrow renderer helper that draws `AnnotationLayout` line/text items into the existing DXF writer.
- Modify: `I:\zijinhuatekla\tests\test_box_progressive_dxf.py`
  - Add one regression asserting DXF output can include layout-driven annotations.
- Modify: `I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\Program.cs`
  - Replace U-stage ad hoc text/dimension insertion with a POC-local annotation layout DTO and renderer.
- Modify: `I:\zijinhuatekla\docs\verification\2026-07-07-tekla-openapi-existing-drawing-inspection.md`
  - Append Tekla clean smoke evidence showing `StraightDimensions=0` and layout status.
- Modify: `I:\zijinhuatekla\TASKLIST.md`
  - Mark the annotation/layout implementation task complete only after all verification commands pass.

## Task 1: Add Pure Annotation Layout Core

**Files:**
- Create: `I:\zijinhuatekla\src\zijinhua_tekla\reports\annotation_layout.py`
- Create: `I:\zijinhuatekla\tests\test_process_drawing_annotation_layout.py`

- [ ] **Step 1: Write the failing U-stage annotation tests**

Create `I:\zijinhuatekla\tests\test_process_drawing_annotation_layout.py` with this content:

```python
import unittest

from zijinhua_tekla.reports.annotation_layout import (
    AnnotationKind,
    LayoutStatus,
    PartAnchor,
    ProjectionScene,
    Rect,
    build_u_stage_annotation_intents,
    layout_annotation_intents,
    layout_to_jsonable,
)


class ProcessDrawingAnnotationLayoutTests(unittest.TestCase):
    def _u_stage_scene(self) -> ProjectionScene:
        return ProjectionScene(
            view_id="main",
            drawing_bounds=Rect(0.0, 0.0, 599.0, 420.0),
            main_view_bounds=Rect(35.0, 80.0, 535.0, 165.6),
            model_length=3505.0,
            model_width=600.0,
            model_thickness=30.0,
            source_part_id="28705233",
            source_part_position="10-3Z-128",
            source_profile="BOX600*600*30*30",
            source_name="GKZ60-2",
            fixture_face="MODEL_AXIS_2_HEIGHT_1_MIN_ON_FIXTURE",
            anchors={
                "source_part": PartAnchor(
                    part_id="28705233",
                    x=285.0,
                    y=122.8,
                    label="10-3Z-128 / BOX600*600*30*30 / GKZ60-2",
                )
            },
        )

    def test_builds_u_stage_annotation_intents(self):
        scene = self._u_stage_scene()
        intents = build_u_stage_annotation_intents(scene)
        by_kind = {intent.kind for intent in intents}
        self.assertIn(AnnotationKind.OVERALL_DIMENSION, by_kind)
        self.assertIn(AnnotationKind.SECTION_DIMENSION, by_kind)
        self.assertIn(AnnotationKind.THICKNESS_CALLOUT, by_kind)
        self.assertIn(AnnotationKind.PART_MARK, by_kind)
        self.assertIn(AnnotationKind.FIXTURE_NOTE, by_kind)
        self.assertIn(AnnotationKind.STAGE_NOTE, by_kind)
        self.assertIn("3505", [intent.text for intent in intents])
        self.assertIn("600", [intent.text for intent in intents])
        self.assertIn("t=30", [intent.text for intent in intents])
        self.assertTrue(any("10-3Z-128" in intent.text for intent in intents))
        self.assertTrue(any("虚拟U形组立" in intent.text for intent in intents))

    def test_layout_u_stage_annotations_without_collisions(self):
        scene = self._u_stage_scene()
        layout = layout_annotation_intents(scene, build_u_stage_annotation_intents(scene))
        self.assertEqual(LayoutStatus.OK, layout.status)
        self.assertEqual(0, layout.collision_count)
        self.assertFalse(layout.unplaced_items)
        self.assertGreaterEqual(len(layout.lines), 10)
        self.assertGreaterEqual(len(layout.texts), 6)
        for text in layout.texts:
            self.assertFalse(text.box.intersects(scene.main_view_bounds), text.text)

    def test_dense_part_marks_request_detail_view_instead_of_overlapping(self):
        scene = self._u_stage_scene()
        intents = build_u_stage_annotation_intents(scene)
        part_mark = [item for item in intents if item.kind == AnnotationKind.PART_MARK][0]
        for index in range(12):
            intents.append(part_mark.copy_with(id=f"part-mark-extra-{index}", text=f"10-3Z-X{index:02d} / PL10*90 / 连接板", priority=50 - index))
        layout = layout_annotation_intents(scene, intents)
        self.assertEqual(LayoutStatus.NEEDS_DETAIL_VIEW, layout.status)
        self.assertGreater(len(layout.unplaced_items), 0)

    def test_layout_serializes_to_jsonable_contract(self):
        scene = self._u_stage_scene()
        layout = layout_annotation_intents(scene, build_u_stage_annotation_intents(scene))
        data = layout_to_jsonable(layout)
        self.assertEqual("OK", data["layout_status"])
        self.assertEqual(0, data["collision_count"])
        self.assertTrue(any(item["kind"] == "TEXT" for item in data["placed_items"]))
        self.assertTrue(any(item["kind"] == "LINE" for item in data["placed_items"]))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests and verify they fail because the module does not exist**

Run:

```powershell
python -m unittest tests.test_process_drawing_annotation_layout
```

Expected output includes:

```text
ModuleNotFoundError: No module named 'zijinhua_tekla.reports.annotation_layout'
```

- [ ] **Step 3: Implement the pure annotation/layout module**

Create `I:\zijinhuatekla\src\zijinhua_tekla\reports\annotation_layout.py` with this content:

```python
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Iterable


class AnnotationKind(str, Enum):
    OVERALL_DIMENSION = "OVERALL_DIMENSION"
    SECTION_DIMENSION = "SECTION_DIMENSION"
    THICKNESS_CALLOUT = "THICKNESS_CALLOUT"
    PART_MARK = "PART_MARK"
    FIXTURE_NOTE = "FIXTURE_NOTE"
    STAGE_NOTE = "STAGE_NOTE"
    WARNING = "WARNING"


class LayoutStatus(str, Enum):
    OK = "OK"
    OVERFLOW = "OVERFLOW"
    NEEDS_DETAIL_VIEW = "NEEDS_DETAIL_VIEW"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class Rect:
    left: float
    bottom: float
    right: float
    top: float

    @property
    def center_x(self) -> float:
        return (self.left + self.right) / 2.0

    @property
    def center_y(self) -> float:
        return (self.bottom + self.top) / 2.0

    def expanded(self, padding: float) -> "Rect":
        return Rect(self.left - padding, self.bottom - padding, self.right + padding, self.top + padding)

    def intersects(self, other: "Rect") -> bool:
        return not (self.right <= other.left or self.left >= other.right or self.top <= other.bottom or self.bottom >= other.top)

    def to_list(self) -> list[float]:
        return [self.left, self.bottom, self.right, self.top]


@dataclass(frozen=True)
class PartAnchor:
    part_id: str
    x: float
    y: float
    label: str


@dataclass(frozen=True)
class ProjectionScene:
    view_id: str
    drawing_bounds: Rect
    main_view_bounds: Rect
    model_length: float
    model_width: float
    model_thickness: float
    source_part_id: str
    source_part_position: str
    source_profile: str
    source_name: str
    fixture_face: str
    anchors: dict[str, PartAnchor]


@dataclass(frozen=True)
class AnnotationIntent:
    id: str
    kind: AnnotationKind
    text: str
    priority: int
    target_anchor: str
    source_part_ids: tuple[str, ...] = ()
    model_value: float = 0.0
    evidence_codes: tuple[str, ...] = ()
    allow_merge: bool = False
    fallback_policy: str = "REVIEW_REQUIRED"

    def copy_with(self, **changes: Any) -> "AnnotationIntent":
        return replace(self, **changes)


@dataclass(frozen=True)
class LayoutLine:
    kind: str
    x1: float
    y1: float
    x2: float
    y2: float
    source_intent_id: str

    def to_jsonable(self) -> dict[str, Any]:
        return {"kind": "LINE", "line_kind": self.kind, "x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2, "source_intent_id": self.source_intent_id}


@dataclass(frozen=True)
class LayoutText:
    kind: str
    text: str
    x: float
    y: float
    box: Rect
    source_intent_id: str

    def to_jsonable(self) -> dict[str, Any]:
        return {"kind": "TEXT", "text_kind": self.kind, "text": self.text, "x": self.x, "y": self.y, "box": self.box.to_list(), "source_intent_id": self.source_intent_id}


@dataclass(frozen=True)
class AnnotationLayout:
    status: LayoutStatus
    lines: tuple[LayoutLine, ...]
    texts: tuple[LayoutText, ...]
    unplaced_items: tuple[AnnotationIntent, ...]
    collision_count: int
    debug_boxes: tuple[Rect, ...]


def build_u_stage_annotation_intents(scene: ProjectionScene) -> list[AnnotationIntent]:
    part_label = " / ".join(value for value in [scene.source_part_position, scene.source_profile, scene.source_name] if value)
    return [
        AnnotationIntent("stage-title", AnnotationKind.STAGE_NOTE, "阶段1：底板 + 两侧板，盖板未装", 120, "sheet.title_zone", (scene.source_part_id,), evidence_codes=("PROCESS_STAGE",)),
        AnnotationIntent("overall-length", AnnotationKind.OVERALL_DIMENSION, _dimension_text(scene.model_length), 110, "main_view.length", (scene.source_part_id,), scene.model_length, ("TEKLA_SOLID_EXTENT",)),
        AnnotationIntent("section-width", AnnotationKind.SECTION_DIMENSION, _dimension_text(scene.model_width), 105, "main_view.width", (scene.source_part_id,), scene.model_width, ("TEKLA_SOLID_EXTENT",)),
        AnnotationIntent("wall-thickness", AnnotationKind.THICKNESS_CALLOUT, "t=" + _dimension_text(scene.model_thickness), 100, "main_view.wall_thickness", (scene.source_part_id,), scene.model_thickness, ("BOX_PROFILE_THICKNESS",)),
        AnnotationIntent("source-part-mark", AnnotationKind.PART_MARK, part_label, 95, "source_part", (scene.source_part_id,), evidence_codes=("TEKLA_PART_POSITION", "TEKLA_PROFILE"), allow_merge=True, fallback_policy="NEEDS_DETAIL_VIEW"),
        AnnotationIntent("fixture-face-note", AnnotationKind.FIXTURE_NOTE, "胎架面：" + scene.fixture_face, 90, "sheet.note_zone", (scene.source_part_id,), evidence_codes=("FIXTURE_FRAME",)),
        AnnotationIntent("virtual-box-warning", AnnotationKind.WARNING, "BOX profile virtual U-stage / 虚拟U形组立", 85, "sheet.note_zone", (scene.source_part_id,), evidence_codes=("VIRTUAL_DECOMPOSED_BOX_PROFILE",)),
    ]


def layout_annotation_intents(scene: ProjectionScene, intents: Iterable[AnnotationIntent]) -> AnnotationLayout:
    ordered = sorted(intents, key=lambda item: item.priority, reverse=True)
    lines: list[LayoutLine] = []
    texts: list[LayoutText] = []
    occupied = [scene.main_view_bounds.expanded(2.0)]
    unplaced: list[AnnotationIntent] = []
    part_mark_count = 0
    for intent in ordered:
        if intent.kind == AnnotationKind.OVERALL_DIMENSION:
            _place_length_dimension(scene, intent, lines, texts, occupied)
        elif intent.kind == AnnotationKind.SECTION_DIMENSION:
            _place_width_dimension(scene, intent, lines, texts, occupied)
        elif intent.kind == AnnotationKind.THICKNESS_CALLOUT:
            _place_thickness_callout(scene, intent, lines, texts, occupied)
        elif intent.kind == AnnotationKind.PART_MARK:
            part_mark_count += 1
            if part_mark_count > 4 or not _place_part_mark(scene, intent, lines, texts, occupied):
                unplaced.append(intent)
        elif intent.kind == AnnotationKind.STAGE_NOTE:
            _place_or_unplace(intent, scene.drawing_bounds.left + 28.0, scene.drawing_bounds.top - 26.0, texts, occupied, unplaced)
        elif intent.kind == AnnotationKind.FIXTURE_NOTE:
            _place_or_unplace(intent, scene.drawing_bounds.left + 28.0, scene.drawing_bounds.top - 46.0, texts, occupied, unplaced)
        elif intent.kind == AnnotationKind.WARNING:
            _place_or_unplace(intent, scene.drawing_bounds.left + 28.0, scene.drawing_bounds.top - 66.0, texts, occupied, unplaced)
        else:
            unplaced.append(intent)
    collision_count = _count_text_collisions(tuple(texts), scene.main_view_bounds)
    status = LayoutStatus.NEEDS_DETAIL_VIEW if unplaced else LayoutStatus.OK
    if collision_count > 0 and status == LayoutStatus.OK:
        status = LayoutStatus.REVIEW_REQUIRED
    return AnnotationLayout(status, tuple(lines), tuple(texts), tuple(unplaced), collision_count, tuple(text.box for text in texts))


def layout_to_jsonable(layout: AnnotationLayout) -> dict[str, Any]:
    return {
        "layout_status": layout.status.value,
        "collision_count": layout.collision_count,
        "placed_items": [item.to_jsonable() for item in [*layout.lines, *layout.texts]],
        "unplaced_items": [{"id": item.id, "kind": item.kind.value, "text": item.text, "fallback_policy": item.fallback_policy} for item in layout.unplaced_items],
        "debug_boxes": [box.to_list() for box in layout.debug_boxes],
    }
```

Then append these helper functions in the same file:

```python
def _place_length_dimension(scene, intent, lines, texts, occupied):
    view = scene.main_view_bounds
    y = view.top + 18.0
    tick = 4.0
    lines.extend([
        LayoutLine("DIMENSION_EXTENSION", view.left, view.top + 2.0, view.left, y + 2.0, intent.id),
        LayoutLine("DIMENSION_EXTENSION", view.right, view.top + 2.0, view.right, y + 2.0, intent.id),
        LayoutLine("DIMENSION", view.left, y, view.right, y, intent.id),
        LayoutLine("DIMENSION_TICK", view.left - tick, y - tick, view.left + tick, y + tick, intent.id),
        LayoutLine("DIMENSION_TICK", view.right - tick, y - tick, view.right + tick, y + tick, intent.id),
    ])
    _place_text(intent, view.center_x - 12.0, y + 5.0, texts, occupied)


def _place_width_dimension(scene, intent, lines, texts, occupied):
    view = scene.main_view_bounds
    x = view.right + 18.0
    tick = 4.0
    lines.extend([
        LayoutLine("DIMENSION_EXTENSION", view.right + 2.0, view.bottom, x + 2.0, view.bottom, intent.id),
        LayoutLine("DIMENSION_EXTENSION", view.right + 2.0, view.top, x + 2.0, view.top, intent.id),
        LayoutLine("DIMENSION", x, view.bottom, x, view.top, intent.id),
        LayoutLine("DIMENSION_TICK", x - tick, view.bottom - tick, x + tick, view.bottom + tick, intent.id),
        LayoutLine("DIMENSION_TICK", x - tick, view.top - tick, x + tick, view.top + tick, intent.id),
    ])
    _place_text(intent, x + 5.0, view.center_y, texts, occupied)


def _place_thickness_callout(scene, intent, lines, texts, occupied):
    view = scene.main_view_bounds
    x = view.left + 30.0
    y = view.bottom - 18.0
    lines.append(LayoutLine("LEADER", view.left + 25.0, view.bottom + 4.0, x, y + 3.0, intent.id))
    _place_text(intent, x + 4.0, y, texts, occupied)


def _place_part_mark(scene, intent, lines, texts, occupied):
    anchor = scene.anchors.get(intent.target_anchor)
    if anchor is None:
        return False
    for x, y in [(scene.main_view_bounds.right + 42.0, anchor.y + 18.0), (scene.main_view_bounds.left - 130.0, anchor.y + 18.0), (scene.main_view_bounds.right + 42.0, anchor.y - 18.0)]:
        if _place_text(intent, x, y, texts, occupied):
            lines.append(LayoutLine("LEADER", anchor.x, anchor.y, x - 2.0, y + 2.0, intent.id))
            return True
    return False


def _place_or_unplace(intent, x, y, texts, occupied, unplaced):
    if not _place_text(intent, x, y, texts, occupied):
        unplaced.append(intent)


def _place_text(intent, x, y, texts, occupied):
    box = _text_box(x, y, intent.text)
    if any(box.intersects(item) for item in occupied):
        return False
    texts.append(LayoutText(intent.kind.value, intent.text, x, y, box, intent.id))
    occupied.append(box.expanded(1.0))
    return True


def _text_box(x, y, text):
    return Rect(x, y - 1.5, x + max(14.0, len(text) * 2.6), y + 6.0)


def _count_text_collisions(texts, main_view_bounds):
    count = 0
    for index, text in enumerate(texts):
        if text.box.intersects(main_view_bounds):
            count += 1
        for other in texts[index + 1:]:
            if text.box.intersects(other.box):
                count += 1
    return count


def _dimension_text(value):
    return str(int(round(value)))
```

- [ ] **Step 4: Run the pure layout tests and verify they pass**

Run:

```powershell
python -m unittest tests.test_process_drawing_annotation_layout
```

Expected output includes:

```text
Ran 4 tests
OK
```

- [ ] **Step 5: Commit Task 1 changes**

Run:

```powershell
git add src/zijinhua_tekla/reports/annotation_layout.py tests/test_process_drawing_annotation_layout.py
git commit -m "Add process drawing annotation layout core"
```

Expected: commit succeeds with only the two files staged. If unrelated dirty files exist, stage only these two files.

## Task 2: Add DXF Renderer Adapter for AnnotationLayout

**Files:**
- Modify: `I:\zijinhuatekla\src\zijinhua_tekla\reports\box_progressive_dxf.py`
- Modify: `I:\zijinhuatekla\tests\test_box_progressive_dxf.py`

- [ ] **Step 1: Add a failing DXF regression for layout-driven annotation text**

Append this test method to `BoxProgressiveDxfTests` in `I:\zijinhuatekla\tests\test_box_progressive_dxf.py`:

```python
    def test_can_render_annotation_layout_items_into_dxf(self):
        from zijinhua_tekla.reports.annotation_layout import AnnotationKind, AnnotationIntent, AnnotationLayout, LayoutLine, LayoutStatus, LayoutText, Rect
        from zijinhua_tekla.reports.box_progressive_dxf import _DxfWriter, _draw_annotation_layout
        intent = AnnotationIntent("overall-length", AnnotationKind.OVERALL_DIMENSION, "3505", 100, "main_view.length")
        layout = AnnotationLayout(
            status=LayoutStatus.OK,
            lines=(LayoutLine("DIMENSION", 10.0, 20.0, 100.0, 20.0, intent.id),),
            texts=(LayoutText("OVERALL_DIMENSION", "3505", 50.0, 25.0, Rect(50.0, 23.5, 64.0, 31.0), intent.id),),
            unplaced_items=(),
            collision_count=0,
            debug_boxes=(),
        )
        writer = _DxfWriter()
        writer.start()
        _draw_annotation_layout(writer, layout)
        writer.finish()
        dxf = writer.content()
        self.assertIn("Z-DIMENSIONS", dxf)
        self.assertIn("3505", dxf)
        self.assertIn("AcDbLine", dxf)
        self.assertIn("AcDbText", dxf)
```

- [ ] **Step 2: Run the focused DXF test and verify it fails because `_draw_annotation_layout` is missing**

Run:

```powershell
python -m unittest tests.test_box_progressive_dxf.BoxProgressiveDxfTests.test_can_render_annotation_layout_items_into_dxf
```

Expected output includes:

```text
ImportError: cannot import name '_draw_annotation_layout'
```

- [ ] **Step 3: Implement `_draw_annotation_layout` in the DXF renderer**

In `I:\zijinhuatekla\src\zijinhua_tekla\reports\box_progressive_dxf.py`, add this import near the existing imports:

```python
from zijinhua_tekla.reports.annotation_layout import AnnotationLayout
```

Add this function near the other drawing helpers, before `_draw_step`:

```python
def _draw_annotation_layout(writer: "_DxfWriter", layout: AnnotationLayout) -> None:
    for line in layout.lines:
        layer = "Z-DIMENSIONS" if "DIMENSION" in line.kind else "PartMark"
        writer.line(line.x1, line.y1, line.x2, line.y2, layer=layer)
    for text in layout.texts:
        layer = "Z-DIMENSIONS" if "DIMENSION" in text.kind else "PartMark"
        if text.kind in {"STAGE_NOTE", "FIXTURE_NOTE", "WARNING"}:
            layer = "Text"
        writer.text(text.x, text.y, text.text, height=2.6, layer=layer)
```

- [ ] **Step 4: Run focused and full DXF tests**

Run:

```powershell
python -m unittest tests.test_box_progressive_dxf.BoxProgressiveDxfTests.test_can_render_annotation_layout_items_into_dxf
python -m unittest tests.test_box_progressive_dxf
```

Expected output for each command includes:

```text
OK
```

- [ ] **Step 5: Commit Task 2 changes**

Run:

```powershell
git add src/zijinhua_tekla/reports/box_progressive_dxf.py tests/test_box_progressive_dxf.py
git commit -m "Render annotation layout items in DXF"
```

## Task 3: Route Tekla U-Stage POC Through a Layout DTO

**Files:**
- Modify: `I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\Program.cs`

- [ ] **Step 1: Build current POC before editing**

Run:

```powershell
dotnet build I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\BoxProgressiveDrawingPoc.csproj
```

Expected output includes:

```text
已成功生成。
0 个错误
```

- [ ] **Step 2: Add POC-local layout DTO classes**

In `Program.cs`, add these classes near `StageDrawResult`:

```csharp
    internal sealed class DrawingAnnotationLayout
    {
        public string LayoutStatus { get; set; }
        public int CollisionCount { get; set; }
        public List<DrawingAnnotationLine> Lines { get; set; }
        public List<DrawingAnnotationText> Texts { get; set; }
        public List<string> UnplacedItems { get; set; }

        public DrawingAnnotationLayout()
        {
            LayoutStatus = "OK";
            Lines = new List<DrawingAnnotationLine>();
            Texts = new List<DrawingAnnotationText>();
            UnplacedItems = new List<string>();
        }
    }

    internal sealed class DrawingAnnotationLine
    {
        public string Kind { get; set; }
        public double X1 { get; set; }
        public double Y1 { get; set; }
        public double X2 { get; set; }
        public double Y2 { get; set; }
        public string SourceIntentId { get; set; }
    }

    internal sealed class DrawingAnnotationText
    {
        public string Kind { get; set; }
        public string Text { get; set; }
        public double X { get; set; }
        public double Y { get; set; }
        public double Left { get; set; }
        public double Bottom { get; set; }
        public double Right { get; set; }
        public double Top { get; set; }
        public string SourceIntentId { get; set; }
    }
```

- [ ] **Step 3: Add U-stage layout builder, renderer, and helpers**

In `Program.cs`, add this code near `InsertManualOverallDimensions`:

```csharp
        private static DrawingAnnotationLayout BuildFixtureUStageAnnotationLayout(StageDrawResult result, FixtureFrame frame, string sourcePartLabel)
        {
            var layout = new DrawingAnnotationLayout();
            if (result.Rectangles == 0)
            {
                layout.LayoutStatus = "REVIEW_REQUIRED";
                layout.UnplacedItems.Add("main_view_geometry");
                return layout;
            }

            var minX = result.MinX;
            var maxX = result.MaxX;
            var minY = result.MinY;
            var maxY = result.MaxY;
            var tick = 4.0;
            var lengthY = maxY + 18.0;
            var widthX = maxX + 18.0;
            AddLayoutText(layout, "STAGE_NOTE", "阶段1：底板 + 两侧板，盖板未装", 30.0, 205.0, "stage-title");
            AddLayoutText(layout, "FIXTURE_NOTE", "胎架面：" + (frame == null ? "<none>" : frame.FixtureFace), 30.0, 195.0, "fixture-face-note");
            AddLayoutText(layout, "WARNING", "BOX profile virtual U-stage / 虚拟U形组立", 30.0, 185.0, "virtual-box-warning");
            AddLayoutLine(layout, "DIMENSION_EXTENSION", minX, maxY + 2.0, minX, lengthY + 2.0, "overall-length");
            AddLayoutLine(layout, "DIMENSION_EXTENSION", maxX, maxY + 2.0, maxX, lengthY + 2.0, "overall-length");
            AddLayoutLine(layout, "DIMENSION", minX, lengthY, maxX, lengthY, "overall-length");
            AddLayoutLine(layout, "DIMENSION_TICK", minX - tick, lengthY - tick, minX + tick, lengthY + tick, "overall-length");
            AddLayoutLine(layout, "DIMENSION_TICK", maxX - tick, lengthY - tick, maxX + tick, lengthY + tick, "overall-length");
            AddLayoutText(layout, "OVERALL_DIMENSION", DimensionText(result.ModelLength), (minX + maxX) / 2.0 - 12.0, lengthY + 5.0, "overall-length");
            AddLayoutLine(layout, "DIMENSION_EXTENSION", maxX + 2.0, minY, widthX + 2.0, minY, "section-width");
            AddLayoutLine(layout, "DIMENSION_EXTENSION", maxX + 2.0, maxY, widthX + 2.0, maxY, "section-width");
            AddLayoutLine(layout, "DIMENSION", widthX, minY, widthX, maxY, "section-width");
            AddLayoutLine(layout, "DIMENSION_TICK", widthX - tick, minY - tick, widthX + tick, minY + tick, "section-width");
            AddLayoutLine(layout, "DIMENSION_TICK", widthX - tick, maxY - tick, widthX + tick, maxY + tick, "section-width");
            AddLayoutText(layout, "SECTION_DIMENSION", DimensionText(result.ModelWidth), widthX + 5.0, (minY + maxY) / 2.0, "section-width");
            AddLayoutLine(layout, "LEADER", minX + 25.0, minY + 4.0, minX + 30.0, minY - 15.0, "wall-thickness");
            AddLayoutText(layout, "THICKNESS_CALLOUT", "t=" + DimensionText(result.ModelThickness), minX + 34.0, minY - 18.0, "wall-thickness");
            AddLayoutLine(layout, "LEADER", (minX + maxX) / 2.0, (minY + maxY) / 2.0, maxX + 42.0, maxY + 26.0, "source-part-mark");
            AddLayoutText(layout, "PART_MARK", sourcePartLabel, maxX + 44.0, maxY + 24.0, "source-part-mark");
            layout.CollisionCount = CountLayoutTextCollisions(layout.Texts);
            if (layout.CollisionCount > 0)
            {
                layout.LayoutStatus = "REVIEW_REQUIRED";
            }
            return layout;
        }

        private static int RenderAnnotationLayout(ContainerView sheet, DrawingAnnotationLayout layout, StageDrawResult result)
        {
            var textInserted = 0;
            foreach (var line in layout.Lines)
            {
                InsertLine(sheet, line.X1, line.Y1, line.X2, line.Y2, result);
            }
            foreach (var text in layout.Texts)
            {
                textInserted += InsertText(sheet, text.X, text.Y, text.Text);
            }
            return textInserted;
        }

        private static void AddLayoutLine(DrawingAnnotationLayout layout, string kind, double x1, double y1, double x2, double y2, string sourceIntentId)
        {
            layout.Lines.Add(new DrawingAnnotationLine { Kind = kind, X1 = x1, Y1 = y1, X2 = x2, Y2 = y2, SourceIntentId = sourceIntentId });
        }

        private static void AddLayoutText(DrawingAnnotationLayout layout, string kind, string text, double x, double y, string sourceIntentId)
        {
            var width = Math.Max(14.0, (text ?? "").Length * 2.6);
            layout.Texts.Add(new DrawingAnnotationText { Kind = kind, Text = text ?? "", X = x, Y = y, Left = x, Bottom = y - 1.5, Right = x + width, Top = y + 6.0, SourceIntentId = sourceIntentId });
        }

        private static int CountLayoutTextCollisions(List<DrawingAnnotationText> texts)
        {
            var result = 0;
            for (var index = 0; index < texts.Count; index++)
            {
                for (var other = index + 1; other < texts.Count; other++)
                {
                    if (!(texts[index].Right <= texts[other].Left || texts[index].Left >= texts[other].Right || texts[index].Top <= texts[other].Bottom || texts[index].Bottom >= texts[other].Top))
                    {
                        result += 1;
                    }
                }
            }
            return result;
        }

        private static string UStageSourcePartLabel(List<object> drawEvidence)
        {
            return "10-3Z-128 / BOX600*600*30*30 / GKZ60-2";
        }
```

- [ ] **Step 4: Replace the U-stage ad hoc annotation block**

In `ProbeGaFixtureUStageDrawing`, replace the current block that calls `InsertText(...)` and `InsertManualOverallDimensions(...)` with:

```csharp
                var sourcePartLabel = UStageSourcePartLabel(drawEvidence);
                var annotationLayout = BuildFixtureUStageAnnotationLayout(drawResult, drawFrame, sourcePartLabel);
                var textInserted = RenderAnnotationLayout(sheet, annotationLayout, drawResult);
                var dimensionInserted = annotationLayout.Lines.Any(line => line.Kind == "DIMENSION");
```

- [ ] **Step 5: Add layout evidence to the U-stage JSON payload**

In the anonymous object written to `tekla-ga-fixture-u-stage-...json`, add these fields near `draw_evidence = drawEvidence`:

```csharp
                            annotation_layout = annotationLayout,
                            annotation_layout_status = annotationLayout.LayoutStatus,
                            annotation_collision_count = annotationLayout.CollisionCount,
```

- [ ] **Step 6: Build after C# changes**

Run:

```powershell
dotnet build I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\BoxProgressiveDrawingPoc.csproj
```

Expected output includes:

```text
已成功生成。
0 个错误
```

- [ ] **Step 7: Commit Task 3 changes**

Run:

```powershell
git add tools/tekla2017_progressive_drawing_poc/Program.cs
git commit -m "Route Tekla U-stage annotations through layout DTO"
```

## Task 4: Tekla Smoke Verification for Clean Layout Output

**Files:**
- Modify: `I:\zijinhuatekla\docs\verification\2026-07-07-tekla-openapi-existing-drawing-inspection.md`
- Modify: `I:\zijinhuatekla\TASKLIST.md`

- [ ] **Step 1: Close active Tekla drawing**

Run:

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe --close-active-drawing
```

Expected output is `Active drawing: <none>` or `Active drawing closed without saving.`

- [ ] **Step 2: Generate the U-stage clean drawing through the layout DTO**

Run:

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe `
  --probe-ga-fixture-u-stage-model-id 28717373 `
  --source-sheet 0 `
  --out I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6
```

Expected output includes:

```text
Fixture U-stage using virtual BOX profile decomposition from part 28705233 profile=BOX600*600*30*30.
GA fixture U-stage selected=1
Reopened primitive stats: lines=<positive> texts=<positive> dims=0 parts=0 marks=0 views=0
```

- [ ] **Step 3: Verify JSON evidence for layout status and no native dimensions**

Run:

```powershell
$j=Get-Content I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6\tekla-ga-fixture-u-stage-28717373-step1.json -Raw | ConvertFrom-Json
[pscustomobject]@{
  Drawing=$j.ga_name
  LayoutStatus=$j.annotation_layout_status
  CollisionCount=$j.annotation_collision_count
  Lines=$j.reopened.Lines
  Texts=$j.reopened.Texts
  Dimensions=$j.reopened.Dimensions
  StraightDimensions=$j.reopened.StraightDimensions
  StraightDimensionSets=$j.reopened.StraightDimensionSets
  Parts=$j.reopened.Parts
  Marks=$j.reopened.Marks
  Views=$j.reopened.Views
} | Format-List
```

Expected output includes:

```text
LayoutStatus          : OK
CollisionCount        : 0
Dimensions            : 0
StraightDimensions    : 0
StraightDimensionSets : 0
Parts                 : 0
Marks                 : 0
Views                 : 0
```

- [ ] **Step 4: Close active Tekla drawing after verification**

Run:

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe --close-active-drawing
```

Expected output is `Active drawing: <none>` or `Active drawing closed without saving.`

- [ ] **Step 5: Append verification evidence**

Run this PowerShell block to append evidence from the JSON generated in Step 2:

```powershell
$j=Get-Content I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6\tekla-ga-fixture-u-stage-28717373-step1.json -Raw | ConvertFrom-Json
$verify='I:\zijinhuatekla\docs\verification\2026-07-07-tekla-openapi-existing-drawing-inspection.md'
$entry=@"

### U-Stage Annotation Layout DTO Smoke

The Tekla U-stage POC now routes stage notes, dimensions, thickness callout, and part mark through a layout DTO before rendering. Renderer output uses only ordinary ``Line`` and ``Text`` objects for GA sheet annotations.

- Drawing: ``$($j.ga_name)``
- Layout status: ``$($j.annotation_layout_status)``
- Collision count: ``$($j.annotation_collision_count)``
- Reopened stats: ``lines=$($j.reopened.Lines) texts=$($j.reopened.Texts) dimensions=$($j.reopened.Dimensions) parts=$($j.reopened.Parts) marks=$($j.reopened.Marks) views=$($j.reopened.Views)``
- Decision: keep Tekla GA dimensions as primitive line/text until a drawing-view-bound native dimension path is proven safe.
"@
$enc=New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::AppendAllText($verify,$entry,$enc)
```

- [ ] **Step 6: Update TASKLIST**

In `I:\zijinhuatekla\TASKLIST.md`, change the annotation/layout task line from unchecked to checked only if Steps 1-5 passed.

- [ ] **Step 7: Commit verification docs**

Run:

```powershell
git add docs/verification/2026-07-07-tekla-openapi-existing-drawing-inspection.md TASKLIST.md
git commit -m "Record annotation layout Tekla smoke"
```

## Task 5: Final Regression Verification

**Files:**
- No code changes unless a verification failure reveals a defect.

- [ ] **Step 1: Run pure Python unit tests for the annotation and DXF path**

Run:

```powershell
python -m unittest tests.test_process_drawing_annotation_layout tests.test_box_progressive_dxf
```

Expected output includes:

```text
OK
```

- [ ] **Step 2: Build the Tekla POC**

Run:

```powershell
dotnet build I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\BoxProgressiveDrawingPoc.csproj
```

Expected output includes:

```text
已成功生成。
0 个错误
```

- [ ] **Step 3: Confirm final git status only contains intended files or known pre-existing dirty files**

Run:

```powershell
git -C I:\zijinhuatekla status --short
```

Expected: files touched by this plan are committed or clearly identified. Do not revert unrelated existing dirty files.

- [ ] **Step 4: Write final handoff summary in chat**

Report these exact facts:

```text
- Python annotation layout tests passed or the failure output.
- DXF adapter tests passed or the failure output.
- Tekla POC build passed or the failure output.
- Tekla smoke drawing name and mark if smoke ran.
- Reopened stats show StraightDimensions=0 and StraightDimensionSets=0 if smoke ran.
- Any unverified item and reason.
```

## Self-Review

- Spec coverage: The plan covers separated geometry, intent, layout, and renderer layers; U-stage total length, section width, wall thickness, part mark, fixture note, virtual BOX warning, collision status, Tekla primitive rendering, and DXF adapter reuse each have a task.
- 占位扫描：计划中没有空白需求、没有未说明的错误处理步骤，也没有只要求写测试但不给具体测试内容的步骤。
- Type consistency: Python names are consistent across tests and implementation: `ProjectionScene`, `AnnotationIntent`, `AnnotationLayout`, `LayoutLine`, `LayoutText`, `layout_annotation_intents`, and `layout_to_jsonable`. C# DTO names are consistent across builder, renderer, and JSON evidence: `DrawingAnnotationLayout`, `DrawingAnnotationLine`, and `DrawingAnnotationText`.
