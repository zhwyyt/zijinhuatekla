# Part Drawing CAD Dimension Style Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Repository constraint:** Tasks 2-5 overlap the same renderer/layout files, so this repository's `AGENTS.md` requires inline execution. Do not dispatch implementation subagents unless the user explicitly changes that constraint.

**Goal:** Replace flattened `LINE + TEXT` part dimensions with sample-derived semantic dimensions, native editable DXF `DIMENSION` entities, and matching PDF vector styling.

**Architecture:** Add one versioned `CadDimensionStyle` preset derived from `零件标注.dwg`. Keep placed dimensions semantic through `PartDrawingLayout` and `PartDrawingDocument`; let DXF and PDF renderers consume the same `PlacedDimension` records without reselecting dimensions. Intents without enough geometric evidence remain notes or unplaced review items.

**Tech Stack:** Python 3.12, dataclasses, ezdxf 1.4.3, ReportLab, pypdf, unittest.

---

## File Structure

- Create `src/zijinhua_tekla/part_drawing/dimension_style.py`: versioned sample-derived style DTO and scale conversion.
- Create `tests/test_part_drawing_dimension_style.py`: locks sample parameters and scale behavior.
- Modify `src/zijinhua_tekla/part_drawing/dimension_optimizer.py`: convert placeable intents into semantic `PlacedDimension` records while retaining ordinary notes.
- Modify `src/zijinhua_tekla/part_drawing/drawing_output.py`: carry semantic dimensions into the document, emit native DXF dimensions, and draw equivalent PDF primitives.
- Modify `tests/test_part_drawing_layout.py`: assert semantic placement, direction, source geometry, and review behavior.
- Modify `tests/test_part_drawing_output.py`: assert native DXF objects, DIMSTYLE settings, PDF parity, and atomic failures.
- Modify `tests/test_part_drawing_pipeline.py`: protect manifest/status propagation and batch behavior.
- Modify `STATUS.md`, `TASKLIST.md`: record the completed style stage and remaining unplaced-hole work.
- Create `docs/verification/2026-07-13-part-drawing-cad-dimension-style.md`: focused tests, full suite, DXF audit, real smoke, and visual review evidence.

## Quality Boundary

Only intents with enough geometric evidence become CAD dimensions:

- `OVERALL`, `DATUM_X`, `DATUM_Y`, and two-anchor `LENGTH/WIDTH` become horizontal or vertical linear dimensions.
- One-anchor `DIAMETER` becomes a diameter dimension because its model value provides the diameter and the anchor provides the center.
- One-anchor `RADIUS` becomes a radius dimension because its model value provides the radius and the anchor provides the center.
- `THICKNESS`, `PATTERN`, single-anchor slot `LENGTH/WIDTH`, and `WARNING` stay ordinary annotation text.
- Capacity overflow remains `unplaced_intents` and continues to produce `REVIEW_REQUIRED`.

### Task 1: Add The Versioned CAD Dimension Style Contract

**Files:**
- Create: `src/zijinhua_tekla/part_drawing/dimension_style.py`
- Create: `tests/test_part_drawing_dimension_style.py`

- [ ] **Step 1: Write the failing style contract tests**

```python
import unittest

from zijinhua_tekla.part_drawing.dimension_style import PART_CAD_DIMENSION_STYLE_V1


class PartDrawingDimensionStyleTests(unittest.TestCase):
    def test_v1_matches_the_confirmed_cad_sample(self):
        style = PART_CAD_DIMENSION_STYLE_V1
        self.assertEqual("partCadDimensionStyle.v1", style.style_id)
        self.assertEqual("Arial", style.font_family)
        self.assertEqual(0.65, style.text_width_factor)
        self.assertEqual(2.5, style.text_height_mm)
        self.assertEqual("OBLIQUE", style.linear_arrow_name)
        self.assertEqual("", style.leader_arrow_name)
        self.assertEqual(2.0, style.arrow_size_mm)
        self.assertEqual(2.5, style.extension_offset_mm)
        self.assertEqual(2.0, style.extension_beyond_mm)
        self.assertEqual(1.0, style.text_gap_mm)
        self.assertEqual(0, style.decimal_places)

    def test_measurement_factor_is_inverse_of_layout_scale(self):
        style = PART_CAD_DIMENSION_STYLE_V1
        expected = {1.0: 1.0, 0.5: 2.0, 0.2: 5.0, 0.1: 10.0, 0.05: 20.0}
        self.assertEqual(expected, {scale: style.measurement_factor(scale) for scale in expected})
        with self.assertRaisesRegex(ValueError, "scale must be positive"):
            style.measurement_factor(0.0)
```

- [ ] **Step 2: Run the new tests and verify the missing module failure**

Run: `python -m unittest tests.test_part_drawing_dimension_style -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'zijinhua_tekla.part_drawing.dimension_style'`.

- [ ] **Step 3: Add the minimal immutable style contract**

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CadDimensionStyle:
    style_id: str
    font_family: str
    text_width_factor: float
    text_height_mm: float
    linear_arrow_name: str
    leader_arrow_name: str
    arrow_size_mm: float
    extension_offset_mm: float
    extension_beyond_mm: float
    text_gap_mm: float
    decimal_places: int
    suppress_trailing_zeros: bool
    text_above_line: bool

    def measurement_factor(self, layout_scale: float) -> float:
        if layout_scale <= 0:
            raise ValueError("layout scale must be positive")
        return 1.0 / layout_scale


PART_CAD_DIMENSION_STYLE_V1 = CadDimensionStyle(
    style_id="partCadDimensionStyle.v1",
    font_family="Arial",
    text_width_factor=0.65,
    text_height_mm=2.5,
    linear_arrow_name="OBLIQUE",
    leader_arrow_name="",
    arrow_size_mm=2.0,
    extension_offset_mm=2.5,
    extension_beyond_mm=2.0,
    text_gap_mm=1.0,
    decimal_places=0,
    suppress_trailing_zeros=True,
    text_above_line=True,
)
```

- [ ] **Step 4: Run the focused tests**

Run: `python -m unittest tests.test_part_drawing_dimension_style -v`

Expected: `Ran 2 tests ... OK`.

- [ ] **Step 5: Run the submission gate and commit only Task 1 files**

```powershell
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode working
git add src/zijinhua_tekla/part_drawing/dimension_style.py tests/test_part_drawing_dimension_style.py
git diff --cached --check
git commit -m "feat: define part drawing CAD dimension style"
```

Expected: CCG reports no blocking issue; commit contains exactly two files.

### Task 2: Preserve Semantic Dimensions Through Layout

**Files:**
- Modify: `src/zijinhua_tekla/part_drawing/dimension_optimizer.py`
- Modify: `tests/test_part_drawing_layout.py`

- [ ] **Step 1: Add failing assertions for semantic placement**

Extend `test_places_rectangle_dimensions_without_collision` and add a round-hole case:

```python
from dataclasses import replace

from zijinhua_tekla.part_drawing.contracts import HoleSnapshot, Point3D
from zijinhua_tekla.part_drawing.feature_recognizer import recognize_plate_features


def test_places_rectangle_dimensions_as_semantic_linear_dimensions(self):
    layout = optimize_dimension_layout(self.snapshot, self.geometry, self.intents, quantity=2)
    by_id = {item.dimension_id: item for item in layout.placed_dimensions}
    self.assertEqual("LINEAR_HORIZONTAL", by_id["overall-x"].kind.value)
    self.assertEqual("LINEAR_VERTICAL", by_id["overall-y"].kind.value)
    self.assertEqual(200.0, by_id["overall-x"].measured_value_mm)
    self.assertEqual(100.0, by_id["overall-y"].measured_value_mm)
    self.assertEqual(2, len(by_id["overall-x"].source_points))
    self.assertNotEqual(
        by_id["overall-x"].source_points[0],
        by_id["overall-x"].source_points[1],
    )


def test_places_hole_diameter_as_semantic_diameter_dimension(self):
    snapshot = replace(
        self.snapshot,
        holes=(HoleSnapshot("H1", "ROUND", Point3D(60, 70, 30), diameter=22),),
    )
    geometry = analyze_plate_geometry(snapshot).geometry
    features = recognize_plate_features(snapshot, geometry).features
    intents = generate_dimension_intents(snapshot, geometry, features).intents
    layout = optimize_dimension_layout(snapshot, geometry, intents, quantity=1)
    diameter = next(item for item in layout.placed_dimensions if item.dimension_id == "hole-H1-dia")
    self.assertEqual("DIAMETER", diameter.kind.value)
    self.assertEqual(22.0, diameter.measured_value_mm)
    self.assertEqual(11.0 * layout.scale, diameter.paper_radius)
```

Also strengthen the dense test:

```python
self.assertGreater(len(layout.unplaced_intents), 0)
self.assertLessEqual(len(layout.placed_dimensions) + len(layout.annotation_texts), 26)
```

- [ ] **Step 2: Run the layout tests and verify the missing field failure**

Run: `python -m unittest tests.test_part_drawing_layout -v`

Expected: FAIL with `AttributeError: 'PartDrawingLayout' object has no attribute 'placed_dimensions'`.

- [ ] **Step 3: Add semantic placed-dimension types**

Add above `PartDrawingLayout`:

```python
from enum import Enum


class PlacedDimensionKind(str, Enum):
    LINEAR_HORIZONTAL = "LINEAR_HORIZONTAL"
    LINEAR_VERTICAL = "LINEAR_VERTICAL"
    RADIUS = "RADIUS"
    DIAMETER = "DIAMETER"


@dataclass(frozen=True)
class PlacedDimension:
    dimension_id: str
    kind: PlacedDimensionKind
    source_points: tuple[tuple[float, float], ...]
    dimension_line_point: tuple[float, float]
    measured_value_mm: float
    display_text: str
    text_rotation: float
    text_box: DrawingRect
    paper_radius: float = 0.0
    evidence_codes: tuple[str, ...] = ()
```

Add `placed_dimensions: tuple[PlacedDimension, ...]` to `PartDrawingLayout` before `annotation_lines`.

- [ ] **Step 4: Convert placeable intents without fabricating unsupported geometry**

Change the placement loop to collect `dimensions`, and pass `transform` into `_place`:

```python
dimensions, lines, texts, unplaced = [], [], [], []
...
dimension, line, text = _place(intent, view, transform, counts.get(band, 0))
obstacle = dimension.text_box if dimension else text.box
if obstacle.left < 12 or obstacle.right > PAGE_WIDTH - 12 or obstacle.top < 12 or obstacle.bottom > PAGE_HEIGHT - 12:
    unplaced.append(intent)
    continue
existing_boxes = [item.text_box for item in dimensions] + [item.box for item in texts]
if any(obstacle.intersects(existing, 1.0) for existing in existing_boxes):
    unplaced.append(intent)
    continue
if dimension:
    dimensions.append(dimension)
if line:
    lines.append(line)
if text:
    texts.append(text)
...
return PartDrawingLayout(
    PAGE_WIDTH, PAGE_HEIGHT, scale, view, transform, tuple(dimensions),
    tuple(lines), tuple(texts), ...
)
```

Implement the dispatch at the start of `_place`:

```python
def _place(intent, view, transform, index):
    x, y = _band_position(intent.preferred_band, view, index)
    if _is_placeable_linear(intent):
        points = tuple(transform.point(anchor) for anchor in intent.anchors[:2])
        kind = (
            PlacedDimensionKind.LINEAR_VERTICAL
            if intent.preferred_band in {"left", "right"}
            else PlacedDimensionKind.LINEAR_HORIZONTAL
        )
        rotation = 90.0 if kind == PlacedDimensionKind.LINEAR_VERTICAL else 0.0
        box = _dimension_text_box(x, y, intent.text, 2.5, rotation)
        return PlacedDimension(
            intent.intent_id, kind, points, (x, y), float(intent.model_value),
            intent.text, rotation, box, evidence_codes=intent.evidence_codes,
        ), None, None
    if intent.kind in {DimensionKind.DIAMETER, DimensionKind.RADIUS} and intent.anchors and intent.model_value:
        center = transform.point(intent.anchors[0])
        paper_radius = float(intent.model_value) * transform.scale
        if intent.kind == DimensionKind.DIAMETER:
            paper_radius /= 2.0
        kind = PlacedDimensionKind(intent.kind.value)
        box = _dimension_text_box(x, y, intent.text, 2.5, 0.0)
        return PlacedDimension(
            intent.intent_id, kind, (center,), (x, y), float(intent.model_value),
            intent.text, 0.0, box, paper_radius, intent.evidence_codes,
        ), None, None
    height = 3.5
    width = _text_width(intent.text, height)
    text = DrawingText(x, y, intent.text, height, "ANNOTATION", DrawingRect(x - width / 2, y - height, x + width / 2, y + height))
    return None, None, text


def _is_placeable_linear(intent):
    return (
        len(intent.anchors) >= 2
        and intent.model_value is not None
        and intent.kind in {
            DimensionKind.OVERALL,
            DimensionKind.DATUM_X,
            DimensionKind.DATUM_Y,
            DimensionKind.LENGTH,
            DimensionKind.WIDTH,
        }
    )
```

Extract the existing band coordinate branches into `_band_position()`. `_dimension_text_box()` uses width `2.5` and swaps the width/height bounds for 90-degree text. Do not synthesize source endpoints for single-anchor slot length/width intents; they remain annotations.

```python
def _band_position(band, view, index):
    if band == "top":
        return (view.left + view.right) / 2, view.top - 8 - index * 7
    if band == "right":
        return view.right + 12 + index * 9, (view.top + view.bottom) / 2
    if band == "bottom":
        return (view.left + view.right) / 2, view.bottom + 10 + index * 7
    if band == "left":
        return view.left - 30 - index * 9, (view.top + view.bottom) / 2
    return view.left, 232 + index * 7


def _dimension_text_box(x, y, text, height, rotation):
    width = _text_width(text, height)
    if rotation % 180 == 90:
        width, height = height * 2, width / 2
    return DrawingRect(x - width / 2, y - height, x + width / 2, y + height)
```

- [ ] **Step 5: Run focused layout and dimension-generator regression tests**

Run: `python -m unittest tests.test_part_drawing_dimensions tests.test_part_drawing_layout -v`

Expected: all tests PASS; the dense case remains `REVIEW_REQUIRED`.

- [ ] **Step 6: Run CCG and commit Task 2**

```powershell
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode working
git add src/zijinhua_tekla/part_drawing/dimension_optimizer.py tests/test_part_drawing_layout.py
git diff --cached --check
git commit -m "feat: preserve semantic part dimensions"
```

### Task 3: Carry Dimensions And Style In The Shared Drawing Document

**Files:**
- Modify: `src/zijinhua_tekla/part_drawing/drawing_output.py`
- Modify: `tests/test_part_drawing_output.py`

- [ ] **Step 1: Write failing shared-document assertions**

Add to `test_writes_dxf_pdf_and_json_from_one_document`:

```python
self.assertEqual(2, len(self.document.placed_dimensions))
self.assertEqual("partCadDimensionStyle.v1", self.document.dimension_style.style_id)
self.assertEqual(
    [item.display_text for item in self.document.placed_dimensions],
    payload["placed_dimensions"],
)
self.assertEqual("partCadDimensionStyle.v1", payload["dimension_style"]["style_id"])
```

Update `PartDrawingDocument.annotation_texts()` expectation so it returns placed dimension text plus ordinary note/title-related annotation text.

- [ ] **Step 2: Run the output test and verify the missing document fields**

Run: `python -m unittest tests.test_part_drawing_output.PartDrawingOutputTests.test_writes_dxf_pdf_and_json_from_one_document -v`

Expected: FAIL because `PartDrawingDocument` has no `placed_dimensions` or `dimension_style`.

- [ ] **Step 3: Add the shared fields and JSON serialization**

Import the style and placed type:

```python
from dataclasses import asdict, dataclass

from .dimension_style import CadDimensionStyle, PART_CAD_DIMENSION_STYLE_V1
from .dimension_optimizer import PlacedDimension
```

Add fields to `PartDrawingDocument`:

```python
placed_dimensions: tuple[PlacedDimension, ...]
dimension_style: CadDimensionStyle
```

Populate them in `build_part_drawing_document()`:

```python
placed_dimensions=layout.placed_dimensions,
dimension_style=PART_CAD_DIMENSION_STYLE_V1,
```

Change text collection and JSON output:

```python
def annotation_texts(self) -> list[str]:
    return (
        [item.display_text for item in self.placed_dimensions]
        + [item.text for item in self.annotation_text_items]
    )

...
"placed_dimensions": [item.display_text for item in document.placed_dimensions],
"dimension_style": asdict(document.dimension_style),
```

Count semantic dimensions separately in `_entity_counts()`:

```python
"dimensions": len(document.placed_dimensions),
```

- [ ] **Step 4: Run output and pipeline regressions**

Run: `python -m unittest tests.test_part_drawing_output tests.test_part_drawing_pipeline -v`

Expected: PASS before native rendering is introduced; existing files and JSON remain atomic.

- [ ] **Step 5: Run CCG and commit Task 3**

```powershell
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode working
git add src/zijinhua_tekla/part_drawing/drawing_output.py tests/test_part_drawing_output.py
git diff --cached --check
git commit -m "feat: carry part dimensions in drawing documents"
```

### Task 4: Emit Native Editable DXF Dimensions

**Files:**
- Modify: `src/zijinhua_tekla/part_drawing/drawing_output.py`
- Modify: `tests/test_part_drawing_output.py`

- [ ] **Step 1: Add failing native-DXF tests**

In the common output test, after reading DXF:

```python
dimensions = list(dxf.modelspace().query("DIMENSION"))
self.assertEqual(2, len(dimensions))
self.assertFalse(list(dxf.modelspace().query('LINE[layer=="DIMENSION"]')))
style = dxf.dimstyles.get("PART-CAD-V1")
self.assertEqual(2.5, style.dxf.dimtxt)
self.assertEqual(2.0, style.dxf.dimasz)
self.assertEqual(2.5, style.dxf.dimexo)
self.assertEqual(2.0, style.dxf.dimexe)
self.assertEqual(1.0, style.dxf.dimgap)
self.assertEqual(0, style.dxf.dimdec)
self.assertEqual(8, style.dxf.dimzin)
self.assertEqual("_OBLIQUE", style.dxf.dimblk)
self.assertEqual(0.65, dxf.styles.get("TArial").dxf.width)
raw_measurements = sorted(float(item.get_measurement()) for item in dimensions)
self.assertEqual([100.0, 200.0], raw_measurements)
for entity in dimensions:
    overrides = entity.get_acad_dstyle(dxf.dimstyles.get(entity.dxf.dimstyle))
    self.assertEqual(1.0, overrides["dimlfac"])
```

The rectangular fixture fits at scale `1.0`; its raw measurements and model values are both `200/100`. The style-contract test covers inverse factors for all standard scales, and the real `T3-PX-317` smoke below verifies the `0.5 -> 2.0` DXF override path.

In the round-hole test:

```python
dimension_entities = list(ezdxf.readfile(paths.dxf_path).modelspace().query("DIMENSION"))
self.assertEqual(5, len(dimension_entities))
self.assertIn("DIA22", {entity.dxf.text for entity in dimension_entities})
```

- [ ] **Step 2: Run the two output tests and verify no native dimensions exist**

Run:

```powershell
python -m unittest `
  tests.test_part_drawing_output.PartDrawingOutputTests.test_writes_dxf_pdf_and_json_from_one_document `
  tests.test_part_drawing_output.PartDrawingOutputTests.test_explicit_round_hole_is_present_in_shared_document_and_dxf -v
```

Expected: FAIL because the DXF contains zero `DIMENSION` entities.

- [ ] **Step 3: Create the sample-derived DXF text and dimension styles**

Add constants and helper:

```python
from ezdxf.render.arrows import ARROWS

DXF_DIMSTYLE_NAME = "PART-CAD-V1"
DXF_DIMTEXT_STYLE_NAME = "TArial"


def _ensure_dxf_dimension_style(dxf, document):
    style = document.dimension_style
    if DXF_DIMTEXT_STYLE_NAME not in dxf.styles:
        dxf.styles.new(
            DXF_DIMTEXT_STYLE_NAME,
            dxfattribs={"font": "arial.ttf", "width": style.text_width_factor},
        )
    text_style = dxf.styles.get(DXF_DIMTEXT_STYLE_NAME)
    if DXF_DIMSTYLE_NAME in dxf.dimstyles:
        dimstyle = dxf.dimstyles.get(DXF_DIMSTYLE_NAME)
    else:
        dimstyle = dxf.dimstyles.new(DXF_DIMSTYLE_NAME)
    dimstyle.dxf.dimtxsty = text_style.dxf.handle
    dimstyle.dxf.dimtxt = style.text_height_mm
    dimstyle.dxf.dimasz = style.arrow_size_mm
    dimstyle.dxf.dimexo = style.extension_offset_mm
    dimstyle.dxf.dimexe = style.extension_beyond_mm
    dimstyle.dxf.dimgap = style.text_gap_mm
    dimstyle.dxf.dimdec = style.decimal_places
    dimstyle.dxf.dimzin = 8 if style.suppress_trailing_zeros else 0
    dimstyle.dxf.dimtad = 1 if style.text_above_line else 0
    dimstyle.dxf.dimscale = 1.0
    dimstyle.set_arrows(blk=ARROWS.oblique, ldrblk=ARROWS.closed_filled)
    return dimstyle
```

- [ ] **Step 4: Add native dimensions before saving the DXF**

Call `_ensure_dxf_dimension_style(dxf, document)` before iterating modelspace entities. Do not add `document.annotation_lines` for semantic dimensions; those are now reserved for ordinary annotation lines.

```python
for dimension in document.placed_dimensions:
    _add_dxf_dimension(modelspace, document, dimension)
```

Implement the dispatcher:

```python
def _add_dxf_dimension(modelspace, document, dimension):
    factor = document.dimension_style.measurement_factor(document.scale)
    override = {"dimlfac": factor}
    text = _dxf_dimension_text(dimension)
    if dimension.kind == PlacedDimensionKind.LINEAR_HORIZONTAL:
        result = modelspace.add_linear_dim(
            base=dimension.dimension_line_point,
            p1=dimension.source_points[0],
            p2=dimension.source_points[1],
            angle=0.0,
            text=text,
            dimstyle=DXF_DIMSTYLE_NAME,
            override=override,
            dxfattribs={"layer": "DIMENSION"},
        )
    elif dimension.kind == PlacedDimensionKind.LINEAR_VERTICAL:
        result = modelspace.add_linear_dim(
            base=dimension.dimension_line_point,
            p1=dimension.source_points[0],
            p2=dimension.source_points[1],
            angle=90.0,
            text_rotation=90.0,
            text=text,
            dimstyle=DXF_DIMSTYLE_NAME,
            override=override,
            dxfattribs={"layer": "DIMENSION"},
        )
    else:
        center = dimension.source_points[0]
        edge = (center[0] + dimension.paper_radius, center[1])
        method = (
            modelspace.add_diameter_dim
            if dimension.kind == PlacedDimensionKind.DIAMETER
            else modelspace.add_radius_dim
        )
        result = method(
            center=center,
            mpoint=edge,
            location=dimension.dimension_line_point,
            text=text,
            dimstyle=DXF_DIMSTYLE_NAME,
            override={**override, "dimblk": ARROWS.closed_filled},
            dxfattribs={"layer": "DIMENSION"},
        )
    result.render()


def _dxf_dimension_text(dimension):
    plain = f"{dimension.measured_value_mm:g}"
    return "<>" if dimension.display_text == plain else dimension.display_text
```

Use explicit text only for `R...`, `DIA...`, or other business prefixes. Never use text override to compensate for a wrong measurement factor.

- [ ] **Step 5: Run native DXF tests and audit**

Run: `python -m unittest tests.test_part_drawing_output -v`

Expected: all output tests PASS; every generated DXF has `audit().has_errors == False`.

- [ ] **Step 6: Run CCG and commit Task 4**

```powershell
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode working
git add src/zijinhua_tekla/part_drawing/drawing_output.py tests/test_part_drawing_output.py
git diff --cached --check
git commit -m "feat: render native CAD part dimensions"
```

### Task 5: Render The Same Dimension Style In PDF

**Files:**
- Modify: `src/zijinhua_tekla/part_drawing/drawing_output.py`
- Modify: `tests/test_part_drawing_output.py`

- [ ] **Step 1: Add failing PDF parity assertions**

Extend the common output test:

```python
pdf = PdfReader(str(paths.pdf_path))
page_text = pdf.pages[0].extract_text()
self.assertIn("200", page_text)
self.assertIn("100", page_text)
self.assertEqual(
    sorted(item.display_text for item in self.document.placed_dimensions),
    sorted(text for text in ("200", "100") if text in page_text),
)
```

Add a focused renderer spy test using `unittest.mock.patch` around `_draw_pdf_dimension`:

```python
from unittest.mock import patch

from zijinhua_tekla.part_drawing import drawing_output


def test_pdf_renderer_consumes_each_shared_placed_dimension(self):
    with tempfile.TemporaryDirectory() as directory, patch(
        "zijinhua_tekla.part_drawing.drawing_output._draw_pdf_dimension",
        wraps=drawing_output._draw_pdf_dimension,
    ) as draw_dimension:
        render_part_drawing(self.document, Path(directory))
        self.assertEqual(len(self.document.placed_dimensions), draw_dimension.call_count)
```

- [ ] **Step 2: Run the PDF tests and verify semantic dimensions are not rendered yet**

Run: `python -m unittest tests.test_part_drawing_output -v`

Expected: FAIL because `220/140` disappeared when flattened dimension text was removed, or because `_draw_pdf_dimension` does not exist.

- [ ] **Step 3: Route every placed dimension through one PDF helper**

In `_render_pdf()`:

```python
for dimension in document.placed_dimensions:
    _draw_pdf_dimension(pdf, document, dimension, font_name)
```

Add the dispatcher:

```python
def _draw_pdf_dimension(pdf, document, dimension, font_name):
    style = document.dimension_style
    if dimension.kind in {
        PlacedDimensionKind.LINEAR_HORIZONTAL,
        PlacedDimensionKind.LINEAR_VERTICAL,
    }:
        _draw_pdf_linear_dimension(pdf, document, dimension, style, font_name)
    else:
        _draw_pdf_radial_dimension(pdf, document, dimension, style, font_name)
```

- [ ] **Step 4: Implement linear extension lines, oblique ticks, line break, and compressed text**

Use page-coordinate helpers so PDF Y inversion happens only at the final draw call:

```python
def _pdf_line(pdf, document, start, end):
    pdf.line(
        start[0] * mm,
        (document.page_height - start[1]) * mm,
        end[0] * mm,
        (document.page_height - end[1]) * mm,
    )


def _draw_pdf_linear_dimension(pdf, document, dimension, style, font_name):
    vertical = dimension.kind == PlacedDimensionKind.LINEAR_VERTICAL
    p1, p2 = dimension.source_points
    base = dimension.dimension_line_point
    axis = 1 if vertical else 0
    cross = 0 if vertical else 1
    line_cross = base[cross]
    for point in (p1, p2):
        direction = 1.0 if line_cross >= point[cross] else -1.0
        start = list(point)
        end = list(point)
        start[cross] += direction * style.extension_offset_mm
        end[cross] = line_cross + direction * style.extension_beyond_mm
        _pdf_line(pdf, document, tuple(start), tuple(end))
    first = [p1[0], p1[1]]
    second = [p2[0], p2[1]]
    first[cross] = line_cross
    second[cross] = line_cross
    _draw_pdf_dimension_line_with_text_gap(
        pdf, document, tuple(first), tuple(second), dimension.text_box,
        vertical, style.text_gap_mm,
    )
    _draw_pdf_oblique_tick(pdf, document, tuple(first), style.arrow_size_mm)
    _draw_pdf_oblique_tick(pdf, document, tuple(second), style.arrow_size_mm)
    _pdf_dimension_text(pdf, document, dimension, style, font_name)
```

Implement the helpers explicitly:

```python
def _draw_pdf_dimension_line_with_text_gap(pdf, document, first, second, box, vertical, gap):
    axis = 1 if vertical else 0
    cross = 0 if vertical else 1
    low, high = sorted((first[axis], second[axis]))
    gap_low = (box.top if vertical else box.left) - gap
    gap_high = (box.bottom if vertical else box.right) + gap
    fixed = first[cross]
    if low < gap_low:
        start, end = [fixed, fixed], [fixed, fixed]
        start[axis], start[cross] = low, fixed
        end[axis], end[cross] = min(gap_low, high), fixed
        _pdf_line(pdf, document, tuple(start), tuple(end))
    if gap_high < high:
        start, end = [fixed, fixed], [fixed, fixed]
        start[axis], start[cross] = max(gap_high, low), fixed
        end[axis], end[cross] = high, fixed
        _pdf_line(pdf, document, tuple(start), tuple(end))


def _draw_pdf_oblique_tick(pdf, document, point, size):
    half = size / math.sqrt(2.0)
    _pdf_line(
        pdf,
        document,
        (point[0] - half, point[1] + half),
        (point[0] + half, point[1] - half),
    )


def _pdf_dimension_text(pdf, document, dimension, style, font_name):
    pdf.saveState()
    pdf.translate(
        dimension.dimension_line_point[0] * mm,
        (document.page_height - dimension.dimension_line_point[1]) * mm,
    )
    pdf.rotate(dimension.text_rotation)
    text = pdf.beginText()
    text.setFont(font_name, style.text_height_mm * mm)
    text.setHorizScale(style.text_width_factor * 100.0)
    width = pdfmetrics.stringWidth(
        dimension.display_text, font_name, style.text_height_mm * mm
    ) * style.text_width_factor
    text.setTextOrigin(-width / 2.0, 0)
    text.textOut(dimension.display_text)
    pdf.drawText(text)
    pdf.restoreState()
```

The gap helper uses the layout-provided text box; it does not estimate width again in the renderer.

- [ ] **Step 5: Implement radial/diameter leader and filled arrow**

```python
def _draw_pdf_radial_dimension(pdf, document, dimension, style, font_name):
    center = dimension.source_points[0]
    edge = (center[0] + dimension.paper_radius, center[1])
    location = dimension.dimension_line_point
    _pdf_line(pdf, document, edge, location)
    _draw_pdf_filled_arrow(pdf, document, edge, location, style.arrow_size_mm)
    _pdf_dimension_text(pdf, document, dimension, style, font_name)
```

Implement the filled arrow without a renderer-specific dimension decision:

```python
def _draw_pdf_filled_arrow(pdf, document, tip, tail, size):
    dx, dy = tail[0] - tip[0], tail[1] - tip[1]
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        raise PartDrawingRenderError("radial dimension leader has zero length")
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    base = (tip[0] + ux * size, tip[1] + uy * size)
    half_width = size / 2.0
    left = (base[0] + px * half_width, base[1] + py * half_width)
    right = (base[0] - px * half_width, base[1] - py * half_width)
    path = pdf.beginPath()
    path.moveTo(tip[0] * mm, (document.page_height - tip[1]) * mm)
    path.lineTo(left[0] * mm, (document.page_height - left[1]) * mm)
    path.lineTo(right[0] * mm, (document.page_height - right[1]) * mm)
    path.close()
    pdf.drawPath(path, stroke=1, fill=1)
```

Diameter text remains the existing `DIA...` business format; radius text remains `R...`.

- [ ] **Step 6: Run PDF/DXF parity tests**

Run: `python -m unittest tests.test_part_drawing_output -v`

Expected: all tests PASS; PDF extraction contains the same placed dimension texts as the shared document, and DXF audit remains clean.

- [ ] **Step 7: Run CCG and commit Task 5**

```powershell
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode working
git add src/zijinhua_tekla/part_drawing/drawing_output.py tests/test_part_drawing_output.py
git diff --cached --check
git commit -m "feat: match CAD dimension styling in PDF"
```

### Task 6: Lock Pipeline Status And Real Smoke Evidence

**Files:**
- Modify: `tests/test_part_drawing_pipeline.py`
- Modify: `STATUS.md`
- Modify: `TASKLIST.md`
- Create: `docs/verification/2026-07-13-part-drawing-cad-dimension-style.md`

- [ ] **Step 1: Add a failing batch-manifest style assertion**

In the successful batch pipeline test, read the generated drawing JSON and assert:

```python
drawing_payload = json.loads(next(output.rglob("*.drawing.json")).read_text(encoding="utf-8"))
self.assertEqual("partCadDimensionStyle.v1", drawing_payload["dimension_style"]["style_id"])
self.assertGreaterEqual(drawing_payload["entity_counts"]["dimensions"], 2)
```

In the review-required test, retain the existing unplaced count assertion and add:

```python
self.assertEqual("REVIEW_REQUIRED", result.items[0].status.value)
self.assertTrue(any(issue.code == IssueCode.LAYOUT_OVERFLOW for issue in result.items[0].issues))
```

- [ ] **Step 2: Run pipeline tests**

Run: `python -m unittest tests.test_part_drawing_pipeline -v`

Expected: the manifest assertion initially fails if style serialization was missed; after Tasks 3-5 it passes without production changes. If it already passes, retain the test as regression coverage and proceed.

- [ ] **Step 3: Run focused and full automated verification**

```powershell
python -m unittest `
  tests.test_part_drawing_dimension_style `
  tests.test_part_drawing_dimensions `
  tests.test_part_drawing_layout `
  tests.test_part_drawing_output `
  tests.test_part_drawing_pipeline -v
python -m unittest discover -s tests
```

Expected: focused tests PASS; full suite reports all tests `OK`. Record exact counts and warnings rather than predicted counts.

- [ ] **Step 4: Re-run the real selected-part smoke outside the repository output tree**

```powershell
python -m zijinhua_tekla.cli draw-parts `
  --snapshot-root I:\tmp\tekla-selected-part-snapshot-smoke-20260713-v2\part-drawing-snapshots `
  --out I:\tmp\tekla-selected-part-drawing-cad-style-20260713 `
  --cjk-font C:\Windows\Fonts\simhei.ttf
```

Expected: one `T3-PX-317` DXF/PDF/drawing JSON is generated; status remains `REVIEW_REQUIRED` while the 17 unplaced hole-related intents remain reported.

- [ ] **Step 5: Audit the real DXF and render a PDF preview**

```powershell
python -c "import ezdxf; p=r'I:\tmp\tekla-selected-part-drawing-cad-style-20260713\parts\T3-PX-317\T3-PX-317.dxf'; d=ezdxf.readfile(p); a=d.audit(); dims=list(d.modelspace().query('DIMENSION')); factor=dims[0].get_acad_dstyle(d.dimstyles.get(dims[0].dxf.dimstyle)).get('dimlfac') if dims else None; print(f'dimensions={len(dims)} audit_errors={len(a.errors)} audit_fixes={len(a.fixes)} style={dims[0].dxf.dimstyle if dims else None} dimlfac={factor}')"
pdftoppm -png -f 1 -singlefile -r 150 I:\tmp\tekla-selected-part-drawing-cad-style-20260713\parts\T3-PX-317\T3-PX-317.pdf I:\tmp\tekla-selected-part-drawing-cad-style-20260713\T3-PX-317-preview
```

Expected: at least two native dimensions, `audit_errors=0`, `audit_fixes=0`, style `PART-CAD-V1`, `dimlfac=2.0`, and a nonblank PNG preview.

- [ ] **Step 6: Perform the required visual checks**

Inspect the PNG and DXF in CAD:

- linear dimensions have 45-degree oblique ticks;
- extension lines start clear of the contour and extend past the dimension line;
- horizontal and vertical dimension text follow their dimension direction;
- dimension text is visibly narrower and smaller than the old `3.5` annotation text;
- no new overlaps appear;
- the 17 unplaced hole annotations are still explicitly reported.

Do not mark the visual check passed from entity counts alone.

- [ ] **Step 7: Write verification and live-memory updates**

Create `docs/verification/2026-07-13-part-drawing-cad-dimension-style.md` with:

```markdown
# 零件图 CAD 原生尺寸样式验证

## Scope

- 样板来源与提取参数
- 代码和测试范围

## Automated Verification

- focused test command and exact result
- full test command and exact result
- DXF audit and native dimension counts

## Real Smoke

- input/output paths
- `T3-PX-317` status
- unplaced intent count
- preview path

## Manual Review

- oblique ticks
- extension lines
- text height/width/direction
- remaining risks
```

Update `STATUS.md` with a short handoff linking this verification record. Mark the CAD dimension-style task complete in `TASKLIST.md`, but keep hole-layout completion unchecked.

- [ ] **Step 8: Invoke verification-before-completion, run CCG, and commit evidence**

Read and follow `superpowers:verification-before-completion`, then run:

```powershell
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode working
git add tests/test_part_drawing_pipeline.py STATUS.md TASKLIST.md docs/verification/2026-07-13-part-drawing-cad-dimension-style.md
git diff --cached --check
git commit -m "docs: verify native part dimension styling"
```

Expected: only the pipeline regression, live-memory updates, and verification record are committed; the worktree is clean afterward.

## Final Completion Criteria

- All acceptance criteria in `docs/design/2026-07-13-part-drawing-cad-dimension-style.md` have evidence.
- DXF contains editable native dimensions with `PART-CAD-V1`.
- PDF consumes the same `PlacedDimension` records and visually matches the confirmed sample style.
- Real `T3-PX-317` output is regenerated and manually inspected.
- The existing 17 unplaced hole-related annotations remain visible as review debt, not silently converted or discarded.
- Focused tests, full suite, DXF audit, and CCG verification are freshly passing.
