# Part Drawing Dimension Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a semantic dimension planning stage that converts plate and hole information into layered dimension chains before collision avoidance, eliminating the seven redundant unplaced hole coordinates in `T3-PX-317`.

**Architecture:** Keep `DimensionGenerator` as the raw requirement inventory. Add `DimensionPlanner` between generation and layout to detect complete rectangular hole grids, merge repeated coordinates, build inner feature chains and outer overall chains, and account for every raw intent. Change `DimensionOptimizer` to place the planned layers without changing their semantic order; keep the existing native DXF `DIMENSION` and shared PDF renderers.

**Tech Stack:** Python 3.12, dataclasses, `unittest`, `ezdxf`, ReportLab.

---

## File Map

- Create `src/zijinhua_tekla/part_drawing/dimension_planner.py`: planning DTOs, rectangular hole-grid recognition, chain construction, callout merging, intent coverage and planning issues.
- Create `tests/test_part_drawing_dimension_planner.py`: planner-level regressions independent of page layout.
- Modify `src/zijinhua_tekla/part_drawing/contracts.py`: add `DIMENSION_PLAN_INCOMPLETE`.
- Modify `src/zijinhua_tekla/part_drawing/dimension_optimizer.py`: consume `DimensionPlan`, reserve planned layer margins and place chains without semantic reordering.
- Modify `src/zijinhua_tekla/part_drawing/pipeline.py`: invoke planner, aggregate planner status/issues and report unplaced planned items.
- Modify `src/zijinhua_tekla/part_drawing/drawing_output.py`: serialize plan provenance carried by placed dimensions; continue emitting native DXF dimensions.
- Modify `tests/test_part_drawing_layout.py`: verify fixed layer ordering and title-block-safe placement.
- Modify `tests/test_part_drawing_output.py`: verify all planned chain segments become native `DIMENSION` entities.
- Modify `tests/test_part_drawing_pipeline.py`: verify planner status propagation and the real-style `3 x 2` grid closure.
- Modify `STATUS.md`, `TASKLIST.md`, and create `docs/verification/2026-07-14-part-drawing-dimension-planner.md`: record the verified result and remaining limits.

### Task 1: Planning DTOs And Complete Rectangular Hole Grids

**Files:**
- Create: `src/zijinhua_tekla/part_drawing/dimension_planner.py`
- Create: `tests/test_part_drawing_dimension_planner.py`
- Modify: `src/zijinhua_tekla/part_drawing/contracts.py`

- [ ] **Step 1: Write failing tests for a complete `3 x 2` grid and a missing-hole non-grid**

Create `tests/test_part_drawing_dimension_planner.py` with a fixture helper that replaces the existing rectangular plate holes:

```python
import unittest
from dataclasses import replace
from pathlib import Path

from zijinhua_tekla.part_drawing.contracts import HoleSnapshot, Point3D
from zijinhua_tekla.part_drawing.dimension_generator import generate_dimension_intents
from zijinhua_tekla.part_drawing.dimension_planner import Axis, PlanItemKind, plan_dimensions
from zijinhua_tekla.part_drawing.feature_recognizer import recognize_plate_features
from zijinhua_tekla.part_drawing.geometry_analyzer import analyze_plate_geometry
from zijinhua_tekla.part_drawing.snapshot_input import load_part_snapshot


FIXTURE = Path(__file__).parent / "fixtures" / "part_drawing" / "rectangular_plate.json"


def _planned(points):
    base = load_part_snapshot(FIXTURE)
    holes = tuple(
        HoleSnapshot(f"H{index}", "ROUND", Point3D(x, y, 30), diameter=22)
        for index, (x, y) in enumerate(points, 1)
    )
    snapshot = replace(base, holes=holes)
    geometry = analyze_plate_geometry(snapshot).geometry
    features = recognize_plate_features(snapshot, geometry).features
    intents = generate_dimension_intents(snapshot, geometry, features).intents
    return plan_dimensions(geometry, features, intents)


class PartDrawingDimensionPlannerTests(unittest.TestCase):
    def test_complete_three_by_two_grid_becomes_unique_axis_chains(self):
        plan = _planned(((20, 25), (100, 25), (180, 25), (20, 75), (100, 75), (180, 75)))
        feature_chains = [item for item in plan.items if item.kind == PlanItemKind.FEATURE_CHAIN]
        by_axis = {item.axis: item for item in feature_chains}
        self.assertEqual((20.0, 80.0, 80.0, 20.0), tuple(segment.value_mm for segment in by_axis[Axis.X].segments))
        self.assertEqual((25.0, 50.0, 25.0), tuple(segment.value_mm for segment in by_axis[Axis.Y].segments))
        self.assertEqual("6-DIA22", plan.callouts[0].display_text)
        self.assertFalse(plan.unresolved_intents)

    def test_missing_cartesian_cell_is_not_planned_as_complete_grid(self):
        plan = _planned(((20, 25), (100, 25), (180, 25), (20, 75), (100, 75)))
        self.assertFalse(any(item.kind == PlanItemKind.FEATURE_CHAIN for item in plan.items))
        self.assertEqual("REVIEW_REQUIRED", plan.status.value)
        self.assertTrue(plan.unresolved_intents)
```

- [ ] **Step 2: Run the planner tests and verify RED**

Run:

```powershell
python -m unittest tests.test_part_drawing_dimension_planner -v
```

Expected: import failure for `dimension_planner` or missing `plan_dimensions`.

- [ ] **Step 3: Add the planning issue code and minimal DTOs**

Add to `IssueCode` in `contracts.py`:

```python
DIMENSION_PLAN_INCOMPLETE = "DIMENSION_PLAN_INCOMPLETE"
```

Create `dimension_planner.py` with these public contracts:

```python
from dataclasses import dataclass
from enum import Enum

from .contracts import DrawingIssue, DrawingStatus, IssueCode
from .feature_recognizer import FeatureType
from .geometry_analyzer import Point2D


GRID_TOLERANCE_MM = 0.1


class Axis(str, Enum):
    X = "X"
    Y = "Y"


class PlanSide(str, Enum):
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class PlanItemKind(str, Enum):
    FEATURE_CHAIN = "FEATURE_CHAIN"
    OVERALL = "OVERALL"


@dataclass(frozen=True)
class PlannedSegment:
    segment_id: str
    start: Point2D
    end: Point2D
    value_mm: float
    source_feature_ids: tuple[str, ...]
    evidence_codes: tuple[str, ...]


@dataclass(frozen=True)
class PlannedChain:
    chain_id: str
    kind: PlanItemKind
    axis: Axis
    side: PlanSide
    layer: int
    segments: tuple[PlannedSegment, ...]


@dataclass(frozen=True)
class PlannedCallout:
    callout_id: str
    center: Point2D
    diameter_mm: float
    display_text: str
    source_feature_ids: tuple[str, ...]
    evidence_codes: tuple[str, ...]


@dataclass(frozen=True)
class DimensionPlan:
    items: tuple[PlannedChain, ...]
    callouts: tuple[PlannedCallout, ...]
    passthrough_intents: tuple
    covered_intent_ids: tuple[str, ...]
    unresolved_intents: tuple
    status: DrawingStatus
    issues: tuple[DrawingIssue, ...]
```

- [ ] **Step 4: Implement complete Cartesian-grid detection and chain construction**

Implement `plan_dimensions(geometry, features, intents)` so it:

```python
def plan_dimensions(geometry, features, intents):
    holes = [item for item in features if item.feature_type == FeatureType.ROUND_HOLE]
    grid = _complete_round_hole_grid(holes)
    if grid is None and len(holes) > 1:
        issue = DrawingIssue(
            IssueCode.DIMENSION_PLAN_INCOMPLETE,
            "round holes do not form one complete rectangular grid",
            False,
            evidence=tuple(item.feature_id for item in holes),
        )
        return DimensionPlan((), (), _non_hole_intents(intents), (), tuple(_hole_intents(intents)), DrawingStatus.REVIEW_REQUIRED, (issue,))
    if grid is None:
        return _single_or_no_hole_plan(geometry, holes, intents)

    x_values, y_values, diameter = grid
    hole_ids = tuple(item.feature_id for item in holes)
    x_chain = _feature_chain(Axis.X, PlanSide.BOTTOM, 1, 0.0, geometry.bounds[2], x_values, hole_ids)
    y_chain = _feature_chain(Axis.Y, PlanSide.LEFT, 1, 0.0, geometry.bounds[3], y_values, hole_ids)
    callout = PlannedCallout(
        "hole-grid-diameter",
        holes[0].anchors[0],
        diameter,
        f"{len(holes)}-DIA{_number(diameter)}",
        hole_ids,
        ("COMPLETE_RECTANGULAR_HOLE_GRID", "EQUAL_DIAMETER"),
    )
    covered = tuple(item.intent_id for item in intents if _is_hole_intent(item, hole_ids))
    return DimensionPlan((x_chain, y_chain), (callout,), _non_hole_intents(intents), covered, (), DrawingStatus.OK, ())
```

`_complete_round_hole_grid()` must cluster coordinates within `0.1 mm`, require one common diameter, require at least two unique X and two unique Y values, and verify that every `(x, y)` Cartesian cell has exactly one hole. `_feature_chain()` must produce consecutive edge-to-coordinate, coordinate-to-coordinate and coordinate-to-edge segments and omit zero-length segments.

- [ ] **Step 5: Run tests and verify GREEN**

Run:

```powershell
python -m unittest tests.test_part_drawing_dimension_planner -v
```

Expected: both tests pass.

- [ ] **Step 6: Commit planner DTOs and grid recognition**

```powershell
git add src/zijinhua_tekla/part_drawing/dimension_planner.py src/zijinhua_tekla/part_drawing/contracts.py tests/test_part_drawing_dimension_planner.py
git commit -m "feat: plan rectangular hole grid dimensions"
```

### Task 2: Overall Layers, Single-Hole Fallback, And Coverage Accounting

**Files:**
- Modify: `src/zijinhua_tekla/part_drawing/dimension_planner.py`
- Modify: `tests/test_part_drawing_dimension_planner.py`

- [ ] **Step 1: Add failing tests for outer overall layers and intent accounting**

Append tests:

```python
def test_overall_dimensions_are_outside_feature_chains(self):
    plan = _planned(((20, 25), (100, 25), (180, 25), (20, 75), (100, 75), (180, 75)))
    by_axis = {}
    for item in plan.items:
        by_axis.setdefault(item.axis, []).append(item)
    for axis_items in by_axis.values():
        feature = next(item for item in axis_items if item.kind == PlanItemKind.FEATURE_CHAIN)
        overall = next(item for item in axis_items if item.kind == PlanItemKind.OVERALL)
        self.assertGreater(overall.layer, feature.layer)

def test_every_raw_intent_is_covered_passthrough_or_unresolved(self):
    plan = _planned(((20, 25), (100, 25), (180, 25), (20, 75), (100, 75), (180, 75)))
    accounted = set(plan.covered_intent_ids)
    accounted.update(item.intent_id for item in plan.passthrough_intents)
    accounted.update(item.intent_id for item in plan.unresolved_intents)
    self.assertEqual(set(plan.source_intent_ids), accounted)

def test_single_hole_keeps_two_coordinates_and_one_diameter(self):
    plan = _planned(((60, 70),))
    self.assertEqual(2, len([item for item in plan.items if item.kind == PlanItemKind.FEATURE_CHAIN]))
    self.assertEqual("DIA22", plan.callouts[0].display_text)
    self.assertFalse(plan.unresolved_intents)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m unittest tests.test_part_drawing_dimension_planner -v
```

Expected: missing overall chains, `source_intent_ids`, or single-hole fallback assertions fail.

- [ ] **Step 3: Implement outer overall chains and complete accounting**

Extend `DimensionPlan` with `source_intent_ids`. Add one-segment overall chains:

```python
def _overall_chains(geometry):
    width, height = geometry.bounds[2], geometry.bounds[3]
    return (
        PlannedChain(
            "overall-x", PlanItemKind.OVERALL, Axis.X, PlanSide.BOTTOM, 2,
            (PlannedSegment("overall-x", Point2D(0, 0), Point2D(width, 0), width, (), ("NORMALIZED_BOUNDS",)),),
        ),
        PlannedChain(
            "overall-y", PlanItemKind.OVERALL, Axis.Y, PlanSide.LEFT, 2,
            (PlannedSegment("overall-y", Point2D(0, 0), Point2D(0, height), height, (), ("NORMALIZED_BOUNDS",)),),
        ),
    )
```

For one hole, build one X chain from the selected vertical datum edge to the center and one Y chain from the selected horizontal datum edge to the center at layer 1, plus a single `DIA22` callout. Keep thickness and unsupported non-hole requirements in `passthrough_intents`. At function exit, compute the union of covered, passthrough and unresolved IDs and raise `AssertionError("dimension intent accounting mismatch")` if it differs from all source intent IDs.

- [ ] **Step 4: Run planner and existing dimension tests**

Run:

```powershell
python -m unittest tests.test_part_drawing_dimension_planner tests.test_part_drawing_dimensions -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit planning layers and accounting**

```powershell
git add src/zijinhua_tekla/part_drawing/dimension_planner.py tests/test_part_drawing_dimension_planner.py
git commit -m "feat: layer planned part dimensions"
```

### Task 3: Layout Planned Chains Without Semantic Reordering

**Files:**
- Modify: `src/zijinhua_tekla/part_drawing/dimension_optimizer.py`
- Modify: `tests/test_part_drawing_layout.py`

- [ ] **Step 1: Replace layout tests with failing plan-driven assertions**

Add a helper that calls `plan_dimensions()` and change `optimize_dimension_layout()` calls to pass a plan. Add:

```python
def test_planned_feature_chain_is_inside_overall_chain(self):
    snapshot = replace(
        self.snapshot,
        holes=tuple(
            HoleSnapshot(f"H{i}", "ROUND", Point3D(x, y, 30), diameter=22)
            for i, (x, y) in enumerate(((20, 25), (100, 25), (180, 25), (20, 75), (100, 75), (180, 75)), 1)
        ),
    )
    geometry = analyze_plate_geometry(snapshot).geometry
    features = recognize_plate_features(snapshot, geometry).features
    intents = generate_dimension_intents(snapshot, geometry, features).intents
    plan = plan_dimensions(geometry, features, intents)
    layout = optimize_dimension_layout(snapshot, geometry, plan, quantity=1)
    by_id = {item.dimension_id: item for item in layout.placed_dimensions}
    self.assertLess(by_id["hole-grid-x-1"].dimension_line_point[1], by_id["overall-x"].dimension_line_point[1])
    self.assertGreater(by_id["hole-grid-y-1"].dimension_line_point[0], by_id["overall-y"].dimension_line_point[0])
    self.assertFalse(layout.unplaced_intents)
```

The inequalities reflect paper coordinates: bottom layers increase downward, while left layers move left as the layer increases.

- [ ] **Step 2: Run layout tests and verify RED**

Run:

```powershell
python -m unittest tests.test_part_drawing_layout -v
```

Expected: `optimize_dimension_layout()` cannot consume `DimensionPlan` or planned IDs are absent.

- [ ] **Step 3: Implement plan-driven layer placement**

Change the public signature:

```python
def optimize_dimension_layout(snapshot, geometry, plan, quantity):
```

Reserve margins from the maximum planned layer per side before fitting the view. Convert each `PlannedSegment` directly to a `PlacedDimension`; compute its baseline only from `chain.side` and `chain.layer`:

```python
LAYER_SPACING_MM = 8.0

def _chain_baseline(chain, view):
    if chain.side == PlanSide.BOTTOM:
        return (view.left + view.right) / 2, view.bottom + 8.0 + chain.layer * LAYER_SPACING_MM
    if chain.side == PlanSide.TOP:
        return (view.left + view.right) / 2, view.top - 8.0 - chain.layer * LAYER_SPACING_MM
    if chain.side == PlanSide.LEFT:
        return view.left - 8.0 - chain.layer * LAYER_SPACING_MM, (view.top + view.bottom) / 2
    return view.right + 8.0 + chain.layer * LAYER_SPACING_MM, (view.top + view.bottom) / 2
```

For all segments in one chain, keep the same perpendicular baseline. Place the planned callout at a local leader candidate near its representative hole. Process passthrough thickness/note intents after planned dimensions. Collision handling may adjust text along the same dimension line, but it must not change `side`, `layer`, source anchors or measured value.

- [ ] **Step 4: Run layout regressions and verify GREEN**

Run:

```powershell
python -m unittest tests.test_part_drawing_layout tests.test_part_drawing_dimension_planner -v
```

Expected: all tests pass and the complete grid has no unplaced planned items.

- [ ] **Step 5: Commit plan-driven layout**

```powershell
git add src/zijinhua_tekla/part_drawing/dimension_optimizer.py tests/test_part_drawing_layout.py
git commit -m "feat: lay out planned dimension chains"
```

### Task 4: Pipeline And Native Output Integration

**Files:**
- Modify: `src/zijinhua_tekla/part_drawing/pipeline.py`
- Modify: `src/zijinhua_tekla/part_drawing/drawing_output.py`
- Modify: `tests/test_part_drawing_output.py`
- Modify: `tests/test_part_drawing_pipeline.py`

- [ ] **Step 1: Add failing pipeline and DXF assertions**

Add a pipeline fixture with a complete `3 x 2` grid and assert:

```python
self.assertEqual(DrawingStatus.OK, item.status)
self.assertFalse(any(issue.code == IssueCode.LAYOUT_OVERFLOW for issue in item.issues))
```

In the output test, build a plan-driven layout and assert:

```python
dimensions = list(dxf.modelspace().query("DIMENSION"))
self.assertEqual(len(self.document.placed_dimensions), len(dimensions))
self.assertFalse(list(dxf.modelspace().query('LINE[layer=="DIMENSION"]')))
self.assertIn("6-DIA22", {item.dxf.text for item in dimensions})
self.assertTrue(all(item.dxf.dimstyle == "PART-CAD-V1" for item in dimensions))
```

- [ ] **Step 2: Run focused integration tests and verify RED**

Run:

```powershell
python -m unittest tests.test_part_drawing_output tests.test_part_drawing_pipeline -v
```

Expected: pipeline still bypasses the planner or callout text/count assertions fail.

- [ ] **Step 3: Integrate the planner in the pipeline**

Update `_process_group()`:

```python
plan = plan_dimensions(group.geometry, feature_result.features, dimension_result.intents)
layout = optimize_dimension_layout(group.representative, group.geometry, plan, group.quantity)
status = _aggregate_status(
    group.status,
    feature_result.status,
    dimension_result.status,
    plan.status,
    layout.status,
)
issues = (
    group.issues
    + feature_result.issues
    + dimension_result.issues
    + plan.issues
    + _layout_issues(group, layout)
)
```

Update layout issue evidence to accept planned items through their stable `dimension_id` or `callout_id`. Do not report covered raw intents as unplaced.

- [ ] **Step 4: Preserve native output and plan provenance**

Keep `_add_dxf_dimension()` as the only linear/radial dimension output path. Extend `PlacedDimension` with `source_feature_ids`, serialize it in drawing JSON, and populate it from planned segments/callouts. Do not add primitive dimension lines.

- [ ] **Step 5: Run focused integration tests and verify GREEN**

Run:

```powershell
python -m unittest tests.test_part_drawing_output tests.test_part_drawing_pipeline -v
```

Expected: all tests pass; DXF dimensions are native and no dimension-layer lines exist.

- [ ] **Step 6: Commit pipeline and output integration**

```powershell
git add src/zijinhua_tekla/part_drawing/pipeline.py src/zijinhua_tekla/part_drawing/drawing_output.py tests/test_part_drawing_output.py tests/test_part_drawing_pipeline.py
git commit -m "feat: render planned native part dimensions"
```

### Task 5: Real T3-PX-317 Smoke, Quality Gates, And Documentation

**Files:**
- Modify: `STATUS.md`
- Modify: `TASKLIST.md`
- Create: `docs/verification/2026-07-14-part-drawing-dimension-planner.md`

- [ ] **Step 1: Run all focused planner and drawing tests**

```powershell
python -m unittest tests.test_part_drawing_dimension_planner tests.test_part_drawing_dimensions tests.test_part_drawing_layout tests.test_part_drawing_output tests.test_part_drawing_pipeline -v
```

Expected: all tests pass.

- [ ] **Step 2: Run the complete regression suite**

```powershell
python -m unittest discover -s tests
```

Expected: exit code `0`, no failures or errors.

- [ ] **Step 3: Generate the real result**

```powershell
python -m zijinhua_tekla.cli draw-parts `
  --snapshot-root I:\tmp\tekla-selected-part-snapshot-smoke-20260713-v2\part-drawing-snapshots `
  --out I:\tmp\tekla-selected-part-drawing-planned-20260714 `
  --cjk-font C:\Windows\Fonts\simhei.ttf
```

Expected: `REJECTED=0`; no `LAYOUT_OVERFLOW` evidence for the former seven duplicate hole coordinates.

- [ ] **Step 4: Read back the DXF with structured APIs**

Run a small `ezdxf` readback that reports:

```text
DIMENSION count
DIMSTYLE names
dimension texts and measurements
LINE[layer="DIMENSION"] count
audit errors/fixes
```

Expected: all chain segments and the merged hole callout are native `DIMENSION`; primitive dimension line count is zero; audit errors/fixes are zero.

- [ ] **Step 5: Inspect the PDF preview**

Render the first PDF page to PNG and verify:

- feature chains are nearer the part than overall dimensions;
- X chain expresses `60/90/90/60` and outer `300`;
- Y chain expresses `93.174/90/60` at model precision and outer `243.174`;
- one merged `6-Ø27` callout is present;
- no text overlaps or enters the title block.

- [ ] **Step 6: Run CCG gates and record evidence**

Run `verify-change` for the working tree and `verify-quality src\zijinhua_tekla\part_drawing`. Write exact commands, test counts, DXF readback, visual findings and remaining risks to `docs/verification/2026-07-14-part-drawing-dimension-planner.md`. Update `STATUS.md` and `TASKLIST.md` with a short link to this evidence.

- [ ] **Step 7: Commit verification records**

```powershell
git add STATUS.md TASKLIST.md docs/verification/2026-07-14-part-drawing-dimension-planner.md
git commit -m "docs: verify planned part dimensions"
```

