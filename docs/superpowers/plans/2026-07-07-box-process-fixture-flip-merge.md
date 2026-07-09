# BOX Process Fixture Flip Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make BOX process drawing steps reflect real fabrication: fixture/base placement, reasonable split-plate merging, and flip-stage planning with side-weld carry-along.

**Architecture:** Keep `build_box_assembly_drawing_steps()` as the step planner entrypoint. Add fixture/flip metadata into `BoxAssemblyDrawingStep.evidence_summary` and merge external cluster drafts by planned flip stages before numbering.

**Tech Stack:** Python stdlib, existing dataclasses, `unittest`.

---

### Task 1: Fixture Base And Split Plate Merge

**Files:**
- Modify: `I:\zijinhuatekla\tests\test_box_assembly_drawing_steps.py`
- Modify: `I:\zijinhuatekla\src\zijinhua_tekla\classifiers\box_assembly_drawing_steps.py`

- [x] **Step 1: Write failing tests**

Add a test where the bottom/base main wall is two contiguous plates on the same face. Expected: one `BASE_MAIN_WALL` step includes both ids and has `fixture_face=FACE_BOTTOM`.

- [x] **Step 2: Run focused tests**

Run: `python -m unittest tests.test_box_assembly_drawing_steps`

Expected: FAIL because fixture metadata and explicit title are missing.

- [x] **Step 3: Implement minimal fixture metadata**

Update main wall grouping to score fixture face and set `fixture_face`, `fixture_role`, and a worker-facing title on the base step.

- [x] **Step 4: Re-run focused tests**

Run: `python -m unittest tests.test_box_assembly_drawing_steps`

Expected: PASS for fixture merge behavior.

### Task 2: Flip Stage Merge

**Files:**
- Modify: `I:\zijinhuatekla\tests\test_box_assembly_drawing_steps.py`
- Modify: `I:\zijinhuatekla\src\zijinhua_tekla\classifiers\box_assembly_drawing_steps.py`

- [x] **Step 1: Write failing tests**

Add two external clusters: `FACE_A` marked `MUST_TOP`, `FACE_B` marked `CAN_SIDE`. Expected: one external step with both parts, `up_face=FACE_A`, `side_work_faces=FACE_B`, and title containing `翻面`/`侧焊`.

- [x] **Step 2: Run focused tests**

Run: `python -m unittest tests.test_box_assembly_drawing_steps`

Expected: FAIL because external clusters are still emitted one cluster per step.

- [x] **Step 3: Implement flip stage planning**

Add face normalization, access classification, four-face ring helpers, flip plan generation, and external draft merging by planned stage.

- [x] **Step 4: Re-run focused tests**

Run: `python -m unittest tests.test_box_assembly_drawing_steps`

Expected: PASS.

### Task 3: Surface Metadata In DXF Notes

**Files:**
- Modify: `I:\zijinhuatekla\src\zijinhua_tekla\reports\box_progressive_dxf.py`
- Modify: `I:\zijinhuatekla\tests\test_box_progressive_dxf.py`

- [x] **Step 1: Write a failing DXF note test**

Expect `FIXTURE` or `UP FACE` note text from `evidence_summary`.

- [x] **Step 2: Run renderer tests**

Run: `python -m unittest tests.test_box_progressive_dxf`

Expected: FAIL because the note is not surfaced.

- [x] **Step 3: Implement note rendering**

Append fixture/flip summary into `_draw_stage_note()`.

- [x] **Step 4: Re-run renderer tests**

Run: `python -m unittest tests.test_box_progressive_dxf`

Expected: PASS.

### Task 4: Smoke And Docs

**Files:**
- Modify: `I:\zijinhuatekla\STATUS.md`
- Modify: `I:\zijinhuatekla\TASKLIST.md`
- Add: `I:\zijinhuatekla\docs\design\2026-07-07-box-process-fixture-flip-merge.md`
- Add: `I:\zijinhuatekla\docs\verification\2026-07-07-box-process-fixture-flip-merge.md`

- [x] **Step 1: Run all tests**

Run: `python -m unittest discover -s tests`

Expected: PASS.

- [x] **Step 2: Regenerate selected BOX output**

Run: `python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260706_165011 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-3GZ-6 --out outputs\box-progressive-drawing-selected-20260706`

Expected: output JSON/DXF include fixture/flip notes while preserving true projection DXF structure.

- [x] **Step 3: Record evidence**

Write commands, outputs, and remaining limits to the verification doc; update live memory files.
