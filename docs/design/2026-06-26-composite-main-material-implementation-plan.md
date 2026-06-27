# Composite Main Material Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a general composite main-material classifier that splits a complex Tekla member into N axial section-regime segments and reports the main plates for each regime.

**Architecture:** Add a focused classifier next to the existing BOX/H main-material code, then wire its result into the offline pipeline and reports. Keep existing `box-main-material-segment-groups` behavior intact; the new composite report becomes the richer result for hybrid members.

**Tech Stack:** Python dataclasses, standard `unittest`, existing Tekla bundle dictionaries, existing report writer patterns, existing `python -m zijinhua_tekla.cli analyze` CLI.

---

## File Structure

- Create `src/zijinhua_tekla/classifiers/composite_main_material_segments.py`
  - Owns composite dataclasses, station evidence extraction, regime segmentation, role assignment, and `classify_composite_main_material_segments`.
- Create `tests/test_composite_main_material_segments.py`
  - Unit tests for station segmentation, lower cross flange main plates, transition single-primary-role semantics, and stable BOX role output.
- Modify `src/zijinhua_tekla/pipeline/offline.py`
  - Adds `composite_main_material_segments` to `OfflinePipelineResult`.
  - Calls the new classifier after existing BOX/H groups.
- Modify `src/zijinhua_tekla/reports/offline.py`
  - Writes `<member>-composite-main-material-segments.json/csv`.
  - Adds report paths to `OfflineReportPaths.as_tuple`.
  - Adds a short Markdown link section.
- Modify `tests/test_reports_offline.py`
  - Locks JSON/CSV report creation for composite results.
- Modify `tests/test_pipeline_offline.py`
  - Locks result propagation from pipeline to reports.
- Add `docs/verification/2026-06-26-composite-main-material-segments.md`
  - Records unit test and smoke commands after implementation.

## Data Model

Implement these public objects in `composite_main_material_segments.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CompositeSegmentType(str, Enum):
    CROSS_CORE_WITH_FLANGES = "CROSS_CORE_WITH_FLANGES"
    CROSS_TO_BOX_TRANSITION = "CROSS_TO_BOX_TRANSITION"
    PARTIAL_BOX_FORMING = "PARTIAL_BOX_FORMING"
    BOX_CLOSED_SECTION = "BOX_CLOSED_SECTION"
    END_OR_NODE_ZONE = "END_OR_NODE_ZONE"
    MIXED_OR_INSUFFICIENT_EVIDENCE = "MIXED_OR_INSUFFICIENT_EVIDENCE"


class CompositePrimaryRole(str, Enum):
    CROSS_CORE_MAIN_PLATE = "CROSS_CORE_MAIN_PLATE"
    CROSS_FLANGE_MAIN_PLATE = "CROSS_FLANGE_MAIN_PLATE"
    BOX_MAIN_WALL_PLATE = "BOX_MAIN_WALL_PLATE"
    BOX_FORMING_MAIN_PLATE = "BOX_FORMING_MAIN_PLATE"
    TRANSITION_MAIN_PLATE = "TRANSITION_MAIN_PLATE"
    END_NODE_MAIN_PLATE_CANDIDATE = "END_NODE_MAIN_PLATE_CANDIDATE"


@dataclass(frozen=True)
class CompositeMainPlate:
    part_id: str
    part_position: str
    primary_role: CompositePrimaryRole
    secondary_evidence: list[str] = field(default_factory=list)
    evidence_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "part_position": self.part_position,
            "primary_role": self.primary_role.value,
            "secondary_evidence": list(self.secondary_evidence),
            "evidence_codes": list(self.evidence_codes),
        }


@dataclass(frozen=True)
class CompositeMainMaterialSegment:
    assembly_id: str
    segment_id: str
    station_start: float
    station_end: float
    segment_type: CompositeSegmentType
    main_plates: list[CompositeMainPlate]
    confidence: float
    evidence_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "segment_id": self.segment_id,
            "station_start": round(self.station_start, 3),
            "station_end": round(self.station_end, 3),
            "segment_type": self.segment_type.value,
            "confidence": round(self.confidence, 3),
            "evidence_codes": list(self.evidence_codes),
            "main_plates": [plate.to_dict() for plate in self.main_plates],
        }
```

## Task 1: Add Composite Dataclasses and Public Entrypoint

**Files:**
- Create: `src/zijinhua_tekla/classifiers/composite_main_material_segments.py`
- Create: `tests/test_composite_main_material_segments.py`

- [ ] **Step 1: Write the failing model serialization test**

Add this test:

```python
import unittest

from zijinhua_tekla.classifiers.composite_main_material_segments import (
    CompositeMainMaterialSegment,
    CompositeMainPlate,
    CompositePrimaryRole,
    CompositeSegmentType,
)


class CompositeMainMaterialSegmentTests(unittest.TestCase):
    def test_segment_to_dict_uses_string_roles(self):
        segment = CompositeMainMaterialSegment(
            assembly_id="A1",
            segment_id="S1",
            station_start=0,
            station_end=1000,
            segment_type=CompositeSegmentType.CROSS_CORE_WITH_FLANGES,
            confidence=0.91,
            evidence_codes=["STATION_REGIME_SEGMENT"],
            main_plates=[
                CompositeMainPlate(
                    part_id="p-flange",
                    part_position="P-FLANGE",
                    primary_role=CompositePrimaryRole.CROSS_FLANGE_MAIN_PLATE,
                    secondary_evidence=["parallel_to_cross_core_plate"],
                    evidence_codes=["CROSS_FLANGE_OUTER_PLATE"],
                )
            ],
        )

        self.assertEqual(
            {
                "assembly_id": "A1",
                "segment_id": "S1",
                "station_start": 0,
                "station_end": 1000,
                "segment_type": "CROSS_CORE_WITH_FLANGES",
                "confidence": 0.91,
                "evidence_codes": ["STATION_REGIME_SEGMENT"],
                "main_plates": [
                    {
                        "part_id": "p-flange",
                        "part_position": "P-FLANGE",
                        "primary_role": "CROSS_FLANGE_MAIN_PLATE",
                        "secondary_evidence": ["parallel_to_cross_core_plate"],
                        "evidence_codes": ["CROSS_FLANGE_OUTER_PLATE"],
                    }
                ],
            },
            segment.to_dict(),
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing test**

Run:

```powershell
python -m unittest tests.test_composite_main_material_segments
```

Expected: FAIL with `ModuleNotFoundError: No module named 'zijinhua_tekla.classifiers.composite_main_material_segments'`.

- [ ] **Step 3: Add dataclasses and empty classifier function**

Create the file using the Data Model block above, then add:

```python
from typing import Any


def classify_composite_main_material_segments(
    assembly: dict[str, Any],
    member: dict[str, Any] | None = None,
) -> list[CompositeMainMaterialSegment]:
    return []
```

- [ ] **Step 4: Run the model test**

Run:

```powershell
python -m unittest tests.test_composite_main_material_segments
```

Expected: PASS, `Ran 1 test`.

- [ ] **Step 5: Commit this task**

Commit only the new classifier and test:

```powershell
git add src/zijinhua_tekla/classifiers/composite_main_material_segments.py tests/test_composite_main_material_segments.py
git commit -m "Add composite main material segment model"
```

## Task 2: Build Station Regime Segmentation

**Files:**
- Modify: `src/zijinhua_tekla/classifiers/composite_main_material_segments.py`
- Modify: `tests/test_composite_main_material_segments.py`

- [ ] **Step 1: Add a failing test for N axial segments**

Append this test method:

```python
    def test_splits_cross_transition_and_box_station_regimes(self):
        assembly = _composite_fixture()

        segments = classify_composite_main_material_segments(assembly)

        self.assertEqual(
            [
                "CROSS_CORE_WITH_FLANGES",
                "CROSS_TO_BOX_TRANSITION",
                "BOX_CLOSED_SECTION",
            ],
            [segment.segment_type.value for segment in segments],
        )
        self.assertEqual([(0, 3000), (3000, 4500), (4500, 8000)], [
            (segment.station_start, segment.station_end) for segment in segments
        ])
```

Add these fixture helpers at the bottom of the test file:

```python
def _composite_fixture():
    return {
        "assemblyId": "A-COMPOSITE",
        "metadata": {
            "memberAxisEvidence": {"length": 8000},
            "boxSectionEvidence": {
                "source": "teklaSolidFaceSectionSegments.v2",
                "stationLoops": [
                    _station_loop(0, "cross"),
                    _station_loop(1500, "cross"),
                    _station_loop(3000, "transition"),
                    _station_loop(4500, "box"),
                    _station_loop(8000, "box"),
                ],
            },
        },
        "parts": [
            _part("core-x", "P-CORE-X", 0, 4500, "X", 0, 0, 20, 300),
            _part("core-y", "P-CORE-Y", 0, 4500, "Y", 0, 0, 300, 20),
            _part("flange-l", "P-FLANGE-L", 0, 3000, "X", -220, 0, 20, 220),
            _part("flange-r", "P-FLANGE-R", 0, 3000, "X", 220, 0, 20, 220),
            _part("box-a", "P-BOX-A", 3000, 8000, "X", -260, 0, 20, 520),
            _part("box-b", "P-BOX-B", 3000, 8000, "X", 260, 0, 20, 520),
            _part("box-c", "P-BOX-C", 4500, 8000, "Y", 0, -260, 520, 20),
            _part("box-d", "P-BOX-D", 4500, 8000, "Y", 0, 260, 520, 20),
        ],
        "relationships": [],
    }


def _station_loop(station, regime_hint):
    closed_count = 1 if regime_hint == "box" else 0
    return {
        "station": station,
        "closedLoopCount": closed_count,
        "partLoops": [],
        "diagnostics": [f"compositeTestRegime={regime_hint}"],
    }


def _part(part_id, position, start, end, normal_axis, u, v, span_u, span_v):
    normal = {"u": 1.0, "v": 0.0} if normal_axis == "X" else {"u": 0.0, "v": 1.0}
    return {
        "partId": part_id,
        "partPosition": position,
        "mainMaterialEvidence": {
            "axisStationStart": start,
            "axisStationEnd": end,
            "axisStationLength": end - start,
            "bodyFaceId": f"FACE-{part_id}",
            "isBodyWallPlateCandidate": True,
            "sectionProjectionEvidence": {
                "projectedCentroid": {"u": u, "v": v},
                "projectedBoundsMin": {"u": u - span_u / 2, "v": v - span_v / 2},
                "projectedBoundsMax": {"u": u + span_u / 2, "v": v + span_v / 2},
                "normalProjection": normal,
                "normalProjectionMagnitude": 1.0,
            },
        },
    }
```

- [ ] **Step 2: Run the failing test**

Run:

```powershell
python -m unittest tests.test_composite_main_material_segments
```

Expected: FAIL because the classifier returns `[]`.

- [ ] **Step 3: Implement station snapshots and segment merging**

In `composite_main_material_segments.py`, add:

```python
@dataclass(frozen=True)
class _StationSnapshot:
    station: float
    segment_type: CompositeSegmentType
    active_part_ids: list[str]
    evidence_codes: list[str]


def classify_composite_main_material_segments(
    assembly: dict[str, Any],
    member: dict[str, Any] | None = None,
) -> list[CompositeMainMaterialSegment]:
    snapshots = _station_snapshots(assembly)
    if not snapshots:
        return []
    return _merge_snapshots_into_segments(str(assembly.get("assemblyId", "")), snapshots, assembly)
```

Add helper behavior:

```python
def _station_snapshots(assembly: dict[str, Any]) -> list[_StationSnapshot]:
    parts = [part for part in assembly.get("parts", []) if _is_main_candidate(part)]
    station_loops = (
        assembly.get("metadata", {})
        .get("boxSectionEvidence", {})
        .get("stationLoops", [])
    )
    snapshots = []
    for station_loop in station_loops:
        station = float(station_loop.get("station", 0.0))
        active = [part for part in parts if _part_active_at(part, station)]
        segment_type = _classify_station_type(station_loop, active)
        snapshots.append(
            _StationSnapshot(
                station=station,
                segment_type=segment_type,
                active_part_ids=[str(part.get("partId", "")) for part in active],
                evidence_codes=["STATION_REGIME_CLASSIFIED"],
            )
        )
    return sorted(snapshots, key=lambda item: item.station)
```

Classification rules:

```python
def _classify_station_type(station_loop: dict[str, Any], active_parts: list[dict[str, Any]]) -> CompositeSegmentType:
    if int(station_loop.get("closedLoopCount") or 0) > 0:
        return CompositeSegmentType.BOX_CLOSED_SECTION
    normal_axes = {_normal_axis(part) for part in active_parts}
    has_cross_core = "X" in normal_axes and "Y" in normal_axes
    has_outer_flange = any(_is_outer_offset(part) for part in active_parts)
    has_box_forming = sum(1 for part in active_parts if _is_box_forming_candidate(part)) >= 2
    if has_cross_core and has_box_forming:
        return CompositeSegmentType.CROSS_TO_BOX_TRANSITION
    if has_cross_core and has_outer_flange:
        return CompositeSegmentType.CROSS_CORE_WITH_FLANGES
    if has_box_forming:
        return CompositeSegmentType.PARTIAL_BOX_FORMING
    return CompositeSegmentType.MIXED_OR_INSUFFICIENT_EVIDENCE
```

Merge snapshots by consecutive identical type. Use the first station of the next regime as the previous segment end; use the first station of the current regime as the current segment start. This matches report-friendly engineering intervals such as `0-3000`, `3000-4500`, `4500-8000`.

```python
def _merge_snapshots_into_segments(
    assembly_id: str,
    snapshots: list[_StationSnapshot],
    assembly: dict[str, Any],
) -> list[CompositeMainMaterialSegment]:
    result = []
    group_start = 0
    for index in range(1, len(snapshots) + 1):
        if index < len(snapshots) and snapshots[index].segment_type == snapshots[group_start].segment_type:
            continue
        first = snapshots[group_start]
        last = snapshots[index - 1]
        station_start = first.station
        station_end = last.station
        if index < len(snapshots):
            station_end = snapshots[index].station
        result.append(
            CompositeMainMaterialSegment(
                assembly_id=assembly_id,
                segment_id=f"S{len(result) + 1}",
                station_start=station_start,
                station_end=station_end,
                segment_type=first.segment_type,
                main_plates=[],
                confidence=0.75,
                evidence_codes=["STATION_REGIME_SEGMENT"],
            )
        )
        group_start = index
    return result
```

- [ ] **Step 4: Run the segmentation test**

Run:

```powershell
python -m unittest tests.test_composite_main_material_segments
```

Expected: PASS for model and segmentation tests.

- [ ] **Step 5: Commit this task**

```powershell
git add src/zijinhua_tekla/classifiers/composite_main_material_segments.py tests/test_composite_main_material_segments.py
git commit -m "Add composite station regime segmentation"
```

## Task 3: Assign Main Plate Roles Per Segment

**Files:**
- Modify: `src/zijinhua_tekla/classifiers/composite_main_material_segments.py`
- Modify: `tests/test_composite_main_material_segments.py`

- [ ] **Step 1: Add failing role tests**

Append:

```python
    def test_assigns_cross_flange_and_box_main_wall_roles(self):
        segments = classify_composite_main_material_segments(_composite_fixture())

        lower = segments[0]
        transition = segments[1]
        upper = segments[2]

        lower_roles = {plate.part_position: plate.primary_role.value for plate in lower.main_plates}
        self.assertEqual("CROSS_FLANGE_MAIN_PLATE", lower_roles["P-FLANGE-L"])
        self.assertEqual("CROSS_FLANGE_MAIN_PLATE", lower_roles["P-FLANGE-R"])
        self.assertEqual("CROSS_CORE_MAIN_PLATE", lower_roles["P-CORE-X"])
        self.assertEqual("CROSS_CORE_MAIN_PLATE", lower_roles["P-CORE-Y"])

        transition_roles = {plate.part_position: plate.primary_role.value for plate in transition.main_plates}
        self.assertEqual("TRANSITION_MAIN_PLATE", transition_roles["P-CORE-X"])
        self.assertEqual("BOX_FORMING_MAIN_PLATE", transition_roles["P-BOX-A"])
        self.assertIn(
            "continues_from_lower_cross_column",
            next(plate for plate in transition.main_plates if plate.part_position == "P-CORE-X").secondary_evidence,
        )

        upper_roles = {plate.part_position: plate.primary_role.value for plate in upper.main_plates}
        self.assertEqual(
            {
                "P-BOX-A": "BOX_MAIN_WALL_PLATE",
                "P-BOX-B": "BOX_MAIN_WALL_PLATE",
                "P-BOX-C": "BOX_MAIN_WALL_PLATE",
                "P-BOX-D": "BOX_MAIN_WALL_PLATE",
            },
            upper_roles,
        )
```

- [ ] **Step 2: Run the failing role test**

Run:

```powershell
python -m unittest tests.test_composite_main_material_segments
```

Expected: FAIL because `main_plates` is still empty.

- [ ] **Step 3: Implement role assignment**

Add `_assign_main_plates` and call it from `_merge_snapshots_into_segments` before constructing each segment.

Role rules:

```python
def _assign_main_plates(
    assembly: dict[str, Any],
    station_start: float,
    station_end: float,
    segment_type: CompositeSegmentType,
) -> list[CompositeMainPlate]:
    parts = [
        part for part in assembly.get("parts", [])
        if _is_main_candidate(part) and _interval_overlaps(part, station_start, station_end)
    ]
    plates = []
    for part in parts:
        primary_role, secondary = _primary_role_for_part(part, segment_type)
        if primary_role is None:
            continue
        plates.append(
            CompositeMainPlate(
                part_id=str(part.get("partId", "")),
                part_position=str(part.get("partPosition", "")),
                primary_role=primary_role,
                secondary_evidence=secondary,
                evidence_codes=[segment_type.value, primary_role.value],
            )
        )
    return sorted(plates, key=lambda plate: (plate.primary_role.value, plate.part_position, plate.part_id))
```

Primary role logic:

```python
def _primary_role_for_part(
    part: dict[str, Any],
    segment_type: CompositeSegmentType,
) -> tuple[CompositePrimaryRole | None, list[str]]:
    if segment_type == CompositeSegmentType.CROSS_CORE_WITH_FLANGES:
        if _is_outer_offset(part):
            return CompositePrimaryRole.CROSS_FLANGE_MAIN_PLATE, ["parallel_to_cross_core_plate"]
        return CompositePrimaryRole.CROSS_CORE_MAIN_PLATE, []
    if segment_type == CompositeSegmentType.CROSS_TO_BOX_TRANSITION:
        if _is_box_forming_candidate(part):
            return CompositePrimaryRole.BOX_FORMING_MAIN_PLATE, ["overlaps_with_cross_column_transition"]
        return CompositePrimaryRole.TRANSITION_MAIN_PLATE, ["continues_from_lower_cross_column"]
    if segment_type == CompositeSegmentType.PARTIAL_BOX_FORMING:
        return CompositePrimaryRole.BOX_FORMING_MAIN_PLATE, []
    if segment_type == CompositeSegmentType.BOX_CLOSED_SECTION:
        return CompositePrimaryRole.BOX_MAIN_WALL_PLATE, []
    if segment_type == CompositeSegmentType.END_OR_NODE_ZONE:
        return CompositePrimaryRole.END_NODE_MAIN_PLATE_CANDIDATE, []
    return None, []
```

Use these helpers:

```python
def _is_main_candidate(part: dict[str, Any]) -> bool:
    evidence = part.get("mainMaterialEvidence")
    return isinstance(evidence, dict) and evidence.get("isBodyWallPlateCandidate") is True


def _part_active_at(part: dict[str, Any], station: float) -> bool:
    return _station_start(part) <= station <= _station_end(part)


def _interval_overlaps(part: dict[str, Any], start: float, end: float) -> bool:
    return _station_start(part) < end and _station_end(part) > start
```

- [ ] **Step 4: Run role tests**

Run:

```powershell
python -m unittest tests.test_composite_main_material_segments
```

Expected: PASS.

- [ ] **Step 5: Commit this task**

```powershell
git add src/zijinhua_tekla/classifiers/composite_main_material_segments.py tests/test_composite_main_material_segments.py
git commit -m "Assign composite main plate roles"
```

## Task 4: Wire Composite Results Into Pipeline

**Files:**
- Modify: `src/zijinhua_tekla/pipeline/offline.py`
- Modify: `tests/test_pipeline_offline.py`

- [ ] **Step 1: Add failing pipeline propagation assertion**

In the existing offline pipeline test fixture, add a small composite-friendly assembly with `boxSectionEvidence.stationLoops` and assert:

```python
self.assertTrue(result.composite_main_material_segments)
self.assertEqual(
    "CROSS_FLANGE_MAIN_PLATE",
    {
        plate.part_position: plate.primary_role.value
        for segment in result.composite_main_material_segments
        for plate in segment.main_plates
    }["P-FLANGE-L"],
)
```

- [ ] **Step 2: Run the failing pipeline test**

Run:

```powershell
python -m unittest tests.test_pipeline_offline
```

Expected: FAIL with `AttributeError: 'OfflinePipelineResult' object has no attribute 'composite_main_material_segments'`.

- [ ] **Step 3: Modify pipeline dataclass and call classifier**

In `src/zijinhua_tekla/pipeline/offline.py`, import:

```python
from ..classifiers.composite_main_material_segments import (
    CompositeMainMaterialSegment,
    classify_composite_main_material_segments,
)
```

Add to `OfflinePipelineResult`:

```python
composite_main_material_segments: list[CompositeMainMaterialSegment] = field(default_factory=list)
```

In `run_offline_analysis`, compute:

```python
composite_main_material_segments = classify_composite_main_material_segments(assembly, member)
```

Pass it into `OfflinePipelineResult(...)`:

```python
composite_main_material_segments=composite_main_material_segments,
```

- [ ] **Step 4: Run pipeline tests**

Run:

```powershell
python -m unittest tests.test_pipeline_offline
```

Expected: PASS.

- [ ] **Step 5: Commit this task**

```powershell
git add src/zijinhua_tekla/pipeline/offline.py tests/test_pipeline_offline.py
git commit -m "Wire composite main material into offline pipeline"
```

## Task 5: Write Composite JSON and CSV Reports

**Files:**
- Modify: `src/zijinhua_tekla/reports/offline.py`
- Modify: `tests/test_reports_offline.py`

- [ ] **Step 1: Add failing report assertions**

In `tests/test_reports_offline.py`, import the new dataclasses and add a `composite_main_material_segments=[...]` value to the `OfflinePipelineResult` fixture:

```python
CompositeMainMaterialSegment(
    assembly_id="100",
    segment_id="S1",
    station_start=0,
    station_end=3000,
    segment_type=CompositeSegmentType.CROSS_CORE_WITH_FLANGES,
    confidence=0.88,
    evidence_codes=["STATION_REGIME_SEGMENT"],
    main_plates=[
        CompositeMainPlate(
            part_id="501",
            part_position="A-FLANGE-1",
            primary_role=CompositePrimaryRole.CROSS_FLANGE_MAIN_PLATE,
            secondary_evidence=["parallel_to_cross_core_plate"],
            evidence_codes=["CROSS_FLANGE_OUTER_PLATE"],
        )
    ],
)
```

Assert:

```python
composite_rows = json.loads(paths.composite_main_material_segments_path.read_text(encoding="utf-8"))
composite_csv_rows = pd.read_csv(paths.composite_main_material_segments_csv_path)
self.assertEqual("A-GKZ-1-composite-main-material-segments.json", paths.composite_main_material_segments_path.name)
self.assertEqual("CROSS_CORE_WITH_FLANGES", composite_rows[0]["segment_type"])
self.assertEqual("A-FLANGE-1", composite_rows[0]["main_plates"][0]["part_position"])
self.assertEqual("CROSS_FLANGE_MAIN_PLATE", composite_csv_rows.iloc[0]["primary_role"])
self.assertIn("composite-main-material-segments.json", markdown)
```

- [ ] **Step 2: Run the failing report test**

Run:

```powershell
python -m unittest tests.test_reports_offline
```

Expected: FAIL because `OfflineReportPaths` has no composite paths.

- [ ] **Step 3: Add report paths and writers**

In `OfflineReportPaths`, add:

```python
composite_main_material_segments_path: Path
composite_main_material_segments_csv_path: Path
```

Add both paths to `as_tuple`.

In `write_offline_analysis_report`, create:

```python
composite_main_material_segments_path = out_dir / f"{member_id}-composite-main-material-segments.json"
composite_main_material_segments_csv_path = out_dir / f"{member_id}-composite-main-material-segments.csv"
```

Write JSON and CSV:

```python
composite_segments = [segment.to_dict() for segment in result.composite_main_material_segments]
composite_main_material_segments_path.write_text(
    json.dumps(composite_segments, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
pd.DataFrame(_flatten_composite_main_material_segments(composite_segments)).to_csv(
    composite_main_material_segments_csv_path,
    index=False,
    encoding="utf-8-sig",
)
```

Add flattener:

```python
def _flatten_composite_main_material_segments(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    flat = []
    for segment in rows:
        for plate in segment.get("main_plates", []):
            flat.append({
                "assembly_id": segment.get("assembly_id", ""),
                "segment_id": segment.get("segment_id", ""),
                "station_start": segment.get("station_start", ""),
                "station_end": segment.get("station_end", ""),
                "segment_type": segment.get("segment_type", ""),
                "confidence": segment.get("confidence", ""),
                "part_id": plate.get("part_id", ""),
                "part_position": plate.get("part_position", ""),
                "primary_role": plate.get("primary_role", ""),
                "secondary_evidence": ";".join(plate.get("secondary_evidence", [])),
                "evidence_codes": ";".join(plate.get("evidence_codes", [])),
            })
    return flat
```

Add both paths to Markdown builder arguments and include:

```markdown
- Composite main material segments: `<json_path>` / `<csv_path>`
```

- [ ] **Step 4: Run report tests**

Run:

```powershell
python -m unittest tests.test_reports_offline
```

Expected: PASS.

- [ ] **Step 5: Commit this task**

```powershell
git add src/zijinhua_tekla/reports/offline.py tests/test_reports_offline.py
git commit -m "Write composite main material reports"
```

## Task 6: CLI Smoke and Regression Verification

**Files:**
- Create: `docs/verification/2026-06-26-composite-main-material-segments.md`
- Modify: `STATUS.md`
- Modify: `TASKLIST.md`

- [ ] **Step 1: Run focused unit tests**

Run:

```powershell
python -m unittest tests.test_composite_main_material_segments tests.test_pipeline_offline tests.test_reports_offline
```

Expected: PASS.

- [ ] **Step 2: Run existing main-material regression tests**

Run:

```powershell
python -m unittest tests.test_main_material_segments tests.test_box_main_material_segments tests.test_h_beam_part_sides
```

Expected: PASS. Existing openpyxl deprecation warnings are acceptable if assertions pass.

- [ ] **Step 3: Re-export current Tekla selection for smoke**

Run the Tekla exporter against the current selection. Do not use an older cache as final verification evidence.

```powershell
I:\xingcaisuanfa\TeklaSectionClassifier.Runner\bin\Debug\net48\TeklaSectionClassifier.Runner.exe --body-bracket-export --out I:\zijinhuatekla\cache\composite_current_selection_verify
```

Expected:

- Exporter reports the processed member id.
- Exporter prints the actual timestamped output directory, for example `I:\zijinhuatekla\cache\YYYYMMDD_HHMMSS`.
- Use that actual timestamped directory in the next step.

- [ ] **Step 4: Run current selection smoke with the fresh export**

Use the freshly exported directory from Step 3:

```powershell
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\<fresh-export-dir> --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id <fresh-member-id> --out outputs\current-selection-<fresh-member-id>-composite-20260626
```

Expected:

- Outputs include `<fresh-member-id>-composite-main-material-segments.json`.
- JSON has at least two `segment_type` values.
- At least one main plate has `primary_role=CROSS_FLANGE_MAIN_PLATE` if the current export carries enough lower-section evidence.
- If the current export lacks enough evidence for lower cross flanges, the report must show `MIXED_OR_INSUFFICIENT_EVIDENCE` instead of inventing a role.

- [ ] **Step 5: Create verification note**

Create `docs/verification/2026-06-26-composite-main-material-segments.md` with:

```markdown
# Composite Main Material Segments Verification

日期：2026-06-26

## Scope

验证组合截面构件主材识别：沿构件主轴切 N 个截面体系区段，每段输出单主角色主板，十字柱外侧翼缘板按 `CROSS_FLANGE_MAIN_PLATE` 进入主材。

## Commands

```powershell
python -m unittest tests.test_composite_main_material_segments tests.test_pipeline_offline tests.test_reports_offline
python -m unittest tests.test_main_material_segments tests.test_box_main_material_segments tests.test_h_beam_part_sides
I:\xingcaisuanfa\TeklaSectionClassifier.Runner\bin\Debug\net48\TeklaSectionClassifier.Runner.exe --body-bracket-export --out I:\zijinhuatekla\cache\composite_current_selection_verify`r`npython -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\<fresh-export-dir> --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id <fresh-member-id> --out outputs\current-selection-<fresh-member-id>-composite-20260626
```

## Results

- Unit tests: record PASS/FAIL and failure reason if any.
- Regression tests: record PASS/FAIL and warning summary.
- Smoke output: record generated composite JSON/CSV paths.
- T2-3GKZ-12 result: record segment types and main plate role counts.

## Notes

Do not treat any current selection member id as a hard-coded rule. If lower cross-flange evidence is absent in the fresh export, record the missing evidence and keep the row in `MIXED_OR_INSUFFICIENT_EVIDENCE`.
```

- [ ] **Step 6: Update live memory files**

In `STATUS.md`, add one short line with the verification file path and whether the smoke identified `CROSS_FLANGE_MAIN_PLATE` or required more exporter evidence.

In `TASKLIST.md`, mark the composite design task as done only if unit tests, report output, and smoke all pass. If smoke lacks lower cross evidence, leave the task open and add a subtask to improve exporter section evidence.

- [ ] **Step 7: Final verification command**

Run:

```powershell
python -m unittest tests.test_composite_main_material_segments tests.test_main_material_segments tests.test_box_main_material_segments tests.test_pipeline_offline tests.test_reports_offline tests.test_h_beam_part_sides
```

Expected: PASS.

- [ ] **Step 8: Commit verification and state updates**

```powershell
git add docs/verification/2026-06-26-composite-main-material-segments.md STATUS.md TASKLIST.md
git commit -m "Verify composite main material segments"
```

## Self-Review

- Spec coverage: Tasks cover N axial segments, lower cross flange main material, stable BOX role output, single primary role with secondary evidence, composite JSON/CSV, pipeline propagation, smoke verification, and no part-number hard-coding.
- Placeholder scan: No TBD/TODO placeholders are present. Every task includes exact files, tests, commands, and expected results.
- Type consistency: The plan consistently uses `CompositeMainMaterialSegment`, `CompositeMainPlate`, `CompositeSegmentType`, `CompositePrimaryRole`, and `classify_composite_main_material_segments`.


