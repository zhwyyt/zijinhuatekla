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
## H/BH/GL Native Composite Station Frames

2026-06-29 追加迁移：H/BH/GL 不再只通过 `main_material_groups` adapter 进入 composite。`classify_composite_main_material_segments` 现在优先消费 `assembly.metadata.hBeamSectionEvidence.stationFrames[].partSlices`，按 station 覆盖、有效 `sectionLoops/segments`、`topFlangePartId/webPartId/bottomFlangePartId` 投票输出 `H_OR_BH_SECTION` composite segment。

保留兼容 fallback：当导出数据没有可用 H station frame/native slice 证据时，才继续把既有 `main_material_groups` 适配为 composite 输出。

新增/验证证据码：

- `H_GL_STATION_FRAME_NATIVE_COMPOSITE`
- `H_GL_STATION_SLICE_MAIN_PLATE`
- `hBeamSectionEvidence.stationFrames`

验证命令：

```powershell
python -m unittest tests.test_composite_main_material_segments.CompositeMainMaterialSegmentTests.test_prefers_native_h_station_frames_over_adapted_main_material_groups tests.test_composite_main_material_segments.CompositeMainMaterialSegmentTests.test_adapts_h_gl_main_material_groups_into_composite_roles
python -m unittest tests.test_composite_main_material_segments tests.test_main_material_segments tests.test_pipeline_offline
```

结果：PASS；第二组相关回归 `Ran 16 tests ... OK`。存在既有 openpyxl `datetime.utcnow()` deprecation warning，不影响断言。
## H/GL Regression Smoke After Native Migration

2026-06-29 追加复测：迁入 native composite station frame 后，重新验证之前 H/GL 数据。

命令：

```powershell
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260626_134928 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T2-3GL-55 --out outputs\h-gl-regression-T2-3GL-55-20260629
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260626_144742 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T2-3GL-62 --out outputs\h-gl-regression-T2-3GL-62-20260629
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_135923 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-6GL-110 --out outputs\h-gl-regression-T3-6GL-110-20260629-fix
python -m unittest tests.test_composite_main_material_segments tests.test_main_material_segments tests.test_box_main_material_segments tests.test_pipeline_offline tests.test_reports_offline tests.test_h_beam_part_sides
```

结果：PASS。

- `T2-3GL-55` native composite 输出 3 块强 station 覆盖种子主板：`T2-3B-526`、`T2-3B-508`、`T2-3B-797`；后续 2026-06-29 的“五块主板”扩展结论已在 2026-06-30 纠偏废弃。
- `T2-3GL-62` native composite 输出此前 station slice 验证的 5 块全长主板：`T2-3B-647`、`T2-3B-642`、`T2-3B-930`、`T2-3B-449`、`T2-3B-987`；局部附件未进入 composite 主板集合。
- `T3-6GL-110` 无 native hFrames 时走 adapter fallback，仍输出 `T3-P-4866` 上翼缘、`T3-P-4753` 腹板、`T3-P-4863/T3-P-5555/T3-P-4862` 下翼缘，composite 区段范围修正为 `-0.0-13114.9`。
- 相关回归 `Ran 39 tests ... OK`；存在既有 openpyxl `datetime.utcnow()` deprecation warning，不影响断言。

本次复测发现并修复一个 legacy adapter 解析问题：`station_ranges` 中的 `-0.0-1775.0` 不能用普通 `split("-", 1)` 解析，否则多段 H/GL 下翼缘会把 composite segment 起点误抬到 `1775.0`。已新增 `test_adapter_parses_negative_zero_station_ranges` 覆盖。
## H/GL Overall Report Visibility Fix

2026-06-29 追加修复：用户截图指出 `T2-3GL-62` 中箭头指向的 H 钢型材在整体识别报告中没有明显信息。复核导出数据确认该型材存在：`mainPartId=260925807`，对应 `T2-3B-642 / BEAM / PL10*200`。识别结果本身已在 composite CSV/JSON 中输出，但 Markdown 整体摘要只显示 `H_OR_BH_SECTION=1`，没有展开 H/GL 型材主体和主材明细。

修复：整体 Markdown 报告在组合截面主材分段后新增 `H/GL 型材主体与主材` 小节，显示主零件和 H/GL composite 主材行。

`T2-3GL-62` 最新 smoke：

- 主零件：`260925807 / T2-3B-642 / BEAM / PL10*200`
- `T2-3B-647`: `H_BOTTOM_FLANGE_MAIN_PLATE / BEAM / PL10*200`
- `T2-3B-642`: `H_FLANGE_MAIN_PLATE / BEAM / PL10*200`
- `T2-3B-930`: `H_TOP_FLANGE_MAIN_PLATE / PLATE / PL12`
- `T2-3B-449`: `H_WEB_MAIN_PLATE / PLATE / PL12.0`
- `T2-3B-987`: `H_WEB_MAIN_PLATE / PLATE / PL8`

验证命令：

```powershell
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260626_144742 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T2-3GL-62 --out outputs\h-gl-regression-T2-3GL-62-profile-summary-20260629
python -m unittest tests.test_composite_main_material_segments tests.test_main_material_segments tests.test_box_main_material_segments tests.test_pipeline_offline tests.test_reports_offline tests.test_h_beam_part_sides
```

结果：PASS；相关回归 `Ran 39 tests ... OK`。存在既有 openpyxl `datetime.utcnow()` deprecation warning，不影响断言。


## H/GL Native Main Plate Continuity Expansion

2026-06-29 追加修复：`T2-3GL-55` 暴露 native composite 只输出 3 块主板的问题。根因是 native H/GL station frame 迁入后只把 station 覆盖率足够高的零件作为强种子输出，没有继续按主板轴向连续性补齐同一条翼缘主板链；旧 H/GL 分段口径中的连续性组装能力没有完全迁入 native composite。

修复口径：

- 仍先用 `hBeamSectionEvidence.stationFrames[].partSlices`、有效 `sectionLoops/segments`、station 覆盖率筛出强种子主板。
- 对未达全长覆盖阈值但具备 station slice 证据的候选，只在同一 H 角色、profile 兼容、轴向区间贴近或重叠强种子时扩展进入同一主板链。
- 不使用 `PartRoles`、中文 `name` 或构件号/零件号硬编码；短局部件、不同 profile 的 tail web 片段不会因关系或长度被吸入。

新增证据码：

- `H_GL_AXIS_CONTINUITY_EXPANDED`

验证命令：

```powershell
python -m unittest tests.test_composite_main_material_segments.CompositeMainMaterialSegmentTests.test_native_h_station_frames_expand_main_plate_chain_by_axis_continuity
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260626_134928 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T2-3GL-55 --out outputs\h-gl-regression-T2-3GL-55-continuity-20260629
python -m unittest tests.test_composite_main_material_segments tests.test_main_material_segments tests.test_box_main_material_segments tests.test_pipeline_offline tests.test_reports_offline tests.test_h_beam_part_sides
```

结果：PASS；相关回归 `Ran 40 tests ... OK`，存在既有 openpyxl `datetime.utcnow()` deprecation warning，不影响断言。

已废弃结论：2026-06-29 曾误判 `T2-3GL-55` 应输出 5 块主板。以下条目保留为错误演进记录，不作为当前验收口径：

- `T2-3B-526`: `H_BOTTOM_FLANGE_MAIN_PLATE`，强 station 种子。
- `T2-3B-540`: `H_BOTTOM_FLANGE_MAIN_PLATE`，通过 `H_GL_AXIS_CONTINUITY_EXPANDED` 从 `T2-3B-526` 扩展。
- `T2-3B-508`: `H_TOP_FLANGE_MAIN_PLATE`，强 station 种子。
- `T2-3B-502`: `H_TOP_FLANGE_MAIN_PLATE`，通过 `H_GL_AXIS_CONTINUITY_EXPANDED` 从 `T2-3B-508` 扩展。
- `T2-3B-797`: `H_WEB_MAIN_PLATE`，强 station 种子。

输出文件：

- `outputs\h-gl-regression-T2-3GL-55-continuity-20260629\T2-3GL-55-composite-main-material-segments.json`
- `outputs\h-gl-regression-T2-3GL-55-continuity-20260629\T2-3GL-55-composite-main-material-segments.csv`
- `outputs\h-gl-regression-T2-3GL-55-continuity-20260629\T2-3GL-55-analysis.md`

## H/GL Native Continuity Closure and Variable Thickness

已废弃收敛记录：2026-06-29 在错误的 `T2-3GL-55` 五块主板假设上继续处理三个算法层遗漏。2026-06-30 后只保留其中“有链证据时允许变厚、多跳”的思想，具体主判据已改为三条件：

1. composite segment 的 `station_start/station_end` 不只看 station frame 强种子，也要包含扩展后主板实体的 `mainMaterialEvidence.axisStationStart/End`。
2. 主板连续性扩展改为闭包迭代：强种子进入 accepted 链后，候选可以贴任一已 accepted 主板继续扩展，支持多跳主板链。
3. profile 不再要求完全相同；同角色、同 station slice 证据、轴向连续时，允许 `PL厚度*宽度` 中厚度变化但宽度兼容的主板归入同一链。无法解析宽度的 profile 仍保持保守，不因同法向直接合并不同型材。

新增/补强测试：

- `test_native_h_continuity_updates_segment_range_for_expanded_plates`
- `test_native_h_continuity_expands_multiple_hops`
- `test_native_h_continuity_allows_thickness_change_in_same_plate_chain`

验证命令：

```powershell
python -m unittest tests.test_composite_main_material_segments.CompositeMainMaterialSegmentTests.test_native_h_continuity_updates_segment_range_for_expanded_plates tests.test_composite_main_material_segments.CompositeMainMaterialSegmentTests.test_native_h_continuity_expands_multiple_hops tests.test_composite_main_material_segments.CompositeMainMaterialSegmentTests.test_native_h_continuity_allows_thickness_change_in_same_plate_chain
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260626_134928 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T2-3GL-55 --out outputs\h-gl-regression-T2-3GL-55-continuity-v2-20260629
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_135923 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-6GL-110 --out outputs\h-gl-regression-T3-6GL-110-continuity-v2-20260629
python -m unittest tests.test_composite_main_material_segments tests.test_main_material_segments tests.test_box_main_material_segments tests.test_pipeline_offline tests.test_reports_offline tests.test_h_beam_part_sides
```

结果：PASS；完整相关回归 `Ran 43 tests ... OK`，存在既有 openpyxl `datetime.utcnow()` deprecation warning，不影响断言。

真实 smoke 结果：

- 已废弃：`T2-3GL-55` 输出 5 块主板的 smoke 结论错误；2026-06-30 strict chain 回归确认当前正确输出为 3 块 `T2-3B-526/T2-3B-508/T2-3B-797`。
- `T3-6GL-110` adapter fallback 仍输出 5 块主材，其中下翼缘变厚链保持 `T3-P-4863 / T3-P-5555 / T3-P-4862`，segment 范围 `-0.0-13114.9`。

输出文件：

- `outputs\h-gl-regression-T2-3GL-55-continuity-v2-20260629\T2-3GL-55-composite-main-material-segments.json`
- `outputs\h-gl-regression-T3-6GL-110-continuity-v2-20260629\T3-6GL-110-composite-main-material-segments.json`

## H/GL Strict Chain Correction

2026-06-30 追加纠偏：复核确认 2026-06-29 关于 `T2-3GL-55` 输出 5 块主板的结论是错误的。`T2-3B-540` 与 `T2-3B-502` 不能仅因 profile/位置相近或名称语义被吸入主板链；H/GL 原始扩展算法如果按 `name` 或 profile 兼容扩展，是错误主判据。

修正后的 H/GL 主板链规则：

- 必须收尾相连：候选板 station end/start 在容差内接续。
- 必须同截面侧：优先使用 `mainMaterialEvidence.bodyFaceId`；缺失时才用 `sectionProjectionEvidence.projectedCentroid/normalProjection` 辅助。
- 必须有直接 Weld/Contact 关系：只消费导出 `relationships[].edgeType in {Weld, Contact}`，不再按中文 `name` 判定主板链。
- 板厚可以变化：例如 `T3-6GL-110` 下翼缘 `PL14*200 -> PL22*200 -> PL14*200`，只要三条件成立仍属于同一主板链。
- `name` 只能作为显示/人工解释字段，不能作为识别逻辑输入。

实现要点：

- `box_main_material_segments.py` 的 H/GL fallback 改为枚举 web 候选，只有能闭合出两条翼缘主板链时才输出；否则宁可返回空，避免弱证据误判。
- `composite_main_material_segments.py` 的 native station frame 仍先取强 station 种子；连续性扩展改为从全 parts 池按三条件补齐端部主板，解决 fresh `T3-6GL-110` 中端部下翼缘未进入 station slice 的问题。
- 同侧证据以 `bodyFaceId` 优先，允许厚度变化造成的投影中心偏移；projection 只作 face 缺失时的辅助证据。

验证命令：

```powershell
I:\xingcaisuanfa\TeklaSectionClassifier.Runner\bin\Debug\net48\TeklaSectionClassifier.Runner.exe --body-bracket-export --out I:\zijinhuatekla\cache\20260629_t3_6gl_110_strict_chain
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260630_081919 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-6GL-110 --out outputs\h-gl-regression-T3-6GL-110-strict-chain-20260630-v3
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260626_134928 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T2-3GL-55 --out outputs\h-gl-regression-T2-3GL-55-strict-chain-20260630
python -m unittest tests.test_composite_main_material_segments tests.test_main_material_segments tests.test_box_main_material_segments tests.test_pipeline_offline tests.test_reports_offline tests.test_h_beam_part_sides
```

结果：PASS；相关回归 `Ran 44 tests ... OK`。存在既有 openpyxl `datetime.utcnow()` deprecation warning，不影响断言。

真实 smoke 结果：

- fresh Tekla 当前选择集导出成功，缓存目录：`I:\zijinhuatekla\cache\20260630_081919`，构件：`T3-6GL-110`。
- `T3-6GL-110` native composite 输出 5 块主材：`T3-P-4866` 上翼缘、`T3-P-4753` 腹板、`T3-P-4863/T3-P-5555/T3-P-4862` 下翼缘；两端 `T3-P-4863/T3-P-4862` 由 `H_GL_AXIS_CONTINUITY_EXPANDED` 从 `T3-P-5555` 按三条件补入。
- `T2-3GL-55` strict chain 回归输出 3 块主板：`T2-3B-526` 下翼缘、`T2-3B-508` 上翼缘、`T2-3B-797` 腹板；不再误吸 `T2-3B-540/T2-3B-502`。

输出文件：

- `outputs\h-gl-regression-T3-6GL-110-strict-chain-20260630-v3\T3-6GL-110-composite-main-material-segments.json`
- `outputs\h-gl-regression-T2-3GL-55-strict-chain-20260630\T2-3GL-55-composite-main-material-segments.json`
