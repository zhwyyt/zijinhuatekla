# 零件图 CAD 原生尺寸样式验证

## Scope

- 样板来源：项目根目录 `零件标注.dwg` 的只读备份副本。
- 实现范围：已放置尺寸的语义 DTO、CAD 样式、原生 DXF `DIMENSION`、等价 PDF 矢量表达和布局障碍保护。
- 非范围：图框/标题栏整体复制、孔组业务规则和剩余孔定位尺寸链收敛。

样板提取并固化为 `partCadDimensionStyle.v1` 的关键纸面参数：Arial、宽度系数 `0.65`、字高 `2.5 mm`、线性端头 `OBLIQUE`、引线实心箭头、端头 `2.0 mm`、界线偏移 `2.5 mm`、界线超出 `2.0 mm`、文字间隙 `1.0 mm`、整数精度。

## Automated Verification

Focused command:

```powershell
python -m unittest tests.test_part_drawing_dimension_style tests.test_part_drawing_dimensions tests.test_part_drawing_layout tests.test_part_drawing_output tests.test_part_drawing_pipeline -v
```

Result: `Ran 24 tests ... OK`.

Full command:

```powershell
python -m unittest discover -s tests
```

Result: `Ran 174 tests ... OK`. Existing openpyxl `datetime.utcnow()` deprecation warnings remain and do not affect assertions.

CCG gates:

- `verify-change`: passed;
- `verify-quality src\zijinhua_tekla\part_drawing`: passed with `0 errors / 10 warnings`.

The non-blocking quality warnings include existing classifier/parser complexity plus three items touched by this stage: `_place` is 67 lines, `drawing_output.py` is 513 code lines, and `_draw_pdf_dimension_line_with_text_gap` has 7 parameters. They are recorded for a later renderer/layout decomposition; this style task does not add a broad refactor after visual verification.

Covered regressions include:

- sample style parameters and all standard scale measurement factors;
- semantic horizontal/vertical/diameter dimensions;
- `ROUND_HALF_UP` integer display with exact `measured_value_mm` retained;
- native DXF `DIMENSION`, `_OBLIQUE`, `TArial` width and DIMSTYLE values;
- DXF measurement placeholders remain measurement-driven for style-formatted linear values;
- PDF consumes every shared `PlacedDimension`;
- radial leaders remain local to their feature;
- placed dimensions cannot enter the title block.

## Real Smoke

Input:

```text
I:\tmp\tekla-selected-part-snapshot-smoke-20260713-v2\part-drawing-snapshots
```

Final output:

```text
I:\tmp\tekla-selected-part-drawing-cad-style-20260713-v4
```

Command:

```powershell
python -m zijinhua_tekla.cli draw-parts `
  --snapshot-root I:\tmp\tekla-selected-part-snapshot-smoke-20260713-v2\part-drawing-snapshots `
  --out I:\tmp\tekla-selected-part-drawing-cad-style-20260713-v4 `
  --cjk-font C:\Windows\Fonts\simhei.ttf
```

Result:

- batch: `OK=0 / REVIEW_REQUIRED=1 / REJECTED=0`;
- part: `T3-PX-317`, scale `1:2`;
- native DXF dimensions: `13`;
- DXF style: `PART-CAD-V1`;
- DXF measurement factor: `2.0`;
- ezdxf audit: `0 errors / 0 fixes`;
- PDF text contains integer `243` and no longer contains `243.174`;
- preview: `I:\tmp\tekla-selected-part-drawing-cad-style-20260713-v4\T3-PX-317-preview.png`.

The historical renderer left 17 hole-related intents unplaced. The new local radial placement safely places all six diameter annotations and additional location dimensions. Seven collision-unsafe location intents remain explicit:

```text
hole-45416514-2-y
hole-45416514-3-y
hole-45416514-4-y
hole-45416514-5-x
hole-45416514-5-y
hole-45416514-6-x
hole-45416514-6-y
```

Accounting is complete: `13 placed native dimensions + 1 thickness note + 7 unplaced intents = 21 intents`. No intent is silently discarded.

## Manual Review

The final v4 PDF preview was inspected at 150 DPI:

- overall and coordinate dimensions use visible 45-degree oblique ticks;
- extension lines start clear of the contour and pass the dimension line;
- vertical dimension text follows the vertical dimension direction;
- dimension text is compressed and smaller than the old `3.5 mm` annotation text;
- diameter leaders use filled arrows and stay local to each hole;
- no leader crosses the whole part;
- no dimension text or line enters the title information region;
- the page is nonblank, A3 landscape, and key text is readable.

AutoCAD 2025 Core Console was started against the final DXF, but the scripted `AUDIT/QUIT` sequence did not exit under the installed language prompt and was terminated. Therefore this record does not claim a completed AutoCAD console audit; strict CAD GUI/console opening remains an external manual check. The DXF did pass ezdxf readback and audit with no errors or fixes.

## Remaining Risk

The remaining seven location dimensions should be expressed as a coordinated hole-group/common-datum chain rather than by increasing band capacity. `REVIEW_REQUIRED` and `LAYOUT_OVERFLOW` must remain until that rule is designed and verified.
