# BOX Column Main View Assembly Drawing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the card-style BOX progressive DXF with a first usable main-view assembly drawing DXF for BOX columns.

**Architecture:** Keep the existing `boxAssemblyDrawingSteps.v1` planner as the data source. Rework only the DXF renderer and affected tests so the report pipeline still writes the same output file names, but the DXF content becomes a station-scaled main-view drawing with dimensions, part marks, notes, and a stage material table.

**Tech Stack:** Python 3.10+, `unittest`, existing text-based DXF writer, offline report pipeline.

---

## File Structure

- Modify `tests/test_box_progressive_dxf.py`: replace card-style assertions with main-view drawing assertions.
- Modify `tests/test_reports_offline.py`: update report assertion to expect the new DXF title and layer semantics.
- Modify `src/zijinhua_tekla/reports/box_progressive_dxf.py`: implement sheet, main view, dimensions, part marks, stage notes, and material table.
- Add `docs/verification/2026-07-06-box-column-main-view-assembly-drawing.md`: record test and smoke evidence.
- Update `STATUS.md` and `TASKLIST.md`: mark the card-style DXF as superseded by the main-view assembly drawing first pass.

## Task 1: Main-View DXF Test

**Files:**
- Modify: `tests/test_box_progressive_dxf.py`

- [ ] **Step 1: Write the failing test**

Replace the existing card-style test assertions with assertions for:

```python
self.assertIn("A-GKZ-1 BOX assembly main view", dxf)
self.assertIn("DrawingSheet", dxf)
self.assertIn("Part", dxf)
self.assertIn("NewPart", dxf)
self.assertIn("Z-DIMENSIONS", dxf)
self.assertIn("PartMark", dxf)
self.assertIn("Table", dxf)
self.assertIn("OVERALL 3000", dxf)
self.assertIn("STEP 1 BASE_MAIN_WALL", dxf)
self.assertIn("A-P-401 / PL16*900", dxf)
self.assertIn("QTY", dxf)
self.assertNotIn("BOX progressive drawing steps", dxf)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_box_progressive_dxf`

Expected: FAIL because current renderer still emits the card-style title and lacks main-view drawing layers.

## Task 2: Implement Main-View Renderer

**Files:**
- Modify: `src/zijinhua_tekla/reports/box_progressive_dxf.py`

- [ ] **Step 1: Replace the card renderer**

Implement these renderer helpers:

```python
def _draw_sheet(writer, origin_x, origin_y, step, member_id, layout): ...
def _draw_main_view(writer, origin_x, origin_y, step, layout): ...
def _draw_dimensions(writer, origin_x, origin_y, step, layout): ...
def _draw_part_marks(writer, origin_x, origin_y, step, layout): ...
def _draw_stage_table(writer, origin_x, origin_y, step): ...
```

Use station parsing from `step["station_range"]`. Map station to drawing Y with a fixed main view height per sheet. Draw the body outline as a rectangle, draw current new parts as narrow rectangles at the step station range, and draw existing reference as thinner body lines.

- [ ] **Step 2: Run focused test**

Run: `python -m unittest tests.test_box_progressive_dxf`

Expected: PASS.

## Task 3: Report Test Alignment

**Files:**
- Modify: `tests/test_reports_offline.py`

- [ ] **Step 1: Update offline report assertions**

Change the DXF assertions to expect:

```python
self.assertIn("A-GKZ-1 BOX assembly main view", drawing_step_dxf)
self.assertIn("Z-DIMENSIONS", drawing_step_dxf)
self.assertIn("PartMark", drawing_step_dxf)
```

- [ ] **Step 2: Run focused report test**

Run: `python -m unittest tests.test_reports_offline`

Expected: PASS.

## Task 4: Smoke Output and Verification Record

**Files:**
- Add: `docs/verification/2026-07-06-box-column-main-view-assembly-drawing.md`
- Update: `STATUS.md`
- Update: `TASKLIST.md`

- [ ] **Step 1: Regenerate selected member output**

Run:

```powershell
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260706_165011 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-3GZ-6 --out outputs\box-progressive-drawing-selected-20260706
```

Expected: `T3-3GZ-6-box-assembly-drawing-steps.dxf` is rewritten with main-view semantics.

- [ ] **Step 2: Render a PNG preview**

Run a local Python rendering script with `ezdxf` if available. If not available, use Aspose CAD already installed for local analysis.

Expected: write a PNG preview beside the DXF under `outputs\box-progressive-drawing-selected-20260706`.

- [ ] **Step 3: Run regression tests**

Run:

```powershell
python -m unittest tests.test_box_progressive_dxf tests.test_reports_offline
python -m unittest discover -s tests
```

Expected: tests pass, allowing existing warnings only if unrelated and already present.

- [ ] **Step 4: Write verification record**

Record commands, outputs, generated file paths, and remaining limitations in `docs/verification/2026-07-06-box-column-main-view-assembly-drawing.md`.
