# Part Drawing V2 Geometry Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade selected-part extraction to `partDrawingSnapshot.v2`, preserve complete final/operative solid evidence, and use it to generate center marks, native hole-group MULTILEADER annotations, and evidence-backed bevel lines.

**Architecture:** The C# exporter writes source facts only: part form, full faces/ordered loops/edges/vertices, principal-face relations and operation solids. Python accepts v1/v2, derives manufacturing features and drawing plans, and renders native CAD objects. Project-level Steel Semantic Model definitions remain outside this work.

**Tech Stack:** Tekla Structures 2017 Open API, C#/.NET Framework 4.8, Python 3.12, dataclasses, `unittest`, xUnit, ezdxf 1.4.3, ReportLab.

---

## Working Directories

- Consumer: `I:\tmp\zijinhuatekla-part-drawing-engine`, branch `codex/offline-part-drawing-engine`.
- Exporter: `I:\tmp\xingcaisuanfa-part-snapshot-exporter`, branch `codex/part-drawing-snapshot-exporter`.
- Exporter bin/obj changes already exist from prior builds and must not be committed or reverted.

### Task 1: Center Marks And Native Hole-Group MULTILEADER

**Consumer files:**
- Modify `src/zijinhua_tekla/part_drawing/dimension_optimizer.py`
- Modify `src/zijinhua_tekla/part_drawing/drawing_output.py`
- Modify `tests/test_part_drawing_output.py`
- Modify `tests/test_part_drawing_layout.py`

- [ ] Add failing tests asserting two `PART_CENTER` lines per round hole, one `MULTILEADER` for a hole group, and no diameter `DIMENSION` carrying the group text.
- [ ] Run the focused tests and confirm RED because center lines and `PlacedCallout` do not exist.
- [ ] Add `PlacedCallout` and `PartDrawingLayout.placed_callouts`; keep callouts separate from `PlacedDimension`.
- [ ] Add center primitives in `build_part_drawing_document()`:

```python
def _round_hole_center_lines(feature, transform):
    center = transform.point(feature.anchors[0])
    radius = float(feature.parameters["diameter"]) * transform.scale / 2.0
    extent = radius + 2.0
    return (
        DrawingLine(center[0] - extent, center[1], center[0] + extent, center[1], "PART_CENTER"),
        DrawingLine(center[0], center[1] - extent, center[0], center[1] + extent, "PART_CENTER"),
    )
```

- [ ] Add a versioned `PART-CALLOUT-V1` MLEADER style and render `PlacedCallout` with `modelspace.add_multileader_mtext()`; use shared semantic text `6Φ27` and an Arial-compatible DXF text style.
- [ ] Keep the existing PDF leader renderer but make it consume `PlacedCallout`.
- [ ] Run output/layout tests and verify GREEN.
- [ ] Commit consumer changes as `feat: add native part callouts and center marks` after `verify-change`.

### Task 2: Python V2 Contract With V1 Compatibility

**Consumer files:**
- Modify `src/zijinhua_tekla/part_drawing/contracts.py`
- Modify `src/zijinhua_tekla/part_drawing/snapshot_input.py`
- Create `tests/fixtures/part_drawing/v2_plate_geometry.json`
- Modify `tests/test_part_drawing_contracts.py`

- [ ] Add a failing v2 parser test covering `partForm`, final faces, ordered loops, proven/unresolved edges, principal face ids and operative solid geometry.
- [ ] Verify v1 parser regressions still pass and the v2 test fails as unsupported schema.
- [ ] Add immutable DTOs `SolidVertexSnapshot`, `SolidEdgeSnapshot`, `SolidLoopSnapshot`, `SolidFaceSnapshot`, `SolidGeometrySnapshot`, `OperationSnapshot` and `QualityIssueSnapshot`.
- [ ] Accept both `partDrawingSnapshot.v1` and `.v2`; map v1 to empty extended evidence and require v2 principal faces for `FLAT_PLATE`.
- [ ] Reject malformed face references and duplicate ids; retain `UNKNOWN/UNRESOLVED` curves without converting them to ARC.
- [ ] Run contract tests and commit as `feat: accept v2 part geometry evidence` after `verify-change`.

### Task 3: C# V2 DTO And Pure Geometry Evidence

**Exporter files:**
- Modify `TeklaSectionClassifier/PartDrawingSnapshotContracts.cs`
- Create `TeklaSectionClassifier/PartDrawingSolidEvidence.cs`
- Modify `TeklaSectionClassifier/PartDrawingSnapshotBuilder.cs`
- Create `TeklaSectionClassifier.Tests/PartDrawingSolidEvidenceTests.cs`
- Modify `TeklaSectionClassifier.Tests/PartDrawingSnapshotBuilderTests.cs`

- [ ] Add failing xUnit tests for two principal planar faces, ordered edge ids, wedge/bevel face evidence, unresolved curved edge and operative solid serialization.
- [ ] Run `dotnet test` and verify RED for missing v2 contracts.
- [ ] Add v2 DTOs matching the Python fixture exactly. Use stable per-snapshot ids (`F1`, `E1`, `V1`) and explicit evidence status.
- [ ] Implement pure helpers that deduplicate vertices by tolerance, preserve loop order, assign edge adjacency and select the largest valid opposite-normal face pair as principal faces.
- [ ] Make builder output `partDrawingSnapshot.v2` and retain existing identity, material, frame, holes and legacy contour projection for compatibility.
- [ ] Run C# tests and commit source/test files only as `feat: define v2 part solid evidence` after `verify-change`.

### Task 4: Tekla Final And Operative Solid Extraction

**Exporter files:**
- Modify `TeklaSectionClassifier/Tekla2017PartDrawingSnapshotExporter.cs`
- Modify `TeklaSectionClassifier/PartDrawingOperationMapper.cs`
- Modify `TeklaSectionClassifier.Tests/PartDrawingSnapshotBuilderTests.cs`

- [ ] Add adapter-facing tests using neutral extracted face/edge facts; Tekla runtime objects remain outside unit tests.
- [ ] Replace single `ExtractBestFaceLoops()` evidence with full face enumeration:

```text
Face -> surface relation/normal -> ordered Loop -> ordered vertices
Solid Edge -> start/end/type -> adjacent face assignment
```

- [ ] Preserve Tekla curved edges without center as `UNKNOWN/UNRESOLVED`.
- [ ] Enumerate each Boolean cutter operative part solid with the same extractor; retain bounds only as secondary metadata.
- [ ] Set `partForm` from actual Tekla runtime type/profile and add quality issues for unsupported bend/curve evidence.
- [ ] Build Runner and run C# tests; commit source/test files only as `feat: export complete selected part solids` after `verify-change`.

### Task 5: Cross-Language V2 Contract

**Both repositories:**
- Exporter test output fixture
- Consumer `tests/test_part_drawing_contracts.py`

- [ ] Serialize a deterministic C# v2 fixture containing two principal faces, a wedge operation and one unresolved curve.
- [ ] Read the exact C# JSON with Python `load_part_snapshot()`; assert schema, ids, topology, evidence and operation geometry without field conversion.
- [ ] Verify Python reserialization/manifest retains evidence ids.
- [ ] Run focused C# and Python tests and commit fixture/contract changes in their owning repositories.

### Task 6: Strict Bevel Recognition And Drawing Evidence

**Consumer files:**
- Modify `src/zijinhua_tekla/part_drawing/feature_recognizer.py`
- Modify `src/zijinhua_tekla/part_drawing/dimension_generator.py`
- Modify `src/zijinhua_tekla/part_drawing/dimension_planner.py`
- Modify `src/zijinhua_tekla/part_drawing/drawing_output.py`
- Modify `tests/test_part_drawing_features.py`
- Modify `tests/test_part_drawing_output.py`

- [ ] Add failing tests for a proven single-edge bevel and counterexamples: congruent faces, topology mismatch and multiple unexplained offsets.
- [ ] Recognize `BEVEL_EDGE` only when opposite principal faces and/or operative solid prove one corresponding edge setback; output edge, face side, setback, angle status and evidence ids.
- [ ] Compute angle only from proven thickness/setback geometry; otherwise preserve the bevel line with `REVIEW_REQUIRED` and no guessed angle.
- [ ] Add `BEVEL` layer primitives and an optional planned callout. Serialize feature evidence in drawing JSON.
- [ ] Run feature/output/pipeline tests and commit as `feat: draw evidence-backed plate bevels` after `verify-change`.

### Task 7: Real Tekla T3-PX-317 Closure

**Outputs and docs:**
- Real export under `I:\tmp`
- Consumer `STATUS.md`, `TASKLIST.md`
- Create `docs/verification/2026-07-14-part-drawing-v2-geometry-smoke.md`

- [ ] Build and run the v2 exporter against the currently selected `T3-PX-317`.
- [ ] Record only summary counts in conversation: faces, edges, vertices, principal faces, operations and unresolved evidence.
- [ ] Run the consumer and generate DXF/PDF/drawing JSON.
- [ ] Read back DXF and assert: 12 center lines for six holes, one `MULTILEADER` with `6Φ27`, no group-diameter DIMENSION, at least one `BEVEL` primitive, native linear dimensions, audit `0/0`.
- [ ] Render and inspect PDF/DXF preview against the Tekla screenshot; verify bevel side/direction, center marks, leader target and no overlap.
- [ ] Run C# tests/build, Python focused tests and full Python regression.
- [ ] Run `verify-change` in both repositories and `verify-quality` on the consumer part drawing module.
- [ ] Write exact evidence and remaining unsupported cases to the verification document; update STATUS/TASKLIST.
- [ ] Commit only scoped documentation changes.

## Stop Conditions

- If Tekla 2017 cannot expose face topology or operative solid geometry reliably, stop after recording the exact missing API evidence; do not infer bevels from bounds.
- If the real part is no longer selected, stop before real smoke and request reselection; synthetic tests do not replace real acceptance.
- If v2 reveals curved edges without parameters, retain `UNRESOLVED`; do not approximate them as arcs.
- Bent/curved plates remain exportable evidence but drawing-rejected until separate real samples and unfolding design exist.

