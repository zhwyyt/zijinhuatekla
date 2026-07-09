# BOX 工序图胎架翻身与步骤合并验证

## Scope

- Design: `docs/design/2026-07-07-box-process-fixture-flip-merge.md`
- Planner: `src/zijinhua_tekla/classifiers/box_assembly_drawing_steps.py`
- DXF renderer: `src/zijinhua_tekla/reports/box_progressive_dxf.py`
- Tests:
  - `tests/test_box_assembly_drawing_steps.py`
  - `tests/test_box_progressive_dxf.py`
- Output directory: `outputs/box-progressive-drawing-selected-20260706`

## RED Evidence

### DXF note missing process semantics

Command:

```powershell
python -m unittest tests.test_box_progressive_dxf
```

Failure before fix:

```text
FAIL: test_renders_fixture_and_flip_notes_from_step_summary
AssertionError: 'FIXTURE FACE_BOTTOM' not found
```

### Real-like external face inference missing

Command:

```powershell
python -m unittest tests.test_box_assembly_drawing_steps
```

Failure before fix:

```text
FAIL: test_infers_external_work_face_from_projected_centroid
AssertionError: 1 != 2
```

Root cause: real external parts do not always carry `mainMaterialEvidence.bodyFaceId`; planner only accepted `FACE_A/B/C/D`, so real `projected_centroid_u/v` evidence could not drive flip-stage merge.

## GREEN Tests

Commands:

```powershell
python -m unittest tests.test_box_assembly_drawing_steps
python -m unittest tests.test_box_progressive_dxf
python -m unittest tests.test_box_assembly_drawing_steps tests.test_box_progressive_dxf
python -m unittest discover -s tests
```

Results:

```text
tests.test_box_assembly_drawing_steps: Ran 4 tests ... OK
tests.test_box_progressive_dxf: Ran 8 tests ... OK
combined: Ran 12 tests ... OK
discover: Ran 125 tests in 1.099s ... OK
```

Known warning: full discovery still emits existing `openpyxl` `datetime.utcnow()` deprecation warnings.

## Selected Member Smoke

Command:

```powershell
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260706_165011 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-3GZ-6 --out outputs\box-progressive-drawing-selected-20260706
```

Generated:

- `outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps.json`
- `outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps.csv`
- `outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps.md`
- `outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps.dxf`

JSON readback:

```text
steps=14
fixture_steps=1
flip_steps=4
step 1  BASE_MAIN_WALL       fixture_face=RADIAL_Y_NEG  new_count=6
step 11 ADD_EXTERNAL_CLUSTER up_face=RADIAL_X_POS       new_count=7
step 12 ADD_EXTERNAL_CLUSTER up_face=RADIAL_Y_POS       new_count=15 flip_from_previous=90
step 13 ADD_EXTERNAL_CLUSTER up_face=RADIAL_X_NEG       new_count=11 flip_from_previous=90
step 14 ADD_EXTERNAL_CLUSTER up_face=RADIAL_Y_NEG       new_count=16 flip_from_previous=90
```

DXF text readback:

```text
FIXTURE RADIAL_Y_NEG
UP FACE RADIAL_X_POS
UP FACE RADIAL_Y_POS
FLIP 90
UP FACE RADIAL_X_NEG
FLIP 90
UP FACE RADIAL_Y_NEG
FLIP 90
```

DXF audit:

```text
audit_errors=0 audit_fixes=0
entities=23193 lines=21621 texts=1506
```

Output sizes after merge:

```text
T3-3GZ-6-box-assembly-drawing-steps.csv     17935
T3-3GZ-6-box-assembly-drawing-steps.dxf   4580113
T3-3GZ-6-box-assembly-drawing-steps.json   855932
T3-3GZ-6-box-assembly-drawing-steps.md       3883
```

## Result

本轮没有回退真实投影图纸结构。当前 `T3-3GZ-6` 从 29 个阶段页收敛为 14 个阶段页：前面仍按底板、侧壁、内部件、盖板表达，外部零件按 4 个翻身面合并。DXF 可读回且 `audit` 无错误。

真实样例未输出 `SIDE WELD`，原因是外部件没有明确 `CAN_SIDE` 证据；合成回归已覆盖相邻侧焊合并，后续可接工艺阈值继续放宽。
