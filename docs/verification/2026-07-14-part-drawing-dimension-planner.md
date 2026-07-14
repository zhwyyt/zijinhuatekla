# 零件图尺寸规划层验证

## Scope

- 在 `DimensionGenerator` 与 `DimensionOptimizer` 之间新增 `DimensionPlanner`。
- 先按零件外轮廓和孔阵规划尺寸链、侧边与层级，再在固定层内布局。
- 完整 `N x M`、`N x 1` 和 `1 x N` 同径孔阵按唯一行列坐标生成连续尺寸链。
- 总尺寸位于特征定位链外层；孔组只保留一个数量/孔径引出。
- DXF 继续使用原生 `DIMENSION`，drawing JSON 记录每个尺寸的 feature 来源。

## Automated Verification

专项命令：

```powershell
python -m unittest tests.test_part_drawing_dimension_planner tests.test_part_drawing_dimensions tests.test_part_drawing_layout tests.test_part_drawing_output tests.test_part_drawing_pipeline -v
```

结果：`Ran 30 tests ... OK`。

全量命令：

```powershell
python -m unittest discover -s tests
```

结果：`Ran 183 tests ... OK`。仅存在既有 openpyxl `datetime.utcnow()` deprecation warning，不影响断言。

覆盖的关键回归：

- `3 x 2` 完整孔阵归并为 X/Y 连续链，首尾边距和中间间距准确。
- 单排三孔继续规划为完整孔组，不因二维规划器回归。
- 缺一个孔的非完整笛卡尔阵列不会被误判，进入 `DIMENSION_PLAN_INCOMPLETE`。
- 单孔保留两向定位和一次孔径引出。
- 每个原始 intent 必须属于 covered、passthrough 或 unresolved，禁止静默丢失。
- 特征尺寸链层级严格位于同侧总尺寸内侧。
- 规划链段和孔径引出全部输出原生 DXF `DIMENSION`，不存在 `LINE[layer="DIMENSION"]` 替代物。

## Real T3-PX-317 Smoke

输入：

```text
I:\tmp\tekla-selected-part-snapshot-smoke-20260713-v2\part-drawing-snapshots
```

输出：

```text
I:\tmp\tekla-selected-part-drawing-planned-20260714
```

命令：

```powershell
python -m zijinhua_tekla.cli draw-parts `
  --snapshot-root I:\tmp\tekla-selected-part-snapshot-smoke-20260713-v2\part-drawing-snapshots `
  --out I:\tmp\tekla-selected-part-drawing-planned-20260714 `
  --cjk-font C:\Windows\Fonts\simhei.ttf
```

结果：

- batch：`OK=1 / REVIEW_REQUIRED=0 / REJECTED=0`；原 7 个逐孔定位 `LAYOUT_OVERFLOW` 全部消失。
- 10 个原生尺寸：X 链 `60/90/90/60`，Y 链精确测量 `93.174/90/60.001`，总尺寸 `300/243.174`，孔组引出 `6-Ø27`。
- 尺寸显示遵循 `partCadDimensionStyle.v1` 整数精度，drawing JSON 保留精确 `measured_value_mm`。
- 所有尺寸样式为 `PART-CAD-V1`；普通 dimension-layer line 数量为 `0`。
- `ezdxf.audit()`：`0 errors / 0 fixes`。
- drawing JSON `issues=[]`，每个规划尺寸记录 `source_feature_ids` 和 `evidence_codes`。

输出文件：

- `I:\tmp\tekla-selected-part-drawing-planned-20260714\parts\T3-PX-317\T3-PX-317.dxf`
- `I:\tmp\tekla-selected-part-drawing-planned-20260714\parts\T3-PX-317\T3-PX-317.pdf`
- `I:\tmp\tekla-selected-part-drawing-planned-20260714\parts\T3-PX-317\T3-PX-317.drawing.json`
- 预览：`outputs\part-drawing-planned-preview\T3-PX-317.png`

## Manual Visual Review

- 横向孔定位链位于板件下方内层，总长 `300` 位于外层。
- 纵向孔定位链位于板件左侧内层，总宽 `243` 位于外层。
- 孔位没有逐孔重复坐标，孔组只出现一个 `6-Ø27` 引出。
- 尺寸文字、孔径引线和标题信息没有互相覆盖，也没有进入标题栏保护区。
- 页面为 A3 横向且非空，关键文字可读。

## Quality Gates

- `verify-change`：各代码提交前均通过。
- `verify-quality src\zijinhua_tekla\part_drawing`：通过，`0 errors / 15 warnings`。
- 新增路径的非阻断告警包括 `_optimize_planned_layout` 59 行/复杂度 13、`_complete_round_hole_grid` 复杂度 12、`_single_or_no_hole_plan` 6 个参数。当前不为消除告警扩大本阶段重构范围，后续增加更多孔阵类型前应拆分。

## Remaining Boundaries

- 当前自动孔阵规划只覆盖同径完整笛卡尔孔阵和单孔；缺孔阵、混合孔径阵列和非正交阵列进入规划复核，不猜测尺寸链。
- 当前合并等间距仍逐段显示 `90/90`，尚未压缩为 `2@90`；信息完整，不阻断出图。
- 本轮完成 `ezdxf` 结构化读回和人工 PDF 预览，没有取得 AutoCAD GUI/Core Console 正式打开审计结论。
- `OK` 表示自动规划和图面布局完整，仍不等于生产放行。

