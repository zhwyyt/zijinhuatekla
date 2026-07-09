# BOX Column Main View Assembly Drawing Verification

> Superseded on 2026-07-07 by `docs/verification/2026-07-07-box-process-drawing-claude-guidance.md`. This file records the earlier main-view pass; the current verified output is the Claude v3 cumulative process drawing.

## Scope

- Design: `docs/design/2026-07-06-box-column-main-view-assembly-drawing.md`
- Plan: `docs/superpowers/plans/2026-07-06-box-column-main-view-assembly-drawing.md`
- Renderer: `src/zijinhua_tekla/reports/box_progressive_dxf.py`
- Output member: `T3-3GZ-6`
- Output directory: `outputs/box-progressive-drawing-selected-20260706`

## What Changed

The DXF fallback for `box-assembly-drawing-steps` was changed from card-style step summaries to a first main-view assembly drawing pass:

- each step has a sheet frame;
- left side shows a station-scaled BOX column main view;
- current step parts are drawn on `NewPart`;
- body/reference geometry is drawn on `Part`;
- total length and step station range are drawn on `Z-DIMENSIONS`;
- new parts get leader marks on `PartMark`;
- each step has a compact stage material table on `Table`;
- notes and headers use `Text`.

## TDD Evidence

### Red

Command:

```powershell
python -m unittest tests.test_box_progressive_dxf
```

Observed failure before implementation:

```text
FAIL: test_renders_main_view_assembly_drawing_with_dimensions_marks_and_table
AssertionError: 'A-GKZ-1 BOX assembly main view' not found
```

The old renderer still emitted `A-GKZ-1 BOX progressive drawing steps`, confirming the test caught the card-style output.

### Green

Command:

```powershell
python -m unittest tests.test_box_progressive_dxf
```

Result:

```text
Ran 1 test in 0.000s
OK
```

## Report Regression

Command:

```powershell
python -m unittest tests.test_box_progressive_dxf tests.test_reports_offline
```

Result:

```text
Ran 2 tests in 0.109s
OK
```

## Selected Member Smoke

Command:

```powershell
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260706_165011 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-3GZ-6 --out outputs\box-progressive-drawing-selected-20260706
```

Result:

- Rewrote `outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps.dxf`
- DXF includes `T3-3GZ-6 BOX assembly main view`
- DXF includes `STEP 1 BASE_MAIN_WALL 基准主板`
- DXF includes `Z-DIMENSIONS`, `PartMark`, and `Table`

Generated previews:

- `outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps-preview.png`
- `outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps-preview-first3.png`

## Full Regression

Command:

```powershell
python -m unittest discover -s tests
```

Result:

```text
Ran 115 tests in 0.833s
OK
```

Known warning:

- Existing `openpyxl` `datetime.utcnow()` deprecation warning appears during tests. It is unrelated to this DXF renderer change.

## Manual Preview Notes

The PNG preview shows:

- each step is now a drawing sheet rather than a step card;
- the left area contains a vertical main view and station dimensions;
- the current stage has leader marks;
- the right area contains a stage part table.

Remaining first-pass limitations:

- The main view uses simplified rectangular projections because `boxAssemblyDrawingSteps.v1` does not yet include full per-part projected contour geometry.
- Section views are not generated in this pass.
- The complete 29-step PNG is very tall; the first-three-step preview is better for visual review.
- Text placement is functional but still needs CAD drafting polish after user review.
