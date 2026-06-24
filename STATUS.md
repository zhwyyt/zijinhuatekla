# STATUS

## 当前阶段

2026-06-17：已建立紫金花 Tekla 识别工程骨架，迁入 T3-5GKZ-10 已验证过的核心口径，并完成第一阶段算法抽取。

2026-06-17：已开始搭 Tekla AI Agent 正式架构骨架，新增 `architecture`、`quality`、`pipeline` 层级代码和对应测试。

2026-06-17：已完成第一轮 `adapters` 和 `reports` 边界迁移，CLI 当前只负责命令解析、调用分析和触发报告输出。

2026-06-17：已建立 `classifiers` 包门面，统一包住构件主材、零件角色和附属件簇分类入口；CLI 零件角色预测已改走门面。

2026-06-17：已建立 `run_offline_analysis` 离线流水线入口，CLI 收敛为参数解析和报告触发薄壳。

2026-06-17：已将 `spatial` 附属件簇分类接入 `run_offline_analysis`，报告新增空间关系诊断摘要。

2026-06-17：已将 Case Bank 升级为 JSON/CSV 可持久化，并新增 `cases\seed.json` 回归种子案例。

2026-06-17：已将空间分类明细输出为 CSV/JSON，并在报告中列出 Bracket 候选 `72805757:5`、`72805757:6` 及其证据码。

2026-06-17：已给空间分类明细补充 cluster 内部 Tekla part ids，可直接定位 Bracket 候选零件集合。

2026-06-17：已将 Data Quality Gate 问题明细输出为 CSV/JSON，缺失/冲突零件可进入后续复核工具。

2026-06-18：已新增质量复核任务队列，将 Data Quality Gate 问题转换为可人工处理的 `quality-review-tasks.json`。

2026-06-18：已新增质量复核任务 CSV 输出，方便用 Excel 人工筛查缺失/冲突复核队列。

2026-06-18：已新增质量复核摘要 JSON/CSV，将复核任务按问题类型和建议动作分组，为后续全模型搜索、几何候选复核、制造/建模口径映射提供入口。

2026-06-18：已新增缺失零件全模型候选搜索只读内核，可按规格、长度、板厚和宽度对 bundle 全部 assemblies 排序候选。

2026-06-18：已将缺失候选搜索接入离线报告，常规 analyze 输出会生成 `missing-candidates.json/csv`。

2026-06-18：已将同名冲突/几何候选复核接入离线报告，常规 analyze 输出会生成 `conflict-candidates.json/csv`。

2026-06-18：已固化编号硬约束：普通零件只允许精准 `partPosition` 匹配；几何相似不再自动命中，只输出复核候选；拆板派生保留为独立 `derivedFromProfilePart` 口径。

2026-06-18：已新增制造范围复核层，将箱型柱长主壁板“Excel 制造整板 vs Tekla 分段模型”从普通缺件/同名冲突中分流，报告输出 `manufacturing-scope-candidates.json/csv`。

2026-06-23：已将人工确认的 T3-5GKZ-10 柱主材分段集合写入 Case Bank；制造范围报告会携带 `confirmed_segment_positions` 和 `HUMAN_CONFIRMED_SEGMENT_GROUP` 证据。

2026-06-23：制造范围候选报告已新增 `station_ranges`、`continuity_gaps`、`continuity_level`；真实 T3 smoke 暴露候选段存在轴向重叠，当前标记为 `AXIS_OVERLAP_NEEDS_FACE_GROUPING`，下一步必须补壁板面/主材面归属。

2026-06-23：已在 `I:\xingcaisuanfa` 导出器补充主材分段工程证据字段：assembly 级 `memberAxisEvidence`，part 级 `mainMaterialEvidence.axisStationStart/End/bodyFaceId/segmentAdjacency`；厚度只作为辅助证据，不再作为主材分段集合强条件。

2026-06-23：已在 `I:\zijinhuatekla` 接入 BOX 主材分段集合算法和离线报告输出，并按用户反馈从粗 face bucket 分组改为“同 face 候选内主轴 station 邻接 + Weld/Contact 拓扑验证”；真实 T3 smoke 输出 201 个候选组，连续性分布 `GAPPED=14`、`NEAR_CONTINUOUS=12`、`INSUFFICIENT_EVIDENCE=175`，最大组 4 个零件，人工确认修正后的 13 个主材分段编号在新 cache 中 `13/13` 召回；`T3-P-4914` 已确认是误写成主材，不属于主材分段集合。

2026-06-23：已将主材分段算法上抽为统一入口 `classify_main_material_segment_groups`，先接 `H/GL/BEAM` 策略和 BOX fallback；新导出 `T3-6GL-110` 可识别 `TOP_FLANGE=T3-P-4866`、`WEB=T3-P-4753`、`BOTTOM_FLANGE=T3-P-4863;T3-P-5555;T3-P-4862`，BOX 回归 `T3-5GKZ-10` 仍保持修正后确认集合 `13/13` 召回。

2026-06-23：已补 Python 侧 BOX 截面证据层 `box_section.py`，基于 `bodyFaceId/bodyFaceOffset/station/Weld/Contact/name` 派生 `WALL_CORE`、`OUTER_ATTACHMENT`、`INNER_STIFFENER_OR_DIAPHRAGM`、`UNKNOWN`；主材分段报告新增 `evidence_summary.box_section_sides`。

2026-06-23：按用户反馈确认异形 BOX 不能依赖包围盒/径向分桶判断内外；已在 `I:\xingcaisuanfa` 导出器给 `mainMaterialEvidence` 补 `sectionProjectionEvidence`，导出构件主轴截面 U/V 坐标系、零件投影质心、投影轮廓、投影包络和板法向截面投影。该字段是下游闭环/内外判断证据，不作为 C# 侧硬判定结果。

2026-06-23：已升级 BOX 主材分段算法为“闭合截面外轮廓 trace 种子 -> 主轴 station 连续扩展 -> 截面复核”的多轮验证流程。最终报告输出单个 `BOX_MAIN_WALL_CONFIRMED_SET`，旧 `SECTION_FLANGE_CANDIDATE/SECTION_WEB_CANDIDATE/SECTION_UNSAMPLED_CANDIDATE` 只作为内部中间证据，不再作为最终主材集合行。真实 `20260623_144836` smoke 中 T3-5GKZ-10 去重后主材编号为 13 个，修正后确认集合 `13/13` 命中，missing/extra 为空；`T3-P-4916` 未进入主材集合，`T3-P-4918` 已进入主材集合。

2026-06-23：按用户要求暂不细分零件角色，先新增 BOX 内外关系层 `BOX_PART_SPATIAL_RELATION`。关系分为 `MAIN_WALL/INSIDE_BODY/OUTSIDE_ATTACHMENT/BOUNDARY_OR_THROUGH/INSUFFICIENT_EVIDENCE`；已升级为用 `MAIN_WALL` 的 `sectionProjectionEvidence.projectedContour/projectedBounds` 反推真实截面围合区域，并用每个零件 `projectedCentroid` 判内外，不使用构件包围盒。真实 `20260623_144836` smoke 输出 `INSIDE_BODY=228`、`MAIN_WALL=16` Tekla 实体、`OUTSIDE_ATTACHMENT=15`、`INSUFFICIENT_EVIDENCE=0`；`T3-P-4916` 判为 `INSIDE_BODY`。

2026-06-24：已将 BOX 内外关系证据升级为 Tekla solid 原生截面 station loop：导出器输出 `metadata.boxSectionEvidence.stationLoops[].partLoops[]`，station 采样为默认三刀 + 每个零件 `start/mid/end` 三点，并修正采样上限为所有零件最大 station。Python 侧按已确认主壁板 partLoops 重建各 station 主壁板轮廓，并对零件三点 station 做一致性判定；真实 `I:\zijinhuatekla\cache\20260624_092738` smoke 中主板仍保持 13 个确认编号，`T3-GG-2` 8 个实体全部由旧 `INSIDE_BODY` 修正为 `OUTSIDE_ATTACHMENT`，关系分布 `MAIN_WALL=16`、`INSIDE_BODY=185`、`OUTSIDE_ATTACHMENT=57`、`BOUNDARY_OR_THROUGH=1`。验证记录：`docs/verification/2026-06-24-box-solid-station-loop-relations.md`。

## 已确认业务口径

- `T3-H-558s/x/f` 这类 Excel 加工板可以来自 `BH400*200*7*10` 型钢拆板；它们不是 Tekla 独立零件缺失。
- `s/x` 对应 BH 翼缘板加工口径，示例 `PL10*200`。
- `f` 对应 BH 腹板加工口径，示例 `PL7*380`。
- 斜放或异形 `ContourPlate` 不能只用 OBB 外包盒尺寸判断加工规格，应优先用轮廓边长匹配 Excel 的 `PL厚*宽 + 长度`。
- 同名 `partPosition` 只能作为候选，规格/长度明显冲突时必须标为冲突，不可算自动命中。
- 普通零件编号必须精准一致；几何相似候选只能作为复核证据，不得自动改号或自动匹配。
- 拆板/派生加工件不是编号漂移，必须由母件名、母件 profile、后缀语义和尺寸证据共同证明。
- 箱型柱长主壁板可能存在制造整板与 Tekla 分段建模口径差异；当前只能标记为 `MANUFACTURING_MODEL_SCOPE_MISMATCH` 复核候选，不代表自动改号。`T3-5GKZ-10` 已人工确认一组柱主材分段集合，作为 Case Bank 回归样例。

## 当前输入样例

- Tekla cache：`I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1`
- 真实 Excel：`I:\xingcaisuanfa\cache\20260615_161938\T3楼五节柱零构件清单(1).xls`
- 目标构件：`T3-5GKZ-10`

## 风险

- Excel 清单存在制造口径和 Tekla 分段口径差异，尤其箱型柱超长主壁板。
- 制造范围候选旧 cache 只有 Python 推导 station/连续性证据；新导出器已补 `memberAxisEvidence/mainMaterialEvidence` 字段，但需要重新导出 T3 cache 后才能在 Python 侧消费并验证。
- 部分 `partPosition` 在全模型中存在同名冲突或制造/建模口径差异，需要冲突状态保留证据。
- 后续接入 Tekla MCP 或插件直连时，数据入口可替换，但规则层不应重写。
- 参考算法都还会随案例修正，必须通过特征契约、评分策略和 Case Bank 进化，禁止维护成零散规则堆砌。
- `MemberBodyClassifier` 当前已接已有分类和 profile-family 证据，完整截面 trace/闭环拓扑还需要导出器补字段后继续接入。
- `BracketClassifier` 当前已接牛腿核心 evidence code，完整附属件簇、RootZone、Overhang 自动计算还需要空间关系字段。
- 当前 bundle/member 已有 `boundingBox`、`centroid`、`relationships`、`AxisSegments`、`PartRoles`，已可在 Python 侧先推导第一轮空间特征，不必马上改 C# 导出器。

## 下一步

1. 人工复核 T3 空间诊断中 2 个 Bracket 候选：`72805757:5` 包含 part `71163864`；`72805757:6` 包含 parts `71170394;71170452;71170471;71460728;71460737;71460746;71460755;71460764`。确认后写入 Case Bank 回归样例。
2. 对 `T3-P-3449`、`T3-P-4910` 补查是否为选中构件缺实体、制造口径差异或导出范围问题；不得用几何相似件自动改号。
3. 基于统一主材分段入口继续补策略：H/GL 减少对 name 的依赖、BOX 在导出器补原生 `boxSectionEvidence`、T 型/十字/圆管新增策略，并将报告文件名从 box-main-material 迁移为通用 main-material。
4. 未实现项：构件装配顺序、焊接顺序、配送顺序、图纸自动标注的数据契约、流水线和报告。

## 最新验证

- 验证记录：`docs/verification/2026-06-17-t3-recognition-core.md`
- 算法抽取验证：`docs/verification/2026-06-17-algorithm-extraction-core.md`
- 空间特征适配验证：`docs/verification/2026-06-17-spatial-feature-adapter.md`
- 架构骨架设计：`docs/design/2026-06-17-agent-architecture-skeleton.md`
- adapter 层验证：`docs/verification/2026-06-17-adapter-layer.md`
- reports 层验证：`docs/verification/2026-06-17-reports-layer.md`
- classifiers 门面验证：`docs/verification/2026-06-17-classifiers-facade.md`
- offline pipeline 验证：`docs/verification/2026-06-17-offline-pipeline.md`
- spatial pipeline 验证：`docs/verification/2026-06-17-spatial-pipeline.md`
- Case Bank 持久化验证：`docs/verification/2026-06-17-casebank-persistence.md`
- 空间候选明细验证：`docs/verification/2026-06-17-spatial-candidate-report.md`
- 空间候选定位验证：`docs/verification/2026-06-17-spatial-candidate-partids.md`
- Data Quality Gate 明细验证：`docs/verification/2026-06-17-quality-issues-report.md`
- 质量复核任务验证：`docs/verification/2026-06-18-quality-review-tasks.md`
- 质量复核 CSV 验证：`docs/verification/2026-06-18-quality-review-tasks-csv.md`
- 质量复核摘要验证：`docs/verification/2026-06-18-quality-review-summary.md`
- 缺失候选搜索验证：`docs/verification/2026-06-18-missing-candidate-search.md`
- 缺失候选报告验证：`docs/verification/2026-06-18-missing-candidates-report.md`
- 冲突候选报告验证：`docs/verification/2026-06-18-conflict-candidates-report.md`
- 制造范围候选报告验证：`docs/verification/2026-06-18-manufacturing-scope-report.md`
- 人工确认主材分段验证：`docs/verification/2026-06-23-confirmed-main-material-segments.md`
- station 连续性证据验证：`docs/verification/2026-06-23-station-continuity-evidence.md`
- 主材分段导出字段契约：`docs/design/2026-06-23-main-material-segment-export-contract.md`
- BOX 主材分段集合验证：`docs/verification/2026-06-23-box-main-material-segment-groups.md`
- 统一主材分段入口验证：`docs/verification/2026-06-23-unified-main-material-segments.md`
- BOX 截面内外证据验证：`docs/verification/2026-06-23-box-section-evidence.md`
- BOX 截面投影导出字段验证：`docs/verification/2026-06-23-section-projection-exporter.md`
- BOX 截面采样主材算法升级验证：`docs/verification/2026-06-23-section-sample-main-material-upgrade.md`
- BOX 外轮廓 trace 验证：docs/verification/2026-06-23-box-wall-trace.md`r
- BOX 主壁板确认集合验证：docs/verification/2026-06-23-box-main-wall-confirmed-set.md`r
- BOX 内外关系层验证：`docs/verification/2026-06-23-box-part-spatial-relations.md`
- Case Bank 种子案例：`cases\seed.json`
- 输出：`outputs\T3-5GKZ-10-analysis.md`
- 算法抽取 smoke 输出：`outputs\algorithm-extraction-smoke-20260617\T3-5GKZ-10-analysis.md`
- 当前严格编号结果：62 行中 `MATCH=35`、`MATCH_CONFLICT=4`、`DATA_MISSING=23`；其中拆板派生 `derivedFromProfilePart=3`。
- 算法抽取治理规则：`docs/design/2026-06-17-algorithm-extraction-governance.md`
- 单元测试：`python -m unittest discover -s tests`，16 tests OK。
- 空间适配后单元测试：`python -m unittest discover -s tests`，20 tests OK。
- 架构骨架后单元测试：`python -m unittest discover -s tests`，23 tests OK。
- adapter 迁移后单元测试：`python -m unittest discover -s tests`，26 tests OK。
- reports 迁移后单元测试：`python -m unittest discover -s tests`，27 tests OK。
- reports 迁移后 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\reports-smoke-20260617`，输出 62 行，`MATCH=55`、`MATCH_CONFLICT=4`、`DATA_MISSING=3`。
- classifiers 门面后单元测试：`python -m unittest discover -s tests`，29 tests OK。
- classifiers 门面后 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\classifiers-smoke-20260617`，输出 62 行，`MATCH=55`、`MATCH_CONFLICT=4`、`DATA_MISSING=3`。
- offline pipeline 后单元测试：`python -m unittest discover -s tests`，30 tests OK。
- offline pipeline 后 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\pipeline-smoke-20260617`，输出 62 行，`MATCH=55`、`MATCH_CONFLICT=4`、`DATA_MISSING=3`。
- spatial pipeline 后单元测试：`python -m unittest discover -s tests`，30 tests OK。
- spatial pipeline 后 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\spatial-pipeline-smoke-20260617`，输出 62 行，`MATCH=55`、`MATCH_CONFLICT=4`、`DATA_MISSING=3`；空间簇 `15`，`Bracket=2`、`Unknown=13`。
- Case Bank 持久化后单元测试：`python -m unittest discover -s tests`，34 tests OK。
- 空间候选明细后单元测试：`python -m unittest discover -s tests`，34 tests OK。
- 空间候选明细后 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\spatial-detail-cli-smoke-20260617`，输出 alignment CSV/JSON、spatial CSV/JSON、Markdown 五份文件；Bracket 候选为 `72805757:5`、`72805757:6`。
- 空间候选定位后单元测试：`python -m unittest discover -s tests`，34 tests OK。
- 空间候选定位后 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\spatial-partids-smoke-20260617`；`72805757:5` 包含 part `71163864`，`72805757:6` 包含 parts `71170394;71170452;71170471;71460728;71460737;71460746;71460755;71460764`。
- Data Quality Gate 明细后单元测试：`python -m unittest discover -s tests`，34 tests OK。
- Data Quality Gate 明细后 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\quality-issues-smoke-20260617`；质量问题 `7` 条，`DATA_MISSING=3`、`MATCH_CONFLICT=4`。
- 质量复核任务后单元测试：`python -m unittest discover -s tests`，36 tests OK。
- 质量复核任务后 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\quality-review-smoke-20260618`；历史旧口径复核任务 `7` 条，`DATA_MISSING=3`，`MATCH_CONFLICT=4`；当前严格编号口径以后续 strict smoke 为准。
- 质量复核 CSV 后单元测试：`python -m unittest discover -s tests`，37 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。
- 质量复核 CSV 后 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\quality-review-csv-smoke-20260618`；新增 `T3-5GKZ-10-quality-review-tasks.csv`，复核任务 `7` 条，`DATA_MISSING=3`、`MATCH_CONFLICT=4`。
- 质量复核摘要后单元测试：`python -m unittest discover -s tests`，38 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。
- 质量复核摘要后 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\quality-review-summary-smoke-20260618`；新增 `T3-5GKZ-10-quality-review-summary.json/csv`，分组为 `DATA_MISSING=3`、`MATCH_CONFLICT=4`。
- 缺失候选搜索后单元测试：`python -m unittest discover -s tests`，39 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。
- 缺失候选搜索 T3 smoke：`outputs\candidate-search-smoke-20260618\T3-5GKZ-10-missing-candidates.json`；`T3-P-4910` 找到近似候选 `T3-P-4894`，`T3-P-3449` 和 `T3-P-4914` 暂无候选。
- 缺失候选报告后单元测试：`python -m unittest discover -s tests`，40 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。
- 缺失候选报告 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\missing-candidates-report-smoke-20260618`；输出 `T3-5GKZ-10-missing-candidates.json/csv`，`T3-P-4910` 找到近似候选 `T3-P-4894/72805808`。
- 冲突候选报告后单元测试：`python -m unittest discover -s tests`，41 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。
- 冲突候选报告 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\conflict-candidates-report-smoke-20260618`；输出 `T3-5GKZ-10-conflict-candidates.json/csv`，`T3-P-4916/4917/4919/6243` 保留同名冲突实体，`T3-P-6243` 找到 5 个几何近似复核候选。
- 严格编号规则后单元测试：`python -m unittest discover -s tests`，42 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。
- 严格编号规则后 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\strict-numbering-smoke-20260618`；普通零件不再用几何相似自动命中，`MATCH=35`、`MATCH_CONFLICT=4`、`DATA_MISSING=23`，拆板派生保留 `derivedFromProfilePart=3`。
- 制造范围报告后单元测试：`python -m unittest discover -s tests`，45 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。
- 制造范围报告后 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\manufacturing-scope-smoke-20260618`；严格编号状态仍为 `MATCH=35`、`MATCH_CONFLICT=4`、`DATA_MISSING=23`，质量归因分流为 `DATA_MISSING=22`、`MANUFACTURING_MODEL_SCOPE_MISMATCH=4`、`MATCH_CONFLICT=1`。
- 制造范围候选：`T3-P-4916/4917/4919` 输出到 `T3-5GKZ-10-manufacturing-scope-candidates.json/csv`；`T3-H-558s/x/f` 仍保持 `derivedFromProfilePart`。
- 人工确认主材分段后单元测试：`python -m unittest discover -s tests`，48 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。
- station 连续性证据后单元测试：`python -m unittest discover -s tests`，50 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。
- 人工确认主材分段后 T3 smoke：`outputs\confirmed-segments-smoke-20260623`；制造范围报告候选带 `confirmation_level=HUMAN_CONFIRMED_SEGMENT_GROUP`，`confirmed_segment_positions` 包含修正后的 13 个柱主材分段编号。
- station 连续性证据 T3 smoke：`outputs\station-continuity-smoke-20260623`；4 个制造范围候选均输出 station 证据，且因轴向重叠标记为 `AXIS_OVERLAP_NEEDS_FACE_GROUPING`。
- xingcaisuanfa 导出器字段验证：`dotnet build I:\xingcaisuanfa\TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj`，build succeeded，0 errors，4 nullable warnings。
- BOX 截面证据后单元测试：`python -m unittest discover -s tests`，64 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。
- BOX 主材分段集合 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_103323 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\box-main-material-segments-smoke-20260623`；候选组 201 个，`GAPPED=14`、`NEAR_CONTINUOUS=12`、`INSUFFICIENT_EVIDENCE=175`，最大组 4 个零件，修正后的人工确认集合 `13/13` 召回。
- GL 主材分段集合 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_135923 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-6GL-110 --out outputs\main-material-gl-smoke-20260623`；识别 `TOP_FLANGE=T3-P-4866`、`WEB=T3-P-4753`、`BOTTOM_FLANGE=T3-P-4863;T3-P-5555;T3-P-4862`，均为 `CONTINUOUS`。
- BOX 主壁板最终确认集合后单元测试：`python -m unittest discover -s tests`，67 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。
- BOX 主壁板最终确认集合 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_144836 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\box-main-wall-confirmed-smoke-20260623`；输出 1 个 `BOX_MAIN_WALL_CONFIRMED_SET`，去重后 13 个主材编号，修正后确认集合 `13/13` 命中，`T3-P-4916` 排除，`T3-P-4918` 纳入。
- BOX 内外关系层后单元测试：`python -m unittest discover -s tests`，70 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。
- BOX 内外关系层 T3 smoke：`python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_144836 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\box-part-spatial-relations-smoke-20260623-v3`；新增 `box-part-spatial-relations.json/csv`，分布 `INSIDE_BODY=228`、`MAIN_WALL=16`、`OUTSIDE_ATTACHMENT=15`、`INSUFFICIENT_EVIDENCE=0`。
- T3 空间诊断：附属件簇 `15`，`Bracket=2`，`Unknown=13`。















