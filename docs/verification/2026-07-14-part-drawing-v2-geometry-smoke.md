# Part Drawing V2 Geometry Smoke

## Scope

- Target: `T3-PX-317 / partId=45416496 / PL16`.
- Exporter: `I:\tmp\xingcaisuanfa-part-snapshot-exporter`, branch `codex/part-drawing-snapshot-exporter`.
- Consumer: `I:\tmp\zijinhuatekla-part-drawing-engine`, branch `codex/offline-part-drawing-engine`.
- Contract: `partDrawingSnapshot.v2` with v1 reader compatibility.

## Real Tekla Evidence

The selected part was exported to:

```text
I:\tmp\tekla-selected-part-v2-20260714\part-drawing-snapshots\T3-PX-317-45416496.json
```

Evidence summary:

- final solid: 7 faces, 15 edges, 10 vertices;
- principal faces: `F5,F3`;
- Boolean operations: 1, operative solid faces: 5;
- unresolved final edges: 0;
- recognized bevel: `F5,F3,E1,E10`;
- setback: `13.999995 mm`, plate thickness: `16 mm`;
- angle: `48.814085 deg`, status `PROVEN` because principal-face separation matches thickness.

No part position, project name, fixed coordinate or Boolean bounds rule is used by the bevel recognizer.

## Drawing Readback

Generated files:

```text
I:\tmp\tekla-selected-part-drawings-v2-20260714\parts\T3-PX-317\T3-PX-317.dxf
I:\tmp\tekla-selected-part-drawings-v2-20260714\parts\T3-PX-317\T3-PX-317.pdf
I:\tmp\tekla-selected-part-drawings-v2-20260714\parts\T3-PX-317\T3-PX-317.drawing.json
```

DXF readback:

- `PART_CENTER` lines: 12 for six holes;
- native `MULTILEADER`: 1, semantic text Unicode code points equal `6\u03a627`;
- native `DIMENSION`: 9;
- fake hole-group diameter dimensions: 0;
- `BEVEL` lines: 1;
- ezdxf audit: 0 errors, 0 fixes.

PDF preview was rendered and inspected. The bevel line is parallel to the lower plate edge and offset inward by about 14 mm. Hole center marks, the hole-group leader and planned dimension levels do not overlap.

## Automated Verification

```powershell
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj --no-build --no-restore
# 34 passed

dotnet build TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj --no-restore
# 0 warnings, 0 errors

python -m unittest tests.test_part_drawing_contracts tests.test_part_drawing_features tests.test_part_drawing_dimensions tests.test_part_drawing_dimension_planner tests.test_part_drawing_layout tests.test_part_drawing_output tests.test_part_drawing_pipeline
# 46 passed

python -m unittest discover -s tests
# 190 passed
```

## Remaining Boundaries

- `BENT_PLATE`, curved plates and profiles can preserve v2 evidence but remain blocked by `PART_FORM_UNSUPPORTED_FOR_DRAWING` for automatic drawing.
- Curves without native parameters remain `UNKNOWN/UNRESOLVED`; they are not approximated as arcs.
- AutoCAD GUI/Core Console opening was not run in this smoke; native entities were read back with ezdxf and the PDF was visually inspected.
