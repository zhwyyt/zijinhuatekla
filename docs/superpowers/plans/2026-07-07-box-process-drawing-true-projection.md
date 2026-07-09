# BOX Process Drawing True Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade BOX process DXF output from station/lane sketches to multi-page process sheets that consume true per-part projected geometry, part marks, dimensions, and bend/curve annotations.

**Architecture:** Keep the existing step planner as the process grouping source. Upgrade the report payload to carry a drawing geometry snapshot per part, then make the DXF renderer prefer true projection edges/arcs and fall back to the old station rectangles only when geometry is unavailable.

**Tech Stack:** Python stdlib, existing offline report pipeline, existing handwritten DXF writer, `unittest`.

---

### Task 1: Lock The Data Contract

**Files:**
- Modify: `I:\zijinhuatekla\tests\test_reports_offline.py`
- Modify: `I:\zijinhuatekla\src\zijinhua_tekla\reports\offline.py`

- [ ] **Step 1: Write the failing test**

Add a report test proving `_drawing_part_snapshots()` preserves projected geometry from `SolidEdges` as `projectionEdges`.

- [ ] **Step 2: Run the focused test**

Run: `python -m unittest tests.test_reports_offline`

Expected: FAIL because `projectionEdges` is not written yet.

- [ ] **Step 3: Implement the minimal snapshot extraction**

Project each `SolidEdges[].Start/End` from global `X/Z` into 2D drawing edges and store rounded `projectionEdges` on each drawing part snapshot.

- [ ] **Step 4: Re-run the focused test**

Run: `python -m unittest tests.test_reports_offline`

Expected: PASS.

### Task 2: Render True Geometry Pages

**Files:**
- Modify: `I:\zijinhuatekla\tests\test_box_progressive_dxf.py`
- Modify: `I:\zijinhuatekla\src\zijinhua_tekla\reports\box_progressive_dxf.py`

- [ ] **Step 1: Write failing renderer tests**

Change the default renderer expectation from a single selected step to multiple process sheets. Add a geometry test where a skew edge from `projectionEdges` must appear as a projected DXF line rather than a lane rectangle.

- [ ] **Step 2: Run the renderer tests**

Run: `python -m unittest tests.test_box_progressive_dxf`

Expected: FAIL because the renderer still selects one step and ignores projection geometry.

- [ ] **Step 3: Implement multi-sheet rendering and projection-first drawing**

Render every step by default in a 3-column sheet grid. Keep `render_step_no` as an explicit single-stage override. When installed parts contain `projectionEdges`, scale their true projected extents into the main view and draw those edges.

- [ ] **Step 4: Re-run the renderer tests**

Run: `python -m unittest tests.test_box_progressive_dxf`

Expected: PASS.

### Task 3: Bend And Curve Annotations

**Files:**
- Modify: `I:\zijinhuatekla\tests\test_box_progressive_dxf.py`
- Modify: `I:\zijinhuatekla\src\zijinhua_tekla\reports\box_progressive_dxf.py`

- [ ] **Step 1: Write failing annotation tests**

Add a bend test expecting `BEND 8°` near the section marker and an arc test expecting an `ARC` entity plus `R500` radius text.

- [ ] **Step 2: Run the renderer tests**

Run: `python -m unittest tests.test_box_progressive_dxf`

Expected: FAIL because bend angle text and arc primitives are missing.

- [ ] **Step 3: Implement annotations**

Add `ARC` output support, parse `projectionArcs`, render radius labels, and label bend joints without adding break symbols.

- [ ] **Step 4: Re-run the renderer tests**

Run: `python -m unittest tests.test_box_progressive_dxf`

Expected: PASS.

### Task 4: Smoke And Documentation

**Files:**
- Modify: `I:\zijinhuatekla\STATUS.md`
- Modify: `I:\zijinhuatekla\TASKLIST.md`
- Add: `I:\zijinhuatekla\docs\design\2026-07-07-box-process-drawing-true-projection.md`
- Add: `I:\zijinhuatekla\docs\verification\2026-07-07-box-process-drawing-true-projection.md`

- [ ] **Step 1: Run full tests**

Run: `python -m unittest discover -s tests`

Expected: PASS.

- [ ] **Step 2: Regenerate the selected BOX column output**

Run: `python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260706_165011 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-3GZ-6 --out outputs\box-progressive-drawing-selected-20260706`

Expected: rewrites the steps JSON/DXF with `projectionEdges` and multi-sheet true-projection process pages.

- [ ] **Step 3: Record evidence**

Write commands, generated paths, and remaining limitations to the verification doc. Update `STATUS.md` and `TASKLIST.md` with the new true-projection direction.
