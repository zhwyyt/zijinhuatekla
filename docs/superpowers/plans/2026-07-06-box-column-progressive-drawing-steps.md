# BOX Column Progressive Drawing Steps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first usable BOX column progressive drawing step planner and a Tekla 2017 drawing POC entrypoint.

**Architecture:** Add a focused classifier that consumes existing BOX main wall, inside/outside relation, appendage cluster, and alignment outputs and emits step records. Wire the records through the offline pipeline and report layer. Keep Tekla drawing automation as a separate `tools/` POC that consumes the same JSON contract so CAD/DXF can reuse the data if Tekla drawing control is insufficient.

**Tech Stack:** Python 3.10+ dataclasses/unittest/pandas for offline planning and reports; Tekla Structures 2017 .NET Framework Drawing API for POC; existing `python -m unittest` verification.

---

## File Structure

- Create `src/zijinhua_tekla/classifiers/box_assembly_drawing_steps.py`: dataclasses and planner function.
- Modify `src/zijinhua_tekla/pipeline/offline.py`: add planner output to `OfflinePipelineResult`.
- Modify `src/zijinhua_tekla/reports/offline.py`: write JSON/CSV/Markdown step reports and list paths in the main Markdown.
- Modify `src/zijinhua_tekla/cli.py`: print new report paths.
- Create `tests/test_box_assembly_drawing_steps.py`: focused unit tests for step order, grouping, and cluster handling.
- Modify `tests/test_pipeline_offline.py`: assert pipeline produces drawing steps.
- Modify `tests/test_reports_offline.py`: assert report files and Markdown links.
- Create `tools/tekla2017_progressive_drawing_poc/BoxProgressiveDrawingPoc.csproj`: Tekla 2017 POC project.
- Create `tools/tekla2017_progressive_drawing_poc/Program.cs`: reads steps JSON and attempts active drawing/view object control.
- Create `docs/verification/2026-07-06-box-column-progressive-drawing-steps.md`: verification record.

## Task 1: Step Planner Contract

**Files:**
- Create: `src/zijinhua_tekla/classifiers/box_assembly_drawing_steps.py`
- Test: `tests/test_box_assembly_drawing_steps.py`

- [ ] **Step 1: Write the failing tests**

Add this test file:

```python
import unittest

from zijinhua_tekla.bracket_classifier import AppendageRoleClassification
from zijinhua_tekla.classifiers.box_assembly_drawing_steps import build_box_assembly_drawing_steps
from zijinhua_tekla.classifiers.box_main_material_segments import BoxMainMaterialSegmentGroup, SegmentContinuityLevel
from zijinhua_tekla.classifiers.box_part_spatial_relations import BoxPartSpatialRelation


class BoxAssemblyDrawingStepTests(unittest.TestCase):
    def test_builds_stage_steps_without_single_part_page_explosion(self):
        assembly = _assembly()
        steps = build_box_assembly_drawing_steps(
            assembly=assembly,
            member_id="A-GKZ-1",
            aligned_rows=[],
            main_wall_groups=[_main_wall_group()],
            box_part_spatial_relations=[
                _relation("base", "A-P-base", "MAIN_WALL", "0.0-6000.0"),
                _relation("side_a", "A-P-side-a", "MAIN_WALL", "0.0-6000.0"),
                _relation("side_b", "A-P-side-b", "MAIN_WALL", "0.0-6000.0"),
                _relation("cover", "A-P-cover", "MAIN_WALL", "0.0-6000.0"),
                _relation("int_a", "A-P-int-a", "INSIDE_BODY", "900.0-980.0"),
                _relation("int_b", "A-P-int-b", "INSIDE_BODY", "940.0-1010.0"),
                _relation("ext_root", "A-P-ext-root", "OUTSIDE_ATTACHMENT", "1200.0-1320.0"),
                _relation("ext_rib", "A-P-ext-rib", "OUTSIDE_ATTACHMENT", "1200.0-1320.0"),
            ],
            spatial_classifications=[
                AppendageRoleClassification(
                    cluster_id="100:0",
                    role="Bracket",
                    confidence=0.91,
                    part_ids=["ext_root", "ext_rib"],
                    evidence_codes=["ROOT_LOCAL_ATTACHMENT"],
                )
            ],
        )

        self.assertEqual(
            ["BASE_MAIN_WALL", "ADD_SIDE_WALLS", "ADD_INTERNAL_GROUP", "ADD_COVER_WALL", "ADD_EXTERNAL_CLUSTER"],
            [step.step_type for step in steps],
        )
        internal = steps[2]
        self.assertEqual(["int_a", "int_b"], internal.new_part_ids)
        self.assertIn("station_position", [target.kind for target in internal.dimension_targets])
        self.assertLess(len(steps), len(assembly["parts"]))
        external = steps[-1]
        self.assertEqual(["ext_root", "ext_rib"], external.new_part_ids)
        self.assertIn("appendage_cluster_root_station", [target.kind for target in external.dimension_targets])


def _assembly():
    return {
        "assemblyId": "100",
        "parts": [
            _part("base", "A-P-base", "PL20*500", 0, 6000, "FACE_BOTTOM"),
            _part("side_a", "A-P-side-a", "PL16*500", 0, 6000, "FACE_SIDE_A"),
            _part("side_b", "A-P-side-b", "PL16*500", 0, 6000, "FACE_SIDE_B"),
            _part("cover", "A-P-cover", "PL20*500", 0, 6000, "FACE_TOP"),
            _part("int_a", "A-P-int-a", "PL12*420", 900, 980, "INNER"),
            _part("int_b", "A-P-int-b", "PL12*420", 940, 1010, "INNER"),
            _part("ext_root", "A-P-ext-root", "PL18*260", 1200, 1320, "OUTER"),
            _part("ext_rib", "A-P-ext-rib", "PL12*180", 1200, 1320, "OUTER"),
        ],
        "relationships": [
            {"partIdA": "base", "partIdB": "side_a", "edgeType": "Contact"},
            {"partIdA": "base", "partIdB": "side_b", "edgeType": "Contact"},
            {"partIdA": "side_a", "partIdB": "cover", "edgeType": "Contact"},
            {"partIdA": "int_a", "partIdB": "int_b", "edgeType": "Weld"},
            {"partIdA": "ext_root", "partIdB": "ext_rib", "edgeType": "Weld"},
            {"partIdA": "side_a", "partIdB": "ext_root", "edgeType": "Weld"},
        ],
    }


def _part(part_id, position, profile, start, end, face):
    return {
        "partId": part_id,
        "partPosition": position,
        "name": "PLATE",
        "profileString": profile,
        "mainMaterialEvidence": {
            "axisStationStart": start,
            "axisStationEnd": end,
            "axisStationLength": end - start,
            "bodyFaceId": face,
        },
    }


def _main_wall_group():
    return BoxMainMaterialSegmentGroup(
        assembly_id="100",
        group_type="BOX_MAIN_WALL_CONFIRMED_SET",
        face_id="BOX_MAIN_WALL_CONFIRMED",
        part_ids=["base", "side_a", "side_b", "cover"],
        part_positions=["A-P-base", "A-P-side-a", "A-P-side-b", "A-P-cover"],
        station_ranges="",
        gap_summary="",
        continuity_level=SegmentContinuityLevel.CONTINUOUS,
        evidence_codes=["BOX_MAIN_WALL_CONFIRMED_SET"],
        confidence=0.96,
    )


def _relation(part_id, position, relation, station_range):
    return BoxPartSpatialRelation(
        assembly_id="100",
        part_id=part_id,
        part_position=position,
        relation_to_box_body=relation,
        station_range=station_range,
        section_relation="",
        connected_main_wall_ids=["base"] if relation != "MAIN_WALL" else [],
        evidence_codes=[relation],
        confidence=0.9,
    )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_box_assembly_drawing_steps`

Expected: FAIL with `ModuleNotFoundError` for `box_assembly_drawing_steps`.

- [ ] **Step 3: Implement the planner contract**

Create `src/zijinhua_tekla/classifiers/box_assembly_drawing_steps.py` with dataclasses:

```python
@dataclass(frozen=True)
class DrawingPartMarkTarget:
    part_id: str
    part_position: str
    profile: str
    name: str

@dataclass(frozen=True)
class DrawingDimensionTarget:
    kind: str
    part_ids: list[str]
    from_ref: str
    to_ref: str
    label: str

@dataclass(frozen=True)
class DrawingViewHint:
    view_mode: str
    purpose: str
    preferred_detail: str = "main"

@dataclass(frozen=True)
class BoxAssemblyDrawingStep:
    assembly_id: str
    member_id: str
    step_no: int
    step_type: str
    title: str
    station_range: str
    new_part_ids: list[str]
    visible_part_ids: list[str]
    reference_part_ids: list[str]
    hidden_part_ids: list[str]
    part_mark_targets: list[DrawingPartMarkTarget]
    dimension_targets: list[DrawingDimensionTarget]
    view_hints: list[DrawingViewHint]
    evidence_codes: list[str]
    confidence: float
    issue_category: str = ""
```

Implement `build_box_assembly_drawing_steps(...)` so it:

- Finds main wall ids from `BOX_MAIN_WALL_CONFIRMED_SET`.
- Picks the base wall by longest station length, then stable face/name ordering.
- Adds up to two side walls in one `ADD_SIDE_WALLS` step.
- Defers the remaining main wall as `ADD_COVER_WALL`.
- Groups `INSIDE_BODY` parts by 500 mm station buckets into `ADD_INTERNAL_GROUP`.
- Adds outside appendage parts by `spatial_classifications` cluster as `ADD_EXTERNAL_CLUSTER`.
- Computes `visible_part_ids` cumulatively.
- Computes `hidden_part_ids` as all assembly ids minus visible ids.
- Creates mark targets and dimension targets for each new group.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_box_assembly_drawing_steps`

Expected: PASS.

## Task 2: Pipeline Integration

**Files:**
- Modify: `src/zijinhua_tekla/pipeline/offline.py`
- Modify: `tests/test_pipeline_offline.py`

- [ ] **Step 1: Write the failing pipeline assertion**

In `tests/test_pipeline_offline.py`, import no new helper. Add assertions to the existing BOX pipeline test:

```python
self.assertTrue(result.box_assembly_drawing_steps)
self.assertEqual("BASE_MAIN_WALL", result.box_assembly_drawing_steps[0].step_type)
self.assertIn("A-P-1", result.box_assembly_drawing_steps[0].part_mark_targets[0].part_position)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_pipeline_offline.OfflinePipelineTests.test_run_offline_analysis_coordinates_adapters_features_classifiers_and_quality`

Expected: FAIL with missing `box_assembly_drawing_steps` field.

- [ ] **Step 3: Wire planner into pipeline**

Modify `OfflinePipelineResult`:

```python
box_assembly_drawing_steps: list[BoxAssemblyDrawingStep] = field(default_factory=list)
```

Import:

```python
from ..classifiers.box_assembly_drawing_steps import BoxAssemblyDrawingStep, build_box_assembly_drawing_steps
```

After final `box_part_spatial_relations` are built, call:

```python
box_assembly_drawing_steps = build_box_assembly_drawing_steps(
    assembly=assembly,
    member_id=member_id,
    aligned_rows=aligned,
    main_wall_groups=main_material_groups,
    box_part_spatial_relations=box_part_spatial_relations,
    spatial_classifications=spatial_classifications,
)
```

Return `box_assembly_drawing_steps=box_assembly_drawing_steps`.

- [ ] **Step 4: Run pipeline test**

Run: `python -m unittest tests.test_pipeline_offline.OfflinePipelineTests.test_run_offline_analysis_coordinates_adapters_features_classifiers_and_quality`

Expected: PASS.

## Task 3: Report Output

**Files:**
- Modify: `src/zijinhua_tekla/reports/offline.py`
- Modify: `src/zijinhua_tekla/cli.py`
- Modify: `tests/test_reports_offline.py`

- [ ] **Step 1: Write failing report assertions**

In `tests/test_reports_offline.py`:

- Add one `BoxAssemblyDrawingStep` with one mark target, one dimension target, and one view hint to the `OfflinePipelineResult` fixture.
- Assert path names:

```python
self.assertEqual("A-GKZ-1-box-assembly-drawing-steps.json", paths.box_assembly_drawing_steps_path.name)
self.assertEqual("A-GKZ-1-box-assembly-drawing-steps.csv", paths.box_assembly_drawing_steps_csv_path.name)
self.assertEqual("A-GKZ-1-box-assembly-drawing-steps.md", paths.box_assembly_drawing_steps_md_path.name)
```

- Assert JSON/CSV/Markdown content:

```python
step_rows = json.loads(paths.box_assembly_drawing_steps_path.read_text(encoding="utf-8"))
self.assertEqual("BASE_MAIN_WALL", step_rows["steps"][0]["step_type"])
self.assertIn("box-assembly-drawing-steps.json", markdown)
```

- [ ] **Step 2: Run report test to verify it fails**

Run: `python -m unittest tests.test_reports_offline.OfflineReportTests.test_write_offline_analysis_report_outputs_csv_json_and_markdown_summary`

Expected: FAIL with missing path attribute.

- [ ] **Step 3: Implement report output**

Modify `OfflineReportPaths` to include:

```python
box_assembly_drawing_steps_path: Path
box_assembly_drawing_steps_csv_path: Path
box_assembly_drawing_steps_md_path: Path
```

Create paths in `write_offline_analysis_report`:

```python
box_assembly_drawing_steps_path = out_dir / f"{member_id}-box-assembly-drawing-steps.json"
box_assembly_drawing_steps_csv_path = out_dir / f"{member_id}-box-assembly-drawing-steps.csv"
box_assembly_drawing_steps_md_path = out_dir / f"{member_id}-box-assembly-drawing-steps.md"
```

Write JSON as:

```python
payload = {
    "assembly_id": result.assembly.get("assemblyId", ""),
    "member_id": member_id,
    "source": "boxAssemblyDrawingSteps.v1",
    "steps": [step.to_dict() for step in result.box_assembly_drawing_steps],
}
```

Add flatten helper for CSV and Markdown helper for step summary.

Modify `cli.py` to print the three new paths.

- [ ] **Step 4: Run report test**

Run: `python -m unittest tests.test_reports_offline.OfflineReportTests.test_write_offline_analysis_report_outputs_csv_json_and_markdown_summary`

Expected: PASS.

## Task 4: Tekla 2017 POC Project

**Files:**
- Create: `tools/tekla2017_progressive_drawing_poc/BoxProgressiveDrawingPoc.csproj`
- Create: `tools/tekla2017_progressive_drawing_poc/Program.cs`

- [ ] **Step 1: Create the POC project files**

Create a .NET Framework console project referencing:

- `D:\Program Files\Tekla Structures\2017\nt\bin\plugins\Tekla.Structures.dll`
- `D:\Program Files\Tekla Structures\2017\nt\bin\plugins\Tekla.Structures.Model.dll`
- `D:\Program Files\Tekla Structures\2017\nt\bin\plugins\Tekla.Structures.Drawing.dll`
- `D:\Program Files\Tekla Structures\2017\nt\bin\plugins\Tekla.Structures.Geometry3d.Compatibility.dll`

`Program.cs` should:

- Accept `--steps <path>` and optional `--dry-run`.
- Read the steps JSON using `JavaScriptSerializer`.
- In dry run, print step count and first step visible/new counts.
- In live run, instantiate `DrawingHandler`, check connection status, read active drawing, enumerate drawing `Part` objects, match their `ModelIdentifier.ID` to step part ids, call `HideFromDrawingView()` for non-visible parts, insert marks for new parts, and save active drawing.
- Print clear failure reasons without modifying the model.

- [ ] **Step 2: Build the POC**

Run: `dotnet build tools\tekla2017_progressive_drawing_poc\BoxProgressiveDrawingPoc.csproj`

Expected: build succeeds, or records a concrete framework/tooling failure in verification notes.

## Task 5: Verification Record and Focused Test Pass

**Files:**
- Create: `docs/verification/2026-07-06-box-column-progressive-drawing-steps.md`
- Modify: `TASKLIST.md`
- Modify: `STATUS.md`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m unittest tests.test_box_assembly_drawing_steps tests.test_pipeline_offline tests.test_reports_offline
```

Expected: PASS.

- [ ] **Step 2: Run full test suite**

Run:

```powershell
python -m unittest discover -s tests
```

Expected: PASS with only existing openpyxl deprecation warnings.

- [ ] **Step 3: Write verification record**

Record:

- Design doc path.
- Test commands and results.
- Tekla POC build result.
- Whether live Tekla drawing execution was run.
- If live Tekla was not run, exact next command after user selects a BOX member.

- [ ] **Step 4: Update live memory**

Update `STATUS.md` with the implementation result and next Tekla selection step.

Update `TASKLIST.md` item to either complete the offline step planner or leave Tekla POC live execution as a pending subtask based on actual verification.

- [ ] **Step 5: Run CCG verify-change before commit**

Run:

```powershell
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode working
```

Expected: PASS or explicit warning addressed in verification record.

- [ ] **Step 6: Commit implementation**

Run:

```powershell
git add src tests tools docs STATUS.md TASKLIST.md
git commit -m "feat: add box progressive drawing steps"
```

Expected: commit succeeds on `codex/box-progressive-drawing`.

## Self-Review

- Spec coverage: The plan covers step contract, grouping behavior, report output, Tekla 2017 POC, verification record, and live memory updates.
- Placeholder scan: No task depends on unresolved placeholders; live Tekla execution is explicitly conditional on the user selecting a BOX member.
- Type consistency: Planner field names match the design contract and report output names.
