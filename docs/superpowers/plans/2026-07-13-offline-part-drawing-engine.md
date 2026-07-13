# Offline Flat-Part Drawing Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a contract-driven offline engine that turns flat-plate snapshots into auditable DXF/PDF part drawings with geometry, feature, dimension, layout, and quality evidence.

**Architecture:** Add a focused `part_drawing` package containing the five approved core modules behind a batch pipeline. A single `PartDrawingDocument` is the source for DXF, PDF, and JSON evidence; invalid or conflicting inputs stop at the quality gate instead of producing drawings.

**Tech Stack:** Python 3.10+ dataclasses and `unittest`, Shapely 2.x for topology checks, ezdxf 1.x for DXF, ReportLab 4.x for vector PDF, pypdf for PDF readback verification.

---

## Scope And Sequencing

This plan implements the offline consumer and drawing engine against versioned contract fixtures. It does not modify the separate Tekla exporter repository. After this plan passes, write a separate exporter plan that produces `partDrawingSnapshot.v1` from real Tekla parts and runs the real-model smoke required by the architecture design.

The implemented engine covers:

- Flat plates with line and arc contours.
- Circular holes, hole groups, slots, polygonal cutouts, chamfers, notches, and arc cutouts.
- Translation/rotation-independent grouping by `partPosition`.
- Shared DXF/PDF/JSON drawing output.
- `OK`, `REVIEW_REQUIRED`, and `REJECTED` quality states.

## Design Traceability

| Approved design responsibility | Implemented by |
| --- | --- |
| Snapshot contract and Data Quality Gate | Tasks 1 and 3 |
| `GeometryAnalyzer` | Task 2 |
| `FeatureRecognizer` | Task 4 |
| `DimensionGenerator` | Task 5 |
| `DimensionOptimizer` | Task 6 |
| `DrawingOutput` and shared `PartDrawingDocument` | Task 7 |
| Isolated batch pipeline and status summary | Task 8 |
| Acceptance Criteria and Verification Plan evidence | Task 9 |
| Real Tekla snapshot producer and real-model smoke | Separate follow-up plan after Task 9 |

## File Structure

- Create: `src/zijinhua_tekla/part_drawing/__init__.py`
  - Public facade for the offline part-drawing engine.
- Create: `src/zijinhua_tekla/part_drawing/contracts.py`
  - Immutable snapshot, geometry, feature, intent, document, issue, and batch DTOs.
- Create: `src/zijinhua_tekla/part_drawing/snapshot_input.py`
  - JSON parsing, contract validation, and safe filename handling.
- Create: `src/zijinhua_tekla/part_drawing/geometry_analyzer.py`
  - 3D-to-2D projection, loop validation, normalization, and canonical fingerprinting.
- Create: `src/zijinhua_tekla/part_drawing/feature_recognizer.py`
  - Hole, slot, cutout, chamfer, notch, and arc feature recognition.
- Create: `src/zijinhua_tekla/part_drawing/dimension_generator.py`
  - Deterministic dimension intent generation.
- Create: `src/zijinhua_tekla/part_drawing/dimension_optimizer.py`
  - Page fitting, dimension bands, text boxes, and collision/overflow status.
- Create: `src/zijinhua_tekla/part_drawing/drawing_output.py`
  - `PartDrawingDocument` builder plus DXF, PDF, and drawing JSON renderers.
- Create: `src/zijinhua_tekla/part_drawing/quality.py`
  - Same-position grouping and issue/status aggregation.
- Create: `src/zijinhua_tekla/part_drawing/pipeline.py`
  - Per-position isolated batch orchestration and summary output.
- Create: `tests/fixtures/part_drawing/rectangular_plate.json`
  - Minimal valid `partDrawingSnapshot.v1` example.
- Create: `tests/test_part_drawing_contracts.py`
- Create: `tests/test_part_drawing_geometry.py`
- Create: `tests/test_part_drawing_quality.py`
- Create: `tests/test_part_drawing_features.py`
- Create: `tests/test_part_drawing_dimensions.py`
- Create: `tests/test_part_drawing_layout.py`
- Create: `tests/test_part_drawing_output.py`
- Create: `tests/test_part_drawing_pipeline.py`
- Modify: `src/zijinhua_tekla/cli.py`
  - Add the `draw-parts` subcommand without changing `analyze` behavior.
- Modify: `pyproject.toml`
  - Declare `reportlab` as the PDF dependency.
- Modify: `TASKLIST.md`
  - Add this implementation phase and update it only as verified tasks complete.
- Create: `docs/verification/2026-07-13-offline-part-drawing-engine.md`
  - Record fixture coverage, exact commands, output audits, and remaining exporter gap.

## Task 1: Define The Snapshot Contract And Parser

**Files:**
- Create: `src/zijinhua_tekla/part_drawing/__init__.py`
- Create: `src/zijinhua_tekla/part_drawing/contracts.py`
- Create: `src/zijinhua_tekla/part_drawing/snapshot_input.py`
- Create: `tests/fixtures/part_drawing/rectangular_plate.json`
- Create: `tests/test_part_drawing_contracts.py`

- [ ] **Step 1: Add the minimal contract fixture**

Create `tests/fixtures/part_drawing/rectangular_plate.json`:

```json
{
  "schemaVersion": "partDrawingSnapshot.v1",
  "exporterVersion": "test-fixture.v1",
  "modelIdentifier": "fixture-model",
  "exportedAt": "2026-07-13T00:00:00Z",
  "part": {
    "partId": "1001",
    "partPosition": "P-1001",
    "assemblyId": "A-1",
    "name": "PLATE",
    "profile": "PL10",
    "material": "Q355B",
    "quantity": 1,
    "thickness": 10.0,
    "localFrame": {
      "origin": [10.0, 20.0, 30.0],
      "xAxis": [1.0, 0.0, 0.0],
      "yAxis": [0.0, 1.0, 0.0],
      "normal": [0.0, 0.0, 1.0]
    },
    "outerLoop": [
      {"kind": "LINE", "start": [10.0, 20.0, 30.0], "end": [210.0, 20.0, 30.0]},
      {"kind": "LINE", "start": [210.0, 20.0, 30.0], "end": [210.0, 120.0, 30.0]},
      {"kind": "LINE", "start": [210.0, 120.0, 30.0], "end": [10.0, 120.0, 30.0]},
      {"kind": "LINE", "start": [10.0, 120.0, 30.0], "end": [10.0, 20.0, 30.0]}
    ],
    "innerLoops": [],
    "holes": [],
    "cuts": [],
    "sourceEvidence": ["TEKLA_SOLID", "TEKLA_PART_POSITION"]
  }
}
```

- [ ] **Step 2: Write failing parser and validation tests**

Create `tests/test_part_drawing_contracts.py`:

```python
import json
import unittest
from dataclasses import replace
from pathlib import Path

from zijinhua_tekla.part_drawing.contracts import LocalFrame, Vector3D
from zijinhua_tekla.part_drawing.snapshot_input import load_part_snapshot, parse_part_snapshot, safe_part_position


FIXTURE = Path(__file__).parent / "fixtures" / "part_drawing" / "rectangular_plate.json"


class PartDrawingContractTests(unittest.TestCase):
    def test_loads_versioned_flat_plate_snapshot(self):
        snapshot = load_part_snapshot(FIXTURE)
        self.assertEqual("partDrawingSnapshot.v1", snapshot.schema_version)
        self.assertEqual("P-1001", snapshot.part_position)
        self.assertEqual(10.0, snapshot.thickness)
        self.assertEqual(4, len(snapshot.outer_loop))

    def test_rejects_missing_part_position(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        data["part"]["partPosition"] = ""
        with self.assertRaisesRegex(ValueError, "partPosition"):
            parse_part_snapshot(data)

    def test_rejects_unknown_schema(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        data["schemaVersion"] = "partDrawingSnapshot.v2"
        with self.assertRaisesRegex(ValueError, "schemaVersion"):
            parse_part_snapshot(data)

    def test_sanitizes_file_name_without_changing_business_position(self):
        self.assertEqual("P_1001_2", safe_part_position("P/1001:2"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the tests and verify the missing-module failure**

Run:

```powershell
python -m unittest tests.test_part_drawing_contracts
```

Expected: `ModuleNotFoundError: No module named 'zijinhua_tekla.part_drawing'`.

- [ ] **Step 4: Implement immutable snapshot DTOs and strict parsing**

Create `src/zijinhua_tekla/part_drawing/contracts.py` with these public DTOs:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DrawingStatus(str, Enum):
    OK = "OK"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"


class IssueCode(str, Enum):
    SNAPSHOT_INVALID = "SNAPSHOT_INVALID"
    PART_POSITION_CONFLICT = "PART_POSITION_CONFLICT"
    GEOMETRY_INVALID = "GEOMETRY_INVALID"
    FEATURE_AMBIGUOUS = "FEATURE_AMBIGUOUS"
    DIMENSION_INCOMPLETE = "DIMENSION_INCOMPLETE"
    LAYOUT_OVERFLOW = "LAYOUT_OVERFLOW"
    NEEDS_DETAIL_VIEW = "NEEDS_DETAIL_VIEW"
    RENDER_FAILED = "RENDER_FAILED"


@dataclass(frozen=True)
class Point3D:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Vector3D:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class LocalFrame:
    origin: Point3D
    x_axis: Vector3D
    y_axis: Vector3D
    normal: Vector3D


@dataclass(frozen=True)
class ContourSegmentSnapshot:
    kind: str
    start: Point3D
    end: Point3D
    center: Point3D | None = None
    clockwise: bool = False


@dataclass(frozen=True)
class HoleSnapshot:
    hole_id: str
    kind: str
    center: Point3D
    diameter: float = 0.0
    length: float = 0.0
    width: float = 0.0
    angle_deg: float = 0.0


@dataclass(frozen=True)
class PartDrawingSnapshot:
    schema_version: str
    exporter_version: str
    model_identifier: str
    exported_at: str
    part_id: str
    part_position: str
    assembly_id: str
    name: str
    profile: str
    material: str
    quantity: int
    thickness: float
    local_frame: LocalFrame
    outer_loop: tuple[ContourSegmentSnapshot, ...]
    inner_loops: tuple[tuple[ContourSegmentSnapshot, ...], ...] = ()
    holes: tuple[HoleSnapshot, ...] = ()
    cuts: tuple[dict[str, Any], ...] = ()
    source_evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class DrawingIssue:
    code: IssueCode
    message: str
    blocking: bool
    part_ids: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
```

Create `src/zijinhua_tekla/part_drawing/snapshot_input.py` with strict helpers `_point`, `_vector`, `_segment`, `_hole`, and these public functions:

```python
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .contracts import ContourSegmentSnapshot, HoleSnapshot, LocalFrame, PartDrawingSnapshot, Point3D, Vector3D


SCHEMA_VERSION = "partDrawingSnapshot.v1"


def load_part_snapshot(path: Path) -> PartDrawingSnapshot:
    return parse_part_snapshot(json.loads(path.read_text(encoding="utf-8")))


def parse_part_snapshot(data: dict[str, Any]) -> PartDrawingSnapshot:
    if data.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError(f"unsupported schemaVersion: {data.get('schemaVersion')!r}")
    part = data.get("part") or {}
    if not str(part.get("partPosition") or "").strip():
        raise ValueError("partPosition is required")
    thickness = float(part.get("thickness") or 0.0)
    if thickness <= 0.0:
        raise ValueError("thickness must be positive")
    frame = part.get("localFrame") or {}
    outer = tuple(_segment(item) for item in part.get("outerLoop") or [])
    if len(outer) < 3:
        raise ValueError("outerLoop requires at least three segments")
    return PartDrawingSnapshot(
        schema_version=SCHEMA_VERSION,
        exporter_version=str(data.get("exporterVersion") or ""),
        model_identifier=str(data.get("modelIdentifier") or ""),
        exported_at=str(data.get("exportedAt") or ""),
        part_id=str(part.get("partId") or ""),
        part_position=str(part["partPosition"]).strip(),
        assembly_id=str(part.get("assemblyId") or ""),
        name=str(part.get("name") or ""),
        profile=str(part.get("profile") or ""),
        material=str(part.get("material") or ""),
        quantity=max(1, int(part.get("quantity") or 1)),
        thickness=thickness,
        local_frame=LocalFrame(
            origin=_point(frame.get("origin")),
            x_axis=_vector(frame.get("xAxis")),
            y_axis=_vector(frame.get("yAxis")),
            normal=_vector(frame.get("normal")),
        ),
        outer_loop=outer,
        inner_loops=tuple(tuple(_segment(segment) for segment in loop) for loop in part.get("innerLoops") or []),
        holes=tuple(_hole(item) for item in part.get("holes") or []),
        cuts=tuple(part.get("cuts") or []),
        source_evidence=tuple(str(item) for item in part.get("sourceEvidence") or []),
    )


def safe_part_position(value: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value).strip(" .")
    return safe or "unnamed-part"


def _point(value: Any) -> Point3D:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("3D point requires three coordinates")
    return Point3D(*(float(item) for item in value))


def _vector(value: Any) -> Vector3D:
    point = _point(value)
    return Vector3D(point.x, point.y, point.z)


def _segment(data: dict[str, Any]) -> ContourSegmentSnapshot:
    kind = str(data.get("kind") or "").upper()
    if kind not in {"LINE", "ARC"}:
        raise ValueError(f"unsupported contour segment kind: {kind!r}")
    return ContourSegmentSnapshot(
        kind=kind,
        start=_point(data.get("start")),
        end=_point(data.get("end")),
        center=_point(data["center"]) if data.get("center") is not None else None,
        clockwise=bool(data.get("clockwise", False)),
    )


def _hole(data: dict[str, Any]) -> HoleSnapshot:
    return HoleSnapshot(
        hole_id=str(data.get("holeId") or ""),
        kind=str(data.get("kind") or "ROUND").upper(),
        center=_point(data.get("center")),
        diameter=float(data.get("diameter") or 0.0),
        length=float(data.get("length") or 0.0),
        width=float(data.get("width") or 0.0),
        angle_deg=float(data.get("angleDeg") or 0.0),
    )
```

Create `src/zijinhua_tekla/part_drawing/__init__.py` exporting `PartDrawingSnapshot`, `DrawingStatus`, and `load_part_snapshot`.

- [ ] **Step 5: Run the contract tests**

Run: `python -m unittest tests.test_part_drawing_contracts`

Expected: `Ran 4 tests ... OK`.

- [ ] **Step 6: Commit the contract slice**

```powershell
git add src/zijinhua_tekla/part_drawing tests/fixtures/part_drawing tests/test_part_drawing_contracts.py
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode staged
git diff --cached --check
git commit -m "feat: define part drawing snapshot contract"
```

## Task 2: Normalize And Validate Plate Geometry

**Files:**
- Create: `src/zijinhua_tekla/part_drawing/geometry_analyzer.py`
- Create: `tests/test_part_drawing_geometry.py`

- [ ] **Step 1: Write failing projection and topology tests**

Create `tests/test_part_drawing_geometry.py` with tests that load the rectangular fixture and assert:

```python
import unittest
from pathlib import Path

from zijinhua_tekla.part_drawing.geometry_analyzer import analyze_plate_geometry
from zijinhua_tekla.part_drawing.snapshot_input import load_part_snapshot


FIXTURE = Path(__file__).parent / "fixtures" / "part_drawing" / "rectangular_plate.json"


class PartDrawingGeometryTests(unittest.TestCase):
    def test_projects_model_points_to_normalized_plate_coordinates(self):
        result = analyze_plate_geometry(load_part_snapshot(FIXTURE))
        self.assertFalse(result.issues)
        self.assertEqual((0.0, 0.0, 200.0, 100.0), result.geometry.bounds)
        self.assertAlmostEqual(20000.0, result.geometry.area)

    def test_rejects_open_outer_loop(self):
        snapshot = load_part_snapshot(FIXTURE)
        broken = replace(snapshot, outer_loop=snapshot.outer_loop[:-1])
        result = analyze_plate_geometry(broken)
        self.assertIsNone(result.geometry)
        self.assertTrue(any(issue.code.value == "GEOMETRY_INVALID" for issue in result.issues))

    def test_fingerprint_is_translation_and_rotation_independent(self):
        result = analyze_plate_geometry(load_part_snapshot(FIXTURE))
        self.assertEqual(64, len(result.geometry.fingerprint))

    def test_rejects_non_orthonormal_local_frame(self):
        snapshot = load_part_snapshot(FIXTURE)
        invalid_frame = LocalFrame(
            snapshot.local_frame.origin,
            Vector3D(1.0, 0.0, 0.0),
            Vector3D(1.0, 0.0, 0.0),
            Vector3D(0.0, 0.0, 1.0),
        )
        result = analyze_plate_geometry(replace(snapshot, local_frame=invalid_frame))
        self.assertIsNone(result.geometry)
        self.assertTrue(any("orthonormal" in issue.message for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the geometry tests and verify failure**

Run: `python -m unittest tests.test_part_drawing_geometry`

Expected: missing `geometry_analyzer` module.

- [ ] **Step 3: Implement geometry projection and validation**

Create `geometry_analyzer.py` with immutable `Point2D`, `NormalizedSegment`, `NormalizedPlateGeometry`, and `GeometryAnalysisResult` DTOs. Implement:

```python
def project_point(point: Point3D, frame: LocalFrame) -> Point2D:
    delta = (point.x - frame.origin.x, point.y - frame.origin.y, point.z - frame.origin.z)
    return Point2D(
        round(delta[0] * frame.x_axis.x + delta[1] * frame.x_axis.y + delta[2] * frame.x_axis.z, 6),
        round(delta[0] * frame.y_axis.x + delta[1] * frame.y_axis.y + delta[2] * frame.y_axis.z, 6),
    )


def analyze_plate_geometry(snapshot: PartDrawingSnapshot) -> GeometryAnalysisResult:
    frame_error = _validate_orthonormal_frame(snapshot.local_frame, tolerance=1e-6)
    if frame_error:
        return GeometryAnalysisResult(None, (DrawingIssue(IssueCode.GEOMETRY_INVALID, frame_error, True, (snapshot.part_id,)),))
    planarity_error = _validate_planarity(snapshot, tolerance_mm=0.1)
    if planarity_error:
        return GeometryAnalysisResult(None, (DrawingIssue(IssueCode.GEOMETRY_INVALID, planarity_error, True, (snapshot.part_id,)),))
    projected_outer = tuple(_project_segment(item, snapshot.local_frame) for item in snapshot.outer_loop)
    projected_inner = tuple(
        tuple(_project_segment(item, snapshot.local_frame) for item in loop)
        for loop in snapshot.inner_loops
    )
    continuity_errors = _loop_continuity_errors(projected_outer, tolerance=0.01)
    continuity_errors += sum((_loop_continuity_errors(loop, 0.01) for loop in projected_inner), [])
    if continuity_errors:
        return GeometryAnalysisResult(
            geometry=None,
            issues=(DrawingIssue(IssueCode.GEOMETRY_INVALID, "; ".join(continuity_errors), True, (snapshot.part_id,)),),
        )
    outer_points = _sample_loop(projected_outer, chord_tolerance=0.05)
    inner_points = tuple(_sample_loop(loop, 0.05) for loop in projected_inner)
    polygon = Polygon([(point.x, point.y) for point in outer_points], [[(point.x, point.y) for point in loop] for loop in inner_points])
    if not polygon.is_valid or polygon.area <= 0.0:
        reason = explain_validity(polygon)
        return GeometryAnalysisResult(None, (DrawingIssue(IssueCode.GEOMETRY_INVALID, reason, True, (snapshot.part_id,)),))
    min_x, min_y, max_x, max_y = polygon.bounds
    normalized_outer = _translate_loop(projected_outer, -min_x, -min_y)
    normalized_inner = tuple(_translate_loop(loop, -min_x, -min_y) for loop in projected_inner)
    fingerprint = _canonical_fingerprint(normalized_outer, normalized_inner, snapshot.thickness)
    return GeometryAnalysisResult(
        NormalizedPlateGeometry(
            outer_loop=normalized_outer,
            inner_loops=normalized_inner,
            thickness=snapshot.thickness,
            normalization_offset=Point2D(min_x, min_y),
            bounds=(0.0, 0.0, round(max_x - min_x, 6), round(max_y - min_y, 6)),
            area=float(polygon.area),
            perimeter=float(polygon.length),
            fingerprint=fingerprint,
        ),
        (),
    )
```

`NormalizedPlateGeometry` must include `normalization_offset: Point2D`; all later operation coordinates subtract this offset after projection. Implement `_project_segment` for `LINE` and `ARC`, `_sample_loop` using angle steps derived from `0.05 mm` chord tolerance, `_loop_continuity_errors`, and `_canonical_fingerprint`. The fingerprint must serialize rounded segment geometry for all eight XY rotations/reflections, normalize each candidate to `(0, 0)`, and hash the lexicographically smallest serialization with SHA-256. Preserve segment kinds and arc radius/clockwise state in the serialization.

- [ ] **Step 4: Add explicit rotated-fixture coverage**

Extend `test_fingerprint_is_translation_and_rotation_independent` by creating a second snapshot whose frame swaps X/Y and whose model points are rotated 90 degrees. Assert both analyses return the same fingerprint. This test must fail before completing the eight-transform canonicalizer and pass afterward.

- [ ] **Step 5: Run geometry and contract tests**

Run:

```powershell
python -m unittest tests.test_part_drawing_contracts tests.test_part_drawing_geometry
```

Expected: command exits `0` with zero failures and zero errors; output includes all contract and geometry tests, including the rotated fingerprint case.

- [ ] **Step 6: Commit geometry analysis**

```powershell
git add src/zijinhua_tekla/part_drawing/geometry_analyzer.py tests/test_part_drawing_geometry.py
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode staged
git diff --cached --check
git commit -m "feat: normalize flat plate geometry"
```

## Task 3: Enforce Same-Position Quality Rules

**Files:**
- Create: `src/zijinhua_tekla/part_drawing/quality.py`
- Create: `tests/test_part_drawing_quality.py`

- [ ] **Step 1: Write failing grouping tests**

Create tests for identical, translated/rotated, and conflicting entities:

```python
from dataclasses import replace
import unittest
from pathlib import Path

from zijinhua_tekla.part_drawing.contracts import HoleSnapshot, Point3D
from zijinhua_tekla.part_drawing.quality import group_part_snapshots
from zijinhua_tekla.part_drawing.snapshot_input import load_part_snapshot


FIXTURE = Path(__file__).parent / "fixtures" / "part_drawing" / "rectangular_plate.json"


class PartDrawingQualityTests(unittest.TestCase):
    def snapshot(self, part_id: str, position: str = "P-1001", thickness: float = 10.0):
        return replace(
            load_part_snapshot(FIXTURE),
            part_id=part_id,
            part_position=position,
            thickness=thickness,
        )

    def test_groups_equal_geometry_and_counts_entities(self):
        group = group_part_snapshots([self.snapshot("1"), self.snapshot("2")])[0]
        self.assertEqual("OK", group.status.value)
        self.assertEqual(2, group.quantity)
        self.assertFalse(group.issues)

    def test_rejects_same_position_with_different_thickness(self):
        first = self.snapshot("1", thickness=10.0)
        second = self.snapshot("2", thickness=12.0)
        group = group_part_snapshots([first, second])[0]
        self.assertEqual("REJECTED", group.status.value)
        self.assertEqual("PART_POSITION_CONFLICT", group.issues[0].code.value)

    def test_never_merges_different_part_positions(self):
        groups = group_part_snapshots([self.snapshot("1", position="P1"), self.snapshot("2", position="P2")])
        self.assertEqual(2, len(groups))

    def test_rejects_same_position_with_different_holes(self):
        first = replace(
            self.snapshot("1"),
            holes=(HoleSnapshot("H1", "ROUND", Point3D(60.0, 70.0, 30.0), diameter=22.0),),
        )
        second = replace(
            self.snapshot("2"),
            holes=(HoleSnapshot("H1", "ROUND", Point3D(80.0, 70.0, 30.0), diameter=22.0),),
        )
        group = group_part_snapshots([first, second])[0]
        self.assertEqual("REJECTED", group.status.value)
        self.assertEqual("PART_POSITION_CONFLICT", group.issues[0].code.value)
```

- [ ] **Step 2: Run and verify the missing quality module**

Run: `python -m unittest tests.test_part_drawing_quality`

Expected: missing `quality` module.

- [ ] **Step 3: Implement group status aggregation**

Create `quality.py`:

```python
from dataclasses import dataclass

from .contracts import DrawingIssue, DrawingStatus, IssueCode, PartDrawingSnapshot
from .geometry_analyzer import NormalizedPlateGeometry, analyze_plate_geometry


@dataclass(frozen=True)
class PartPositionGroup:
    part_position: str
    snapshots: tuple[PartDrawingSnapshot, ...]
    representative: PartDrawingSnapshot
    geometry: NormalizedPlateGeometry | None
    quantity: int
    status: DrawingStatus
    issues: tuple[DrawingIssue, ...]


def group_part_snapshots(snapshots: list[PartDrawingSnapshot]) -> list[PartPositionGroup]:
    by_position: dict[str, list[PartDrawingSnapshot]] = {}
    for snapshot in snapshots:
        by_position.setdefault(snapshot.part_position, []).append(snapshot)
    return [_build_group(position, items) for position, items in sorted(by_position.items())]


def _build_group(position: str, snapshots: list[PartDrawingSnapshot]) -> PartPositionGroup:
    analyses = [analyze_plate_geometry(snapshot) for snapshot in snapshots]
    geometry_issues = tuple(issue for analysis in analyses for issue in analysis.issues)
    geometries = [analysis.geometry for analysis in analyses if analysis.geometry is not None]
    quantity = sum(snapshot.quantity for snapshot in snapshots)
    if geometry_issues or len(geometries) != len(snapshots):
        return PartPositionGroup(position, tuple(snapshots), snapshots[0], None, quantity, DrawingStatus.REJECTED, geometry_issues)
    fingerprints = {
        _manufacturing_fingerprint(snapshot, geometry)
        for snapshot, geometry in zip(snapshots, geometries)
    }
    if len(fingerprints) != 1:
        issue = DrawingIssue(
            IssueCode.PART_POSITION_CONFLICT,
            f"partPosition {position} contains {len(fingerprints)} geometry fingerprints",
            True,
            tuple(snapshot.part_id for snapshot in snapshots),
            tuple(sorted(fingerprints)),
        )
        return PartPositionGroup(position, tuple(snapshots), snapshots[0], None, quantity, DrawingStatus.REJECTED, (issue,))
    return PartPositionGroup(position, tuple(snapshots), snapshots[0], geometries[0], quantity, DrawingStatus.OK, ())
```

Implement `_manufacturing_fingerprint` by applying the same eight XY rotation/reflection candidates to both contour geometry and operation coordinates, serializing the combined candidate, and hashing the lexicographically smallest serialization with SHA-256. Each hole/slot descriptor must include kind, transformed center, diameter/length/width/transformed angle; each cut descriptor must use stable JSON key ordering. Project operation centers through the snapshot frame and subtract `geometry.normalization_offset` before candidate transforms. This preserves rotation equivalence while making different holes, slots, cuts, and thickness blocking conflicts even when the outer contour is identical.

- [ ] **Step 4: Run quality and geometry tests**

Run: `python -m unittest tests.test_part_drawing_geometry tests.test_part_drawing_quality`

Expected: all tests pass.

- [ ] **Step 5: Commit the quality gate**

```powershell
git add src/zijinhua_tekla/part_drawing/quality.py tests/test_part_drawing_quality.py
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode staged
git diff --cached --check
git commit -m "feat: gate conflicting part positions"
```

## Task 4: Recognize Plate Features

**Files:**
- Create: `src/zijinhua_tekla/part_drawing/feature_recognizer.py`
- Create: `tests/test_part_drawing_features.py`

- [ ] **Step 1: Write failing feature tests**

Create `tests/test_part_drawing_features.py` with explicit round holes, slots, and one ambiguous arc loop:

```python
from dataclasses import replace
import unittest
from pathlib import Path

from zijinhua_tekla.part_drawing.contracts import ContourSegmentSnapshot, HoleSnapshot, Point3D
from zijinhua_tekla.part_drawing.feature_recognizer import recognize_plate_features
from zijinhua_tekla.part_drawing.geometry_analyzer import analyze_plate_geometry
from zijinhua_tekla.part_drawing.snapshot_input import load_part_snapshot


FIXTURE = Path(__file__).parent / "fixtures" / "part_drawing" / "rectangular_plate.json"


class PartDrawingFeatureTests(unittest.TestCase):
    def setUp(self):
        self.base = load_part_snapshot(FIXTURE)

    def recognize(self, snapshot):
        analysis = analyze_plate_geometry(snapshot)
        self.assertIsNotNone(analysis.geometry)
        return recognize_plate_features(snapshot, analysis.geometry)

    def round_hole(self, hole_id: str, x: float, y: float) -> HoleSnapshot:
        return HoleSnapshot(hole_id, "ROUND", Point3D(x, y, 30.0), diameter=22.0)

    def line_loop(self, xy_points):
        points = [Point3D(x, y, 30.0) for x, y in xy_points]
        return tuple(
            ContourSegmentSnapshot("LINE", start, end)
            for start, end in zip(points, points[1:] + points[:1])
        )

    def test_recognizes_explicit_round_hole_and_slot(self):
        snapshot = replace(
            self.base,
            holes=(
                self.round_hole("H1", 60.0, 70.0),
                HoleSnapshot("S1", "SLOT", Point3D(150.0, 70.0, 30.0), length=40.0, width=18.0),
            ),
        )
        result = self.recognize(snapshot)
        self.assertEqual(["ROUND_HOLE", "SLOT"], [feature.feature_type.value for feature in result.features])
        self.assertEqual(22.0, result.features[0].parameters["diameter"])
        self.assertEqual((40.0, 18.0), (result.features[1].parameters["length"], result.features[1].parameters["width"]))

    def test_groups_equal_round_holes_on_one_axis(self):
        snapshot = replace(
            self.base,
            holes=(
                self.round_hole("H1", 60.0, 70.0),
                self.round_hole("H2", 110.0, 70.0),
                self.round_hole("H3", 160.0, 70.0),
            ),
        )
        result = self.recognize(snapshot)
        groups = [feature for feature in result.features if feature.feature_type.value == "HOLE_GROUP"]
        self.assertEqual(1, len(groups))
        self.assertEqual(3, groups[0].parameters["count"])
        self.assertEqual(50.0, groups[0].parameters["spacing"])

    def test_marks_unexplained_inner_arc_loop_for_review(self):
        arc_loop = (
            ContourSegmentSnapshot(
                "ARC",
                Point3D(80.0, 60.0, 30.0),
                Point3D(100.0, 80.0, 30.0),
                center=Point3D(80.0, 80.0, 30.0),
            ),
            ContourSegmentSnapshot(
                "ARC",
                Point3D(100.0, 80.0, 30.0),
                Point3D(80.0, 60.0, 30.0),
                center=Point3D(100.0, 60.0, 30.0),
            ),
        )
        result = self.recognize(replace(self.base, inner_loops=(arc_loop,)))
        self.assertEqual("REVIEW_REQUIRED", result.status.value)
        self.assertTrue(any(issue.code.value == "FEATURE_AMBIGUOUS" for issue in result.issues))

    def test_recognizes_polygon_cutout(self):
        loop = self.line_loop(((80.0, 55.0), (120.0, 55.0), (120.0, 85.0), (80.0, 85.0)))
        result = self.recognize(replace(self.base, inner_loops=(loop,)))
        self.assertIn("POLYGON_CUTOUT", [feature.feature_type.value for feature in result.features])

    def test_recognizes_chamfer_and_notch_without_inferring_bevel(self):
        chamfer = self.line_loop(((10.0, 20.0), (190.0, 20.0), (210.0, 40.0), (210.0, 120.0), (10.0, 120.0)))
        notch = self.line_loop(((10.0, 20.0), (90.0, 20.0), (90.0, 40.0), (130.0, 40.0), (130.0, 20.0), (210.0, 20.0), (210.0, 120.0), (10.0, 120.0)))
        chamfer_types = [feature.feature_type.value for feature in self.recognize(replace(self.base, outer_loop=chamfer)).features]
        notch_types = [feature.feature_type.value for feature in self.recognize(replace(self.base, outer_loop=notch)).features]
        self.assertIn("CHAMFER", chamfer_types)
        self.assertIn("NOTCH", notch_types)
        self.assertNotIn("BEVEL", chamfer_types + notch_types)

    def test_recognizes_consistent_arc_cutout(self):
        center = Point3D(110.0, 70.0, 30.0)
        loop = (
            ContourSegmentSnapshot("ARC", Point3D(90.0, 70.0, 30.0), Point3D(130.0, 70.0, 30.0), center=center),
            ContourSegmentSnapshot("ARC", Point3D(130.0, 70.0, 30.0), Point3D(90.0, 70.0, 30.0), center=center),
        )
        result = self.recognize(replace(self.base, inner_loops=(loop,)))
        self.assertIn("ARC_CUTOUT", [feature.feature_type.value for feature in result.features])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m unittest tests.test_part_drawing_features`

Expected: missing `feature_recognizer` module.

- [ ] **Step 3: Implement feature DTOs and recognizer**

Create `feature_recognizer.py`:

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .contracts import DrawingIssue, DrawingStatus, IssueCode, PartDrawingSnapshot
from .geometry_analyzer import NormalizedPlateGeometry, Point2D, project_point


class FeatureType(str, Enum):
    ROUND_HOLE = "ROUND_HOLE"
    HOLE_GROUP = "HOLE_GROUP"
    SLOT = "SLOT"
    POLYGON_CUTOUT = "POLYGON_CUTOUT"
    CHAMFER = "CHAMFER"
    NOTCH = "NOTCH"
    ARC_CUTOUT = "ARC_CUTOUT"
    BEVEL = "BEVEL"


@dataclass(frozen=True)
class RecognizedFeature:
    feature_id: str
    feature_type: FeatureType
    anchors: tuple[Point2D, ...]
    parameters: dict[str, Any]
    source_ids: tuple[str, ...]
    evidence_codes: tuple[str, ...]
    confidence: float


@dataclass(frozen=True)
class FeatureRecognitionResult:
    features: tuple[RecognizedFeature, ...]
    status: DrawingStatus
    issues: tuple[DrawingIssue, ...]


def recognize_plate_features(snapshot: PartDrawingSnapshot, geometry: NormalizedPlateGeometry) -> FeatureRecognitionResult:
    features = [_explicit_hole_feature(snapshot, hole) for hole in snapshot.holes]
    features.extend(_hole_groups(features))
    inner_features, inner_issues = _inner_loop_features(geometry.inner_loops)
    outer_features = _outer_contour_features(geometry)
    features.extend(inner_features)
    features.extend(outer_features)
    status = DrawingStatus.REVIEW_REQUIRED if inner_issues else DrawingStatus.OK
    return FeatureRecognitionResult(tuple(features), status, tuple(inner_issues))
```

For explicit hole/slot anchors, first call `project_point(hole.center, snapshot.local_frame)`, then subtract `geometry.normalization_offset`. Do not use raw model XYZ or unshifted projected coordinates in any feature or dimension intent.

Implement these deterministic rules:

- Explicit `ROUND` hole with positive diameter becomes `ROUND_HOLE` using `TEKLA_HOLE_OPERATION`.
- Explicit `SLOT` with positive length/width becomes `SLOT` using `TEKLA_SLOT_OPERATION`.
- Three or more equal round holes on a common axis with equal spacing create one additional `HOLE_GROUP`; retain individual holes for geometry.
- Closed inner loop containing only lines becomes `POLYGON_CUTOUT`.
- Closed inner loop containing arcs becomes `ARC_CUTOUT` only when all arcs share a valid center/radius chain; otherwise add `FEATURE_AMBIGUOUS`.
- Outer vertices missing from the bounding rectangle become `CHAMFER` when one diagonal connects adjacent bounding edges, otherwise `NOTCH`.
- Create `BEVEL` only from explicit cut evidence with `operationType == "BEVEL"`; never infer it from a diagonal outline edge.

- [ ] **Step 4: Run feature tests with prior layers**

Run: `python -m unittest tests.test_part_drawing_contracts tests.test_part_drawing_geometry tests.test_part_drawing_features`

Expected: all tests pass.

- [ ] **Step 5: Commit feature recognition**

```powershell
git add src/zijinhua_tekla/part_drawing/feature_recognizer.py tests/test_part_drawing_features.py
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode staged
git diff --cached --check
git commit -m "feat: recognize flat plate features"
```

## Task 5: Generate Non-Redundant Dimension Intents

**Files:**
- Create: `src/zijinhua_tekla/part_drawing/dimension_generator.py`
- Create: `tests/test_part_drawing_dimensions.py`

- [ ] **Step 1: Write failing intent tests**

Cover overall dimensions, hole coordinates, grouped holes, slots, radii, and review propagation:

```python
from dataclasses import replace
import unittest
from pathlib import Path

from zijinhua_tekla.part_drawing.contracts import HoleSnapshot, Point3D
from zijinhua_tekla.part_drawing.dimension_generator import generate_dimension_intents
from zijinhua_tekla.part_drawing.feature_recognizer import FeatureType, RecognizedFeature, recognize_plate_features
from zijinhua_tekla.part_drawing.geometry_analyzer import Point2D, analyze_plate_geometry
from zijinhua_tekla.part_drawing.snapshot_input import load_part_snapshot


FIXTURE = Path(__file__).parent / "fixtures" / "part_drawing" / "rectangular_plate.json"


class PartDrawingDimensionTests(unittest.TestCase):
    def setUp(self):
        base = load_part_snapshot(FIXTURE)
        holes = tuple(
            HoleSnapshot(f"H{index + 1}", "ROUND", Point3D(x, 70.0, 30.0), diameter=22.0)
            for index, x in enumerate((60.0, 110.0, 160.0))
        )
        self.snapshot = replace(base, holes=holes)
        self.geometry = analyze_plate_geometry(self.snapshot).geometry
        self.features = recognize_plate_features(self.snapshot, self.geometry).features
        self.round_hole = next(feature for feature in self.features if feature.feature_type == FeatureType.ROUND_HOLE)
        self.group_features = self.features

    def test_generates_required_overall_and_thickness_dimensions(self):
        result = generate_dimension_intents(self.snapshot, self.geometry, ())
        by_id = {intent.intent_id: intent for intent in result.intents}
        self.assertEqual(200.0, by_id["overall-x"].model_value)
        self.assertEqual(100.0, by_id["overall-y"].model_value)
        self.assertEqual(10.0, by_id["thickness"].model_value)

    def test_round_hole_uses_diameter_and_two_datum_coordinates(self):
        result = generate_dimension_intents(self.snapshot, self.geometry, (self.round_hole,))
        ids = {intent.intent_id for intent in result.intents}
        self.assertTrue({"hole-H1-dia", "hole-H1-x", "hole-H1-y"}.issubset(ids))

    def test_hole_group_uses_first_hole_spacing_and_count(self):
        result = generate_dimension_intents(self.snapshot, self.geometry, self.group_features)
        texts = {intent.text for intent in result.intents}
        self.assertIn("3xØ22 @50", texts)

    def test_generates_slot_and_arc_cutout_dimensions(self):
        slot = RecognizedFeature(
            "S1", FeatureType.SLOT, (Point2D(100.0, 50.0),),
            {"length": 40.0, "width": 18.0, "angle_deg": 0.0},
            ("S1",), ("TEKLA_SLOT_OPERATION",), 1.0,
        )
        arc = RecognizedFeature(
            "A1", FeatureType.ARC_CUTOUT, (Point2D(40.0, 40.0),),
            {"radius": 20.0}, ("A1",), ("CLOSED_ARC_LOOP",), 1.0,
        )
        result = generate_dimension_intents(self.snapshot, self.geometry, (slot, arc))
        kinds = {intent.kind.value for intent in result.intents}
        self.assertTrue({"LENGTH", "WIDTH", "RADIUS"}.issubset(kinds))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m unittest tests.test_part_drawing_dimensions`

Expected: missing `dimension_generator` module.

- [ ] **Step 3: Implement intent generation**

Create `dimension_generator.py` with:

```python
from dataclasses import dataclass
from enum import Enum

from .contracts import DrawingIssue, DrawingStatus, IssueCode, PartDrawingSnapshot
from .feature_recognizer import FeatureType, RecognizedFeature
from .geometry_analyzer import NormalizedPlateGeometry, Point2D


class DimensionKind(str, Enum):
    OVERALL = "OVERALL"
    THICKNESS = "THICKNESS"
    DIAMETER = "DIAMETER"
    RADIUS = "RADIUS"
    DATUM_X = "DATUM_X"
    DATUM_Y = "DATUM_Y"
    LENGTH = "LENGTH"
    WIDTH = "WIDTH"
    PATTERN = "PATTERN"
    WARNING = "WARNING"


@dataclass(frozen=True)
class DimensionIntent:
    intent_id: str
    kind: DimensionKind
    priority: int
    text: str
    model_value: float | None
    anchors: tuple[Point2D, ...]
    source_feature_ids: tuple[str, ...]
    evidence_codes: tuple[str, ...]
    preferred_band: str


@dataclass(frozen=True)
class DimensionGenerationResult:
    intents: tuple[DimensionIntent, ...]
    status: DrawingStatus
    issues: tuple[DrawingIssue, ...]


def generate_dimension_intents(
    snapshot: PartDrawingSnapshot,
    geometry: NormalizedPlateGeometry,
    features: tuple[RecognizedFeature, ...],
) -> DimensionGenerationResult:
    _, _, width, height = geometry.bounds
    intents = [
        _intent("overall-x", DimensionKind.OVERALL, 100, _number(width), width, ((0.0, 0.0), (width, 0.0)), (), "top", ("NORMALIZED_BOUNDS",)),
        _intent("overall-y", DimensionKind.OVERALL, 100, _number(height), height, ((0.0, 0.0), (0.0, height)), (), "right", ("NORMALIZED_BOUNDS",)),
        _intent("thickness", DimensionKind.THICKNESS, 95, f"t={_number(snapshot.thickness)}", snapshot.thickness, (), (), "note", ("TEKLA_PART_THICKNESS",)),
    ]
    issues: list[DrawingIssue] = []
    grouped_hole_ids = {source_id for feature in features if feature.feature_type == FeatureType.HOLE_GROUP for source_id in feature.source_ids}
    for feature in features:
        if feature.feature_type == FeatureType.ROUND_HOLE and feature.feature_id not in grouped_hole_ids:
            intents.extend(_round_hole_intents(feature))
        elif feature.feature_type == FeatureType.HOLE_GROUP:
            intents.extend(_hole_group_intents(feature))
        elif feature.feature_type == FeatureType.SLOT:
            intents.extend(_slot_intents(feature))
        elif feature.feature_type in {FeatureType.CHAMFER, FeatureType.NOTCH, FeatureType.POLYGON_CUTOUT}:
            intents.extend(_linear_feature_intents(feature))
        elif feature.feature_type == FeatureType.ARC_CUTOUT:
            intents.extend(_arc_feature_intents(feature))
        elif feature.feature_type == FeatureType.BEVEL:
            issues.append(DrawingIssue(IssueCode.DIMENSION_INCOMPLETE, "bevel annotation requires explicit angle and depth", False, (snapshot.part_id,), feature.evidence_codes))
    status = DrawingStatus.REVIEW_REQUIRED if issues else DrawingStatus.OK
    return DimensionGenerationResult(tuple(_deduplicate_intents(intents)), status, tuple(issues))
```

Implement `_intent` to convert `(x, y)` tuples into `Point2D`, `_number` with at most three decimals, feature-specific helpers, and `_deduplicate_intents` keyed by `(kind, rounded model value, rounded anchors, source feature ids)`. Overall dimensions always remain outermost and no helper may emit a second overall width/height intent.

- [ ] **Step 4: Run dimension and feature tests**

Run: `python -m unittest tests.test_part_drawing_features tests.test_part_drawing_dimensions`

Expected: all tests pass.

- [ ] **Step 5: Commit dimension generation**

```powershell
git add src/zijinhua_tekla/part_drawing/dimension_generator.py tests/test_part_drawing_dimensions.py
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode staged
git diff --cached --check
git commit -m "feat: generate plate dimension intents"
```

## Task 6: Optimize Dimension Layout

**Files:**
- Create: `src/zijinhua_tekla/part_drawing/dimension_optimizer.py`
- Create: `tests/test_part_drawing_layout.py`

- [ ] **Step 1: Write failing layout tests**

Create tests for standard scale selection, collision-free rectangle layout, and dense overflow:

```python
from dataclasses import replace
import unittest
from pathlib import Path

from zijinhua_tekla.part_drawing.dimension_generator import generate_dimension_intents
from zijinhua_tekla.part_drawing.dimension_optimizer import optimize_dimension_layout
from zijinhua_tekla.part_drawing.geometry_analyzer import analyze_plate_geometry
from zijinhua_tekla.part_drawing.snapshot_input import load_part_snapshot


FIXTURE = Path(__file__).parent / "fixtures" / "part_drawing" / "rectangular_plate.json"


class PartDrawingLayoutTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = load_part_snapshot(FIXTURE)
        self.geometry = analyze_plate_geometry(self.snapshot).geometry
        self.intents = generate_dimension_intents(self.snapshot, self.geometry, ()).intents

    def test_places_rectangle_dimensions_without_collision(self):
        layout = optimize_dimension_layout(self.snapshot, self.geometry, self.intents, quantity=2)
        self.assertEqual("OK", layout.status.value)
        self.assertEqual(0, layout.collision_count)
        self.assertFalse(layout.unplaced_intents)
        self.assertIn(layout.scale, (1.0, 0.5, 0.2, 0.1, 0.05))

    def test_dense_intents_request_review_instead_of_overlap(self):
        dense = tuple(replace(self.intents[0], intent_id=f"dense-{index}", text=str(index)) for index in range(80))
        layout = optimize_dimension_layout(self.snapshot, self.geometry, dense, quantity=1)
        self.assertEqual("REVIEW_REQUIRED", layout.status.value)
        self.assertGreater(len(layout.unplaced_intents), 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m unittest tests.test_part_drawing_layout`

Expected: missing `dimension_optimizer` module.

- [ ] **Step 3: Implement deterministic page layout**

Create `dimension_optimizer.py` defining `DrawingLine`, `DrawingArc`, `DrawingCircle`, `DrawingText`, `DrawingRect`, and `PartDrawingLayout`. Use A3 landscape coordinates in millimetres:

```python
PAGE_WIDTH = 420.0
PAGE_HEIGHT = 297.0
MARGIN = 12.0
TITLE_HEIGHT = 55.0
STANDARD_SCALES = (1.0, 0.5, 0.2, 0.1, 0.05)


def optimize_dimension_layout(snapshot, geometry, intents, quantity):
    view_rect = DrawingRect(MARGIN + 35.0, MARGIN + 35.0, PAGE_WIDTH - MARGIN - 65.0, PAGE_HEIGHT - TITLE_HEIGHT - MARGIN - 35.0)
    scale = _fit_scale(geometry.bounds[2], geometry.bounds[3], view_rect)
    transform = _centered_transform(geometry.bounds, view_rect, scale)
    contour_obstacles = (_transform_bounds(geometry.bounds, transform),)
    placed_lines = []
    placed_texts = []
    unplaced = []
    band_counts = {"top": 0, "bottom": 0, "left": 0, "right": 0, "note": 0}
    for intent in sorted(intents, key=lambda item: (-item.priority, item.intent_id)):
        candidate = _place_intent(intent, transform, view_rect, band_counts)
        if candidate is None or _candidate_collides(candidate, contour_obstacles, placed_texts):
            unplaced.append(intent)
            continue
        placed_lines.extend(candidate.lines)
        placed_texts.extend(candidate.texts)
        band_counts[intent.preferred_band] += 1
    collision_count = _count_text_collisions(placed_texts)
    status = DrawingStatus.REVIEW_REQUIRED if unplaced or collision_count else DrawingStatus.OK
    return PartDrawingLayout(
        page_width=PAGE_WIDTH,
        page_height=PAGE_HEIGHT,
        scale=scale,
        view_rect=view_rect,
        model_transform=transform,
        annotation_lines=tuple(placed_lines),
        annotation_texts=tuple(placed_texts),
        title_fields=_title_fields(snapshot, quantity, scale),
        status=status,
        collision_count=collision_count,
        unplaced_intents=tuple(unplaced),
    )
```

Implement `_fit_scale`, `_centered_transform`, overall/datum/diameter/radius/pattern/note placement, text width estimation using the existing mixed ASCII/CJK logic from `reports/annotation_layout.py`, and strict page-bound checks. Do not modify the existing BOX annotation layout in this task.

- [ ] **Step 4: Run layout and dimension tests**

Run: `python -m unittest tests.test_part_drawing_dimensions tests.test_part_drawing_layout`

Expected: all tests pass.

- [ ] **Step 5: Commit layout optimization**

```powershell
git add src/zijinhua_tekla/part_drawing/dimension_optimizer.py tests/test_part_drawing_layout.py
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode staged
git diff --cached --check
git commit -m "feat: lay out flat plate dimensions"
```

## Task 7: Render The Shared Document To DXF And PDF

**Files:**
- Create: `src/zijinhua_tekla/part_drawing/drawing_output.py`
- Create: `tests/test_part_drawing_output.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Declare vector PDF and readback dependencies**

Add `"reportlab",` and `"pypdf",` to `[project].dependencies` in `pyproject.toml`.

Run `python -m pip install -e .` and require exit code `0` before running output tests. If dependency download is blocked by the sandbox, request network escalation rather than changing the design or vendoring packages.

- [ ] **Step 2: Write failing shared-output tests**

Create `tests/test_part_drawing_output.py`:

```python
from dataclasses import replace
import json
import tempfile
import unittest
from pathlib import Path

import ezdxf
from pypdf import PdfReader

from zijinhua_tekla.part_drawing.contracts import DrawingStatus, HoleSnapshot, Point3D
from zijinhua_tekla.part_drawing.dimension_generator import generate_dimension_intents
from zijinhua_tekla.part_drawing.dimension_optimizer import optimize_dimension_layout
from zijinhua_tekla.part_drawing.drawing_output import PartDrawingRenderError, build_part_drawing_document, render_part_drawing
from zijinhua_tekla.part_drawing.feature_recognizer import recognize_plate_features
from zijinhua_tekla.part_drawing.geometry_analyzer import analyze_plate_geometry
from zijinhua_tekla.part_drawing.snapshot_input import load_part_snapshot


FIXTURE = Path(__file__).parent / "fixtures" / "part_drawing" / "rectangular_plate.json"


class PartDrawingOutputTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = load_part_snapshot(FIXTURE)
        self.geometry = analyze_plate_geometry(self.snapshot).geometry
        self.features = ()
        intents = generate_dimension_intents(self.snapshot, self.geometry, self.features).intents
        self.layout = optimize_dimension_layout(self.snapshot, self.geometry, intents, quantity=2)
        self.document = build_part_drawing_document(
            self.snapshot,
            self.geometry,
            self.features,
            self.layout,
            quantity=2,
        )

    def test_writes_dxf_pdf_and_json_from_one_document(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = render_part_drawing(self.document, Path(directory))
            self.assertTrue(paths.dxf_path.exists())
            self.assertTrue(paths.pdf_path.exists())
            self.assertTrue(paths.json_path.exists())
            dxf = ezdxf.readfile(paths.dxf_path)
            self.assertFalse(dxf.audit().has_errors)
            payload = json.loads(paths.json_path.read_text(encoding="utf-8"))
            self.assertEqual(self.document.part_position, payload["part_position"])
            self.assertEqual(self.document.annotation_texts(), payload["annotation_texts"])
            self.assertEqual("partDrawingSnapshot.v1", payload["source"]["schema_version"])
            self.assertEqual("partDrawingRules.v1", payload["rule_version"])
            self.assertIn("geometry_match_mm", payload["tolerances"])
            self.assertGreater(paths.pdf_path.stat().st_size, 1000)
            pdf = PdfReader(str(paths.pdf_path))
            self.assertEqual(1, len(pdf.pages))
            self.assertIn("P-1001", pdf.pages[0].extract_text())

    def test_renderer_does_not_emit_files_for_rejected_document(self):
        document = replace(self.document, status=DrawingStatus.REJECTED)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "REJECTED"):
                render_part_drawing(document, Path(directory))

    def test_explicit_round_hole_is_present_in_shared_document_and_dxf(self):
        snapshot = replace(
            self.snapshot,
            holes=(HoleSnapshot("H1", "ROUND", Point3D(60.0, 70.0, 30.0), diameter=22.0),),
        )
        geometry = analyze_plate_geometry(snapshot).geometry
        features = recognize_plate_features(snapshot, geometry).features
        intents = generate_dimension_intents(snapshot, geometry, features).intents
        layout = optimize_dimension_layout(snapshot, geometry, intents, quantity=1)
        document = build_part_drawing_document(snapshot, geometry, features, layout, quantity=1)
        self.assertTrue(any(item.__class__.__name__ == "DrawingCircle" for item in document.inner_segments))
        with tempfile.TemporaryDirectory() as directory:
            paths = render_part_drawing(document, Path(directory))
            entities = list(ezdxf.readfile(paths.dxf_path).modelspace().query("CIRCLE"))
            self.assertEqual(1, len(entities))

    def test_chinese_pdf_text_requires_explicit_cjk_font(self):
        document = replace(self.document, title_fields={**self.document.title_fields, "name": "连接板"})
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(PartDrawingRenderError, "CJK"):
                render_part_drawing(document, Path(directory), cjk_font_path=None)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run and verify failure**

Run: `python -m unittest tests.test_part_drawing_output`

Expected: missing `drawing_output` module.

- [ ] **Step 4: Implement the format-neutral document and renderers**

Create `drawing_output.py` defining:

```python
@dataclass(frozen=True)
class PartDrawingDocument:
    schema_version: str
    rule_version: str
    part_position: str
    part_ids: tuple[str, ...]
    quantity: int
    status: DrawingStatus
    page_width: float
    page_height: float
    scale: float
    geometry_fingerprint: str
    source: dict[str, str]
    tolerances: dict[str, float]
    recognized_feature_ids: tuple[str, ...]
    contour_segments: tuple[DrawingLine | DrawingArc, ...]
    inner_segments: tuple[DrawingLine | DrawingArc | DrawingCircle, ...]
    annotation_lines: tuple[DrawingLine, ...]
    annotation_text_items: tuple[DrawingText, ...]
    title_fields: dict[str, str]
    issues: tuple[DrawingIssue, ...]

    def annotation_texts(self) -> list[str]:
        return [item.text for item in self.annotation_text_items]


@dataclass(frozen=True)
class PartDrawingPaths:
    dxf_path: Path
    pdf_path: Path
    json_path: Path


class PartDrawingRenderError(RuntimeError):
    pass


def build_part_drawing_document(
    snapshot: PartDrawingSnapshot,
    geometry: NormalizedPlateGeometry,
    features: tuple[RecognizedFeature, ...],
    layout: PartDrawingLayout,
    quantity: int,
    status: DrawingStatus | None = None,
    issues: tuple[DrawingIssue, ...] = (),
    part_ids: tuple[str, ...] = (),
) -> PartDrawingDocument:
    document_status = status or layout.status
    contour_segments = tuple(_transform_segment(segment, layout.model_transform, "PART_CONTOUR") for segment in geometry.outer_loop)
    inner_segments = tuple(
        _transform_segment(segment, layout.model_transform, "PART_INNER")
        for loop in geometry.inner_loops
        for segment in loop
    ) + tuple(
        primitive
        for feature in features
        if feature.feature_type in {FeatureType.ROUND_HOLE, FeatureType.SLOT}
        for primitive in _feature_primitives(feature, layout.model_transform)
    )
    return PartDrawingDocument(
        schema_version="partDrawingDocument.v1",
        rule_version="partDrawingRules.v1",
        part_position=snapshot.part_position,
        part_ids=part_ids or (snapshot.part_id,),
        quantity=quantity,
        status=document_status,
        page_width=layout.page_width,
        page_height=layout.page_height,
        scale=layout.scale,
        geometry_fingerprint=geometry.fingerprint,
        source={
            "schema_version": snapshot.schema_version,
            "exporter_version": snapshot.exporter_version,
            "model_identifier": snapshot.model_identifier,
            "exported_at": snapshot.exported_at,
        },
        tolerances={
            "coordinate_noise_mm": 0.01,
            "geometry_match_mm": 0.1,
            "angle_match_deg": 0.05,
            "thickness_match_mm": 0.01,
        },
        recognized_feature_ids=tuple(feature.feature_id for feature in features),
        contour_segments=contour_segments,
        inner_segments=inner_segments,
        annotation_lines=layout.annotation_lines,
        annotation_text_items=layout.annotation_texts,
        title_fields=layout.title_fields,
        issues=issues,
    )


def render_part_drawing(
    document: PartDrawingDocument,
    output_directory: Path,
    cjk_font_path: Path | None = None,
) -> PartDrawingPaths:
    if document.status == DrawingStatus.REJECTED:
        raise ValueError("REJECTED document cannot be rendered")
    output_directory.mkdir(parents=True, exist_ok=True)
    stem = safe_part_position(document.part_position)
    paths = PartDrawingPaths(output_directory / f"{stem}.dxf", output_directory / f"{stem}.pdf", output_directory / f"{stem}.drawing.json")
    _render_dxf(document, paths.dxf_path)
    _render_pdf(document, paths.pdf_path, cjk_font_path)
    paths.json_path.write_text(json.dumps(_document_to_jsonable(document), ensure_ascii=False, indent=2), encoding="utf-8")
    return paths


def _document_to_jsonable(document: PartDrawingDocument) -> dict[str, Any]:
    return {
        "schema_version": document.schema_version,
        "rule_version": document.rule_version,
        "part_position": document.part_position,
        "part_ids": list(document.part_ids),
        "quantity": document.quantity,
        "status": document.status.value,
        "page": {"width": document.page_width, "height": document.page_height, "scale": document.scale},
        "geometry_fingerprint": document.geometry_fingerprint,
        "source": document.source,
        "tolerances": document.tolerances,
        "recognized_feature_ids": list(document.recognized_feature_ids),
        "annotation_texts": document.annotation_texts(),
        "entity_counts": _entity_counts(document),
        "issues": [
            {
                "code": issue.code.value,
                "message": issue.message,
                "blocking": issue.blocking,
                "part_ids": list(issue.part_ids),
                "evidence": list(issue.evidence),
            }
            for issue in document.issues
        ],
    }
```

Implement `_feature_primitives` so `ROUND_HOLE` becomes one `DrawingCircle` and `SLOT` becomes two tangent lines plus two end arcs on `PART_INNER`. Polygon and arc cutouts already come from `geometry.inner_loops`; do not draw them a second time.

DXF requirements:

- Use `ezdxf.new("R2007", setup=True)`.
- Add the seven design layers with stable colors/line types.
- Write contour and inner geometry before annotation and title entities.
- Save, reopen with `ezdxf.readfile`, and fail if `audit().has_errors`.

PDF requirements:

- Use `reportlab.pdfgen.canvas.Canvas` with `(document.page_width * mm, document.page_height * mm)`.
- Render the same document primitives, converting the document's top-left Y convention to ReportLab bottom-left Y.
- Use ReportLab's built-in Helvetica when all text is ASCII. If any document text is non-ASCII, require the explicit `cjk_font_path`, register that TTF, and raise `PartDrawingRenderError("CJK font is required")` when it is absent or unreadable. The batch pipeline converts this exception to `RENDER_FAILED`.
- Save and require a non-empty file larger than 1 KB.

- [ ] **Step 5: Run output and layout tests**

Run:

```powershell
python -m unittest tests.test_part_drawing_layout tests.test_part_drawing_output
```

Expected: all tests pass, DXF audit has no errors, PDF is non-empty.

- [ ] **Step 6: Commit shared output**

```powershell
git add pyproject.toml src/zijinhua_tekla/part_drawing/drawing_output.py tests/test_part_drawing_output.py
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode staged
git diff --cached --check
git commit -m "feat: render part drawings to dxf and pdf"
```

## Task 8: Add The Isolated Batch Pipeline And CLI

**Files:**
- Create: `src/zijinhua_tekla/part_drawing/pipeline.py`
- Create: `tests/test_part_drawing_pipeline.py`
- Modify: `src/zijinhua_tekla/part_drawing/__init__.py`
- Modify: `src/zijinhua_tekla/cli.py`

- [ ] **Step 1: Write failing end-to-end batch tests**

Create `tests/test_part_drawing_pipeline.py`:

```python
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from zijinhua_tekla.cli import main
from zijinhua_tekla.part_drawing.pipeline import run_part_drawing_batch


FIXTURE = Path(__file__).parent / "fixtures" / "part_drawing" / "rectangular_plate.json"


class PartDrawingPipelineTests(unittest.TestCase):
    def test_batch_writes_one_part_folder_and_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot_root = root / "snapshots"
            snapshot_root.mkdir()
            shutil.copy2(FIXTURE, snapshot_root / FIXTURE.name)
            result = run_part_drawing_batch(snapshot_root, root / "out")
            self.assertEqual(1, result.ok_count)
            self.assertEqual(0, result.rejected_count)
            self.assertTrue((root / "out" / "parts" / "P-1001" / "P-1001.dxf").exists())
            summary = json.loads((root / "out" / "part-drawing-batch-summary.json").read_text(encoding="utf-8"))
            self.assertEqual({"OK": 1, "REVIEW_REQUIRED": 0, "REJECTED": 0}, summary["status_counts"])

    def test_cli_returns_nonzero_when_one_group_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot_root = root / "snapshots"
            snapshot_root.mkdir()
            data = json.loads(FIXTURE.read_text(encoding="utf-8"))
            (snapshot_root / "good.json").write_text(json.dumps(data), encoding="utf-8")
            data["part"]["thickness"] = 12.0
            data["part"]["partId"] = "1002"
            (snapshot_root / "conflict.json").write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(1, main(["draw-parts", "--snapshot-root", str(snapshot_root), "--out", str(root / "out")]))
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m unittest tests.test_part_drawing_pipeline`

Expected: missing pipeline or missing `draw-parts` subcommand.

- [ ] **Step 3: Implement per-position isolated orchestration**

Create `pipeline.py` with `PartDrawingBatchResult` and:

```python
def run_part_drawing_batch(
    snapshot_root: Path,
    output_root: Path,
    cjk_font_path: Path | None = None,
) -> PartDrawingBatchResult:
    loaded = []
    load_issues = []
    for path in sorted(snapshot_root.glob("*.json")):
        try:
            loaded.append(load_part_snapshot(path))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            load_issues.append(_snapshot_issue(path, exc))
    group_results = []
    for group in group_part_snapshots(loaded):
        if group.status == DrawingStatus.REJECTED:
            group_results.append(_write_rejected_group(group, output_root))
            continue
        feature_result = recognize_plate_features(group.representative, group.geometry)
        dimension_result = generate_dimension_intents(group.representative, group.geometry, feature_result.features)
        layout = optimize_dimension_layout(group.representative, group.geometry, dimension_result.intents, group.quantity)
        status = _aggregate_status(group.status, feature_result.status, dimension_result.status, layout.status)
        issues = group.issues + feature_result.issues + dimension_result.issues + _layout_issues(layout)
        document = build_part_drawing_document(
            group.representative,
            group.geometry,
            feature_result.features,
            layout,
            group.quantity,
            status,
            issues,
            tuple(snapshot.part_id for snapshot in group.snapshots),
        )
        try:
            paths = render_part_drawing(
                document,
                output_root / "parts" / safe_part_position(group.part_position),
                cjk_font_path=cjk_font_path,
            )
            group_results.append(_successful_result(group, document, paths))
        except (OSError, ValueError, PartDrawingRenderError) as exc:
            group_results.append(_render_failed_result(group, exc))
    result = _batch_result(group_results, load_issues)
    _write_batch_summary(result, output_root / "part-drawing-batch-summary.json")
    return result
```

Rejected groups write only `conflicts/<safe-part-position>.conflict.json`. Snapshot parse failures appear in the batch summary with source path and `SNAPSHOT_INVALID`. A rejected or render-failed item makes `rejected_count > 0`; review-required items do not change the process exit code.

- [ ] **Step 4: Add the CLI subcommand without changing analyze**

In `cli.py`, add:

```python
draw_parts_parser = sub.add_parser("draw-parts")
draw_parts_parser.add_argument("--snapshot-root", required=True)
draw_parts_parser.add_argument("--out", default="outputs/part-drawings")
draw_parts_parser.add_argument("--cjk-font", default="")
```

Add a focused handler and call it before the existing analyze branch:

```python
def _run_draw_parts(args) -> int:
    result = run_part_drawing_batch(
        Path(args.snapshot_root),
        Path(args.out),
        Path(args.cjk_font) if args.cjk_font else None,
    )
    print(f"Part drawings: OK={result.ok_count} REVIEW_REQUIRED={result.review_count} REJECTED={result.rejected_count}")
    return 1 if result.rejected_count else 0
```

Inside `main()`, immediately after `parse_args()`, add the two-line branch `if args.command == "draw-parts": return _run_draw_parts(args)`. Keep the existing analyze body unchanged apart from returning `0` after its final print.

Change the module footer to `raise SystemExit(main())`. Preserve `analyze` output and return `0` after it completes so existing callers remain compatible.

- [ ] **Step 5: Run pipeline, CLI, and existing CLI-adjacent tests**

Run:

```powershell
python -m unittest tests.test_part_drawing_pipeline tests.test_pipeline_offline tests.test_reports_offline
```

Expected: all tests pass.

- [ ] **Step 6: Commit the vertical slice**

```powershell
git add src/zijinhua_tekla/part_drawing src/zijinhua_tekla/cli.py tests/test_part_drawing_pipeline.py
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode staged
git diff --cached --check
git commit -m "feat: add offline part drawing pipeline"
```

## Task 9: Close Verification And Project Memory

**Files:**
- Modify: `TASKLIST.md`
- Create: `docs/verification/2026-07-13-offline-part-drawing-engine.md`

- [ ] **Step 1: Run every focused part-drawing test**

Run:

```powershell
python -m unittest tests.test_part_drawing_contracts tests.test_part_drawing_geometry tests.test_part_drawing_quality tests.test_part_drawing_features tests.test_part_drawing_dimensions tests.test_part_drawing_layout tests.test_part_drawing_output tests.test_part_drawing_pipeline
```

Expected: all tests pass with zero failures and zero errors. Record the actual test count, duration, and warnings in the verification document.

- [ ] **Step 2: Run the full regression suite**

Run:

```powershell
python -m unittest discover -s tests
```

Expected: all tests pass. Record the actual count and any known non-failing warnings.

- [ ] **Step 3: Run a deterministic CLI smoke**

Run:

```powershell
python -m zijinhua_tekla.cli draw-parts --snapshot-root tests\fixtures\part_drawing --out outputs\part-drawing-fixture-smoke-20260713
```

Expected summary:

```text
Part drawings: OK=1 REVIEW_REQUIRED=0 REJECTED=0
```

Verify these paths exist:

```text
outputs/part-drawing-fixture-smoke-20260713/parts/P-1001/P-1001.dxf
outputs/part-drawing-fixture-smoke-20260713/parts/P-1001/P-1001.pdf
outputs/part-drawing-fixture-smoke-20260713/parts/P-1001/P-1001.drawing.json
outputs/part-drawing-fixture-smoke-20260713/part-drawing-batch-summary.json
```

- [ ] **Step 4: Audit generated artifacts independently**

Run a narrow readback command or test helper that prints only:

- DXF audit error/fix count.
- DXF layer and entity counts.
- PDF byte size and page size.
- Drawing JSON status, part position, fingerprint, and annotation count.

Expected: DXF audit errors `0`; PDF non-empty and A3 landscape; JSON status `OK`; no output exceeds the project log hygiene limit.

- [ ] **Step 5: Write the verification record**

Create `docs/verification/2026-07-13-offline-part-drawing-engine.md` with:

- Implemented scope and explicit non-goals.
- Exact focused/full/smoke commands and actual results.
- Fixture-to-output evidence summary.
- DXF/PDF readback statistics.
- Remaining blocker: no real Tekla `partDrawingSnapshot.v1` producer until the separate exporter plan is executed.
- Next step: exporter contract implementation and real-model flat-plate smoke.

- [ ] **Step 6: Update the task list with verified status only**

Add a dated section to `TASKLIST.md`. Mark the offline engine complete only if Steps 1-4 passed. Keep “Tekla exporter snapshot producer” and “real model smoke” unchecked.

- [ ] **Step 7: Run CCG change verification**

Run from the repository root:

```powershell
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode working
```

Resolve any scope or documentation issue before committing. For security-relevant findings, run the separate `verify-security` gate on `src/zijinhua_tekla/part_drawing`.

- [ ] **Step 8: Commit verification and project memory**

```powershell
git add TASKLIST.md docs/verification/2026-07-13-offline-part-drawing-engine.md
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode staged
git diff --cached --check
git commit -m "docs: verify offline part drawing engine"
```

## Final Completion Gate

Before claiming the plan implementation complete:

- Run `git status --short` and confirm only intentional generated smoke output is untracked or ignored.
- Run the focused test command again after the final documentation commit if code changed during verification.
- Run `git log --oneline -10` and confirm every task commit is present.
- Do not claim real Tekla coverage; that remains a separate exporter integration plan.
- Do not push unless the user explicitly requests it.
