# Unified Main Material Segment Classifier Verification

## Scope

将主材分段算法从 BOX 专用入口上抽为统一入口：先识别沿构件主轴的主体板件集合，再按截面体系解释主材角色。

本轮先接两类策略：

- `H/GL/BEAM`：输出 `TOP_FLANGE`、`WEB`、`BOTTOM_FLANGE`。
- `BOX/GKZ fallback`：继续复用既有 BOX wall face 分段候选。

## Implemented Boundary

- `classify_main_material_segment_groups(assembly)` 作为统一入口。
- `T3-6GL-110` 这类 GL 梁通过 `name` 语义和主轴 station 输出：
  - 上翼缘：`TOP_FLANGE`
  - 腹板：`WEB`
  - 下翼缘分段：`BOTTOM_FLANGE`
- BOX/GKZ 构件继续输出 `BOX_WALL_FACE` 角色摘要。
- 统一输出仍复用 `BoxMainMaterialSegmentGroup` 数据结构，保证现有 JSON/CSV 报告兼容。

## Regression Tests

新增 `tests\test_main_material_segments.py`：

- `test_classifies_gl_member_top_web_and_bottom_flange_segments`
  - 上翼缘 `T3-P-4866`
  - 腹板 `T3-P-4753`
  - 下翼缘分段集合 `T3-P-4863;T3-P-5555;T3-P-4862`
  - 加劲板 `T3-P-4653` 不进入主材集合。
- `test_falls_back_to_box_strategy_for_box_member`
  - BOX/GKZ 仍走原 wall face 分段策略。

## Verification Commands

```powershell
python -m unittest tests.test_main_material_segments tests.test_box_main_material_segments
```

结果：11 tests OK。

```powershell
python -m unittest tests.test_pipeline_offline tests.test_reports_offline tests.test_main_material_segments tests.test_box_main_material_segments
```

结果：13 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m unittest discover -s tests
```

结果：61 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

## GL Smoke

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_135923 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-6GL-110 --out outputs\main-material-gl-smoke-20260623
```

输出文件：

- `outputs\main-material-gl-smoke-20260623\T3-6GL-110-box-main-material-segment-groups.json`
- `outputs\main-material-gl-smoke-20260623\T3-6GL-110-box-main-material-segment-groups.csv`

结果摘要：

- `TOP_FLANGE`：`T3-P-4866`，`CONTINUOUS`，station `0 ~ 13114.9`。
- `WEB`：`T3-P-4753`，`CONTINUOUS`，station `0 ~ 13114.9`。
- `BOTTOM_FLANGE`：`T3-P-4863;T3-P-5555;T3-P-4862`，`CONTINUOUS`，station 覆盖 `0 ~ 13114.9`。

## BOX Regression Smoke

对 `I:\xingcaisuanfa\cache\20260623_103323` 的 `T3-5GKZ-10` 使用统一入口复核：

- 候选组：201。
- 连续性分布：`INSUFFICIENT_EVIDENCE=175`、`NEAR_CONTINUOUS=12`、`GAPPED=14`。
- 最大 group 零件数：4。
- 修正后的 13 个主材分段确认集合召回：`13/13`。

## Remaining Risk

- 当前 H/GL 策略强利用 Tekla `name` 中的 `上翼缘/下翼缘/腹板` 语义；如果后续导出缺少这些语义，需要用截面几何和板件方向补强。
- 报告文件名仍沿用 `box-main-material-segment-groups`，后续应改为通用 `main-material-segment-groups` 并保留兼容输出。
- T 型、十字型、圆管等截面还需要新增策略，不应硬套 H/GL 或 BOX 逻辑。
