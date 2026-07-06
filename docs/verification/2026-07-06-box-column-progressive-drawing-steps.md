# BOX Column Progressive Drawing Steps Verification - 2026-07-06

## Scope

- Design: `docs/design/2026-07-06-box-column-progressive-drawing-steps.md`
- Plan: `docs/superpowers/plans/2026-07-06-box-column-progressive-drawing-steps.md`
- Selected Tekla member cache: `cache/20260706_165011`
- Selected member: `T3-3GZ-6`
- Output directory: `outputs/box-progressive-drawing-selected-20260706`

## Offline Planner And Reports

Commands:

```powershell
python -m unittest tests.test_box_assembly_drawing_steps
python -m unittest tests.test_box_progressive_dxf
python -m unittest tests.test_reports_offline.OfflineReportTests.test_write_offline_analysis_report_outputs_csv_json_and_markdown_summary
python -m unittest tests.test_box_assembly_drawing_steps tests.test_box_progressive_dxf tests.test_pipeline_offline tests.test_reports_offline
python -m unittest discover -s tests
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260706_165011 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-3GZ-6 --out outputs\box-progressive-drawing-selected-20260706
```

Results:

- Focused planner test passed.
- DXF renderer test passed.
- Offline report test passed.
- Focused suite passed: `Ran 5 tests ... OK`; existing `openpyxl datetime.utcnow()` deprecation warning only.
- Full suite passed: `Ran 115 tests ... OK`; existing `openpyxl datetime.utcnow()` deprecation warning only.
- `T3-3GZ-6` generated `29` drawing steps:
  - `BASE_MAIN_WALL=1`
  - `ADD_SIDE_WALLS=1`
  - `ADD_INTERNAL_GROUP=7`
  - `ADD_COVER_WALL=1`
  - `ADD_EXTERNAL_CLUSTER=19`

Generated first-view files:

- `outputs/box-progressive-drawing-selected-20260706/T3-3GZ-6-box-assembly-drawing-steps.json`
- `outputs/box-progressive-drawing-selected-20260706/T3-3GZ-6-box-assembly-drawing-steps.csv`
- `outputs/box-progressive-drawing-selected-20260706/T3-3GZ-6-box-assembly-drawing-steps.md`
- `outputs/box-progressive-drawing-selected-20260706/T3-3GZ-6-box-assembly-drawing-steps.dxf`

The DXF preview lays out one panel per step with step title, station range, dimension target kinds, and new part position/profile/name marks. This is the current CAD fallback for reviewing grouping and annotation intent without relying on Tekla drawing editor state.

## Tekla 2017 POC

Commands:

```powershell
dotnet build tools\tekla2017_progressive_drawing_poc\BoxProgressiveDrawingPoc.csproj
tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe --steps outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps.json --step 1 --dry-run
tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe --steps outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps.json --step 1 --create-drawing
```

Results:

- Build passed with `0` warnings and `0` errors.
- Dry run loaded `29` steps and selected `Step 1 BASE_MAIN_WALL`.
- Initial `DrawingHandler.GetConnectionStatus()` failure was traced to missing `SESSIONNAME` in the external process. The POC now sets `SESSIONNAME=Console`, matching the existing Tekla export runner pattern.
- With `SESSIONNAME` fixed, `DrawingHandler` connects and the POC resolves assembly identifier `63737929` from part `63821589`.
- Direct `AssemblyDrawing.Insert()` returns false for `63737929`.
- `DrawingCreator.CreateDrawings(new AutoDrawingRule("ch_column.xdproc"), 63737929, out status)` returns `ok=True` and `status=OPERATION_OK`, so Tekla can create the assembly drawing through AutoDrawing.
- Automatic opening still fails:
  - `AssemblyDrawing.Select()` after AutoDrawing returns false.
  - `DrawingHandler.SetActiveDrawing()` returns false.
  - The UI Drawing List route can select the main part and run the list/filter macros, but the selected drawing still cannot be opened through `SetActiveDrawing`.

## Current Conclusion

First usable review result is available as offline steps plus DXF preview. Tekla drawing automation is partially verified: model/drawing API connection and AutoDrawing creation work; automatic opening of the generated assembly drawing and applying per-step hide/show/marks remains the next Tekla-specific blocker.

## Change Gate

Command:

```powershell
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --mode working
```

Result:

- Passed.
- Info-only notes: new files under `src` and `tests` suggest README updates. Current design and verification records cover this feature-specific change.

## Next Verification Target

Open the generated `T3-3GZ-6` assembly drawing manually in Tekla, then run:

```powershell
tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe --steps outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps.json --step 1
```

Expected next evidence:

- Active drawing is detected.
- Non-step drawing parts are hidden.
- New step parts receive marks.
- Drawing saves without changing the model.
