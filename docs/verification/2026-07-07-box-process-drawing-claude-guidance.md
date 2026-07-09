# BOX 柱工序图 Claude v3 指导验证

## Scope

- Design: `docs/design/2026-07-07-box-process-drawing-claude-guidance.md`
- Guidance: `给Codex的工序图技术指导_v3.md`
- Renderer: `src/zijinhua_tekla/reports/box_progressive_dxf.py`
- Offline report bridge: `src/zijinhua_tekla/reports/offline.py`
- Output member: `T3-3GZ-6`
- Output directory: `outputs/box-progressive-drawing-selected-20260706`

## Root Cause From Previous Output

昨天的 DXF 方向仍然偏“阶段示意图”，关键缺陷是：

- 没有把每一步当成累计装配状态来表达。
- 后续步骤容易丢已有焊缝说明。
- PartMark/局部详图在累计数量变多后可能截断掉本步新增零件。
- 折弯处理没有按 v3 的“真实旋转投影 + 普通拼接节点 + Section 标记”锁定。
- DXF 头部没有按 R2007/UTF-8 方式声明，ezdxf 预览链路读中文会乱码。

## What Changed

- `_AssemblyState` 继续作为累计状态源，每步渲染累计 installed parts。
- PartMark 行选择改为“本步新增优先 + 既有补足”，避免后期新增零件没有引出标注。
- 局部详图选择改为“本步新增 detail 优先 + 既有补足”，避免外部件后期步骤看不到 detail。
- 焊缝说明改为累计绘制；每条焊缝线都绑定 `全熔透` 或 `角焊缝 Nmm` 等文字。
- 尺寸链根据累计零件 station 点生成连续分段，本步新增覆盖段高亮。
- segment 投影支持真实倾角；相邻 segment 角度差自动推断折点，并生成 `Section` 标记。
- DXF header 改为 `AC1021` / `ANSI_1252`，以 UTF-8 文件保存，ezdxf 可正确读回中文 TEXT。

## TDD Evidence

### Red

Command:

```powershell
python -m unittest tests.test_box_progressive_dxf
```

Expected failures before implementation:

```text
FAIL: test_renders_cumulative_process_state_with_part_marks_dimension_chain_welds_and_bom
AssertionError: '全熔透' not found in step 2 region

FAIL: test_prioritizes_new_part_marks_when_cumulative_list_is_long
AssertionError: 'Z-P-new / PL1' not found in step 2 region

FAIL: test_infers_small_bend_joint_from_adjacent_axis_segments
AssertionError: 'BEND STRATEGY single_view_true_rotation' not found
```

Encoding regression was also locked with a header assertion before changing DXF header.

### Green

Command:

```powershell
python -m unittest tests.test_box_progressive_dxf
```

Result:

```text
Ran 5 tests in 0.007s
OK
```

## Report Regression

Command:

```powershell
python -m unittest tests.test_box_progressive_dxf tests.test_reports_offline
```

Result:

```text
Ran 6 tests in 0.234s
OK
```

## Selected Member Smoke

Command:

```powershell
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260706_165011 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-3GZ-6 --out outputs\box-progressive-drawing-selected-20260706
```

Result:

- Generated `T3-3GZ-6-box-assembly-drawing-steps.json/csv/md/dxf`.
- JSON summary: 95 parts, 2 axis segments, 29 steps.
- Current selected member has two straight axis segments, so bend Section behavior is test-covered but not triggered in this output.

Key outputs:

- `outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps.dxf`
- `outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-process-drawing-preview.png`
- `outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps-preview-first3.png`

## DXF Text Readback

Command:

```powershell
python -c "import ezdxf; doc=ezdxf.readfile(r'outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps.dxf'); texts=[e.dxf.text for e in doc.modelspace().query('TEXT')][:12]; [print(t.encode('unicode_escape').decode('ascii')) for t in texts]"
```

Result included:

```text
T3-3GZ-6 BOX \u5de5\u5e8f\u56fe
STEP 1 BASE_MAIN_WALL \u57fa\u51c6\u4e3b\u677f
\u5168\u90e8\u901a\u9ad8 6344
```

This proves the DXF TEXT values are correct Unicode. The PNG preview still shows Chinese as square glyphs because the matplotlib render path lacks a Chinese CAD font; the DXF content itself is not mojibake.

## Full Regression

Command:

```powershell
python -m unittest discover -s tests
```

Result:

```text
Ran 119 tests in 1.599s
OK
```

Known warning:

- Existing `openpyxl` `datetime.utcnow()` deprecation warning appears during tests. It is unrelated to this DXF renderer change.

## Manual Preview Notes

The first-three-step preview shows the intended structure:

- left side main view with two-column dimension chain;
- PartMark leader boxes connected to the part locations;
- red current-step geometry and green/white existing annotations;
- right side local detail frames for detail/bolt parts;
- cumulative BOM per step.

Remaining limitations:

- Text placement is still dense on steps with many weld notes; this is readable as a first DXF proof but still needs drafting polish.
- PNG preview is only a review aid; use the DXF in CAD for font-accurate review.
- Section/detail views are still generated only as local detail frames, not full formal Tekla section drawings.

## Post-Review Correction - 2026-07-07

User compared the output with `4.西岑文化艺术中心地上三节柱组立图2026.07.03.dxf` and correctly rejected the previous result.

Measured difference before correction:

- Reference DXF: one Tekla-style sheet, bbox about `596.5 x 420`, 570 entities.
- Previous generated DXF: vertical process scroll, bbox about `640 x 23863.9`, 20,923 entities.

Root cause:

- The renderer stacked all 29 steps vertically in one modelspace.
- Each stacked frame repeated cumulative BOM/PartMark/weld/detail content, so the drawing became unreadable.
- The reference drawing is one stage sheet, not a long scroll of all stages.

Correction made:

- `box-assembly-drawing-steps.dxf` now renders a single stage sheet by default.
- Default stage selection is the first `ADD_INTERNAL_GROUP` step, which better matches the reference concept of “one assembly stage”.
- A specific stage can be rendered by passing `render_step_no`.
- The sheet bbox is now `599 x 420`.
- PartMark placement is anchored near the target station and old part marks are limited, reducing crossing leader lines.
- BOM is kept at the top-right and row-limited instead of growing down the page.

Verification after correction:

```powershell
python -m unittest tests.test_box_progressive_dxf tests.test_reports_offline
```

```text
Ran 6 tests in 0.119s
OK
```

```powershell
python -m unittest discover -s tests
```

```text
Ran 119 tests in 1.521s
OK
```

Generated comparison previews:

- Reference: `outputs\compare-reference-xicen-assembly.png`
- Current corrected output: `outputs\compare-ours-current-box-process.png`

Remaining gap after correction:

- The current output is no longer structurally wrong as a long scroll, but it is still not equivalent to Tekla’s real assembly drawing.
- The main remaining gap is geometry fidelity: the current renderer still uses station/lane simplified part projections, not true per-part projected contours and true section/detail drawing primitives.
- Next implementation should consume/export drawing-view geometry or generate Tekla drawing objects directly, not keep improving the simplified station renderer indefinitely.
