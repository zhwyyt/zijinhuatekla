# Composite Main Material Segments Verification

日期：2026-06-27

## Scope

验证组合截面构件主材识别：沿构件主轴切 N 个截面体系区段，每段输出单主角色主板，十字柱外侧翼缘板按 `CROSS_FLANGE_MAIN_PLATE` 进入主材。验证对象来自 Tekla 当前选择集重新导出，不复用旧 cache 作为最终证据。

## Fresh Tekla Export

```powershell
I:\xingcaisuanfa\TeklaSectionClassifier.Runner\bin\Debug\net48\TeklaSectionClassifier.Runner.exe --body-bracket-export --out I:\zijinhuatekla\cache\composite_current_selection_verify
```

结果：PASS。

关键输出：

- Runner 显示 `当前模式: 仅导出 Tekla 中已选中的构件`。
- 处理到当前关注构件 `T2-3GKZ-12`。
- 导出完成 `2` 根构件。
- Fresh cache：`I:\zijinhuatekla\cache\20260627_083740`。
- Bundle：`I:\zijinhuatekla\cache\20260627_083740\tekla-body-bracket-export.bundle.json`。

## Commands

```powershell
python -m unittest tests.test_composite_main_material_segments tests.test_pipeline_offline tests.test_reports_offline
python -m unittest tests.test_main_material_segments tests.test_box_main_material_segments tests.test_h_beam_part_sides
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260627_083740 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T2-3GKZ-12 --out outputs\current-selection-T2-3GKZ-12-composite-20260627-fix2
python -m unittest tests.test_composite_main_material_segments tests.test_reports_offline tests.test_pipeline_offline
```

## Results

- Focused composite/report/pipeline tests: PASS, `Ran 11 tests ... OK`；有既有 openpyxl `datetime.utcnow()` deprecation warning，不影响断言。
- Main-material regression tests: PASS, `Ran 25 tests ... OK`。
- Fresh current-selection CLI smoke: PASS，输出 composite JSON/CSV。
- Smoke output JSON：`outputs\current-selection-T2-3GKZ-12-composite-20260627-fix2\T2-3GKZ-12-composite-main-material-segments.json`。
- Smoke output CSV：`outputs\current-selection-T2-3GKZ-12-composite-20260627-fix2\T2-3GKZ-12-composite-main-material-segments.csv`。

## T2-3GKZ-12 Composite Result

`T2-3GKZ-12` fresh smoke 输出 6 个轴向区段，不是固定三段：

| segment | station range | segment type | main plate rows |
| --- | ---: | --- | ---: |
| S1 | 12.0-1423.75 | `CROSS_CORE_WITH_FLANGES` | 14 |
| S2 | 1423.75-4085.0 | `BOX_CLOSED_SECTION` | 12 |
| S3 | 4085.0-5669.8 | `CROSS_CORE_WITH_FLANGES` | 33 |
| S4 | 5669.8-6535.0 | `BOX_CLOSED_SECTION` | 13 |
| S5 | 6535.0-8420.0 | `CROSS_CORE_WITH_FLANGES` | 32 |
| S6 | 8420.0-8449.005 | `BOX_CLOSED_SECTION` | 5 |

Segment type counts：

- `CROSS_CORE_WITH_FLANGES=3`
- `BOX_CLOSED_SECTION=3`

Primary role counts：

- `CROSS_FLANGE_MAIN_PLATE=56`
- `BOX_MAIN_WALL_PLATE=30`
- `CROSS_CORE_MAIN_PLATE=23`

Representative `CROSS_FLANGE_MAIN_PLATE` positions include：`T2-3P-147`、`T2-3P-155`、`T2-3P-501`、`T2-3P-506`、`T2-3P-507`、`T2-3P-508`、`T2-3P-509`、`T2-3P-510`、`T2-3P-517`、`T2-3P-518`、`T2-3P-522`。

## Regression Notes

- 修复了一个真实烟测问题：`closedLoopCount > 0` 只能说明截面里存在闭合环，可能只是单块板自己的闭合矩形，不能直接等同于整体 BOX 闭合截面。组合截面分类器现在优先使用明确闭合箱体证据，例如 `innerLoopCount/topologyStatus=CLOSED_WITH_CAVITY` 或测试夹具中的 box regime 证据；否则先按活跃主板的 cross core、outer flange、box forming 投影证据判断。
- 修复了报告 CSV 可审计性：当某个 composite segment 存在但 `main_plates=[]` 时，CSV 仍输出一行 segment-level 记录，并分开输出 `segment_evidence_codes` 与 `plate_evidence_codes`。
- 本轮没有写死 `T2-3GKZ-12`、零件号或项目名；真实构件只作为 smoke/verification 样例。
## H/BH/GL Composite Adapter

2026-06-27 追加验证：H/BH/GL 主材分段结果已适配进入 composite 输出。当前不改变既有 H/GL 主材识别核心，而是在 offline pipeline 中把已计算的 `main_material_groups` 传给 composite classifier，输出统一的 `H_OR_BH_SECTION` segment 和 H/BH/GL 主角色。

新增/验证角色：

- `H_TOP_FLANGE_MAIN_PLATE`
- `H_WEB_MAIN_PLATE`
- `H_BOTTOM_FLANGE_MAIN_PLATE`
- `H_FLANGE_MAIN_PLATE`

验证命令：

```powershell
python -m unittest tests.test_pipeline_offline
python -m unittest tests.test_composite_main_material_segments tests.test_main_material_segments
python -m unittest tests.test_composite_main_material_segments tests.test_main_material_segments tests.test_box_main_material_segments tests.test_pipeline_offline tests.test_reports_offline tests.test_h_beam_part_sides
```

结果：PASS，最终相关回归 `Ran 37 tests ... OK`；有既有 openpyxl `datetime.utcnow()` deprecation warning，不影响断言。

