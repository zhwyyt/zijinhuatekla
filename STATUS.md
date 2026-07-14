## Handoff - 2026-07-13 零件图 CAD 原生尺寸样式

工作目录：`I:\tmp\zijinhuatekla-part-drawing-engine`，分支 `codex/offline-part-drawing-engine`。

已按根目录 `零件标注.dwg` 固化 `partCadDimensionStyle.v1`：DXF 输出可编辑原生 `DIMENSION`，线性尺寸采用 45 度斜杠，半径/直径采用实心箭头；PDF 从同一 `PlacedDimension` 和样式 DTO 渲染。径向引线改为特征局部放置，标题区加入统一障碍边界，尺寸显示按样板整数精度输出但保留精确测量值。

最新验证：focused `24 tests OK`，完整回归 `174 tests OK`；真实 `T3-PX-317` smoke 为 `REVIEW_REQUIRED=1 / REJECTED=0`，DXF 原生尺寸 `13`、style `PART-CAD-V1`、`dimlfac=2.0`、audit `0 errors/0 fixes`；PDF A3 预览人工检查无跨图引线或标题区穿越。证据见 `docs/verification/2026-07-13-part-drawing-cad-dimension-style.md`。

剩余边界：7 个孔定位尺寸因左/下标注带容量与标题区保护未放置，均保留在 `LAYOUT_OVERFLOW` evidence；应后续设计孔组/共同基准尺寸链，不得放宽碰撞边界硬塞。AutoCAD 2025 Core Console 打开审计脚本因本机语言提示超时，本轮未取得 CAD 控制台正式 audit 结论。

## Handoff - 2026-07-13 平板零件离线出图引擎

工作目录：`I:\tmp\zijinhuatekla-part-drawing-engine`，分支 `codex/offline-part-drawing-engine`。

当前阶段：已完成 `partDrawingSnapshot.v1` 离线消费端和可人工复核的平板零件 DXF/PDF/drawing JSON 出图闭环。实现包括几何归一化、制造指纹质量门、加工特征、尺寸意图、布局、共享文档、双 renderer 和 `draw-parts` 批处理 CLI。

最新验证：零件图 focused `33 tests OK`；完整回归 `165 tests OK`；fixture CLI smoke `OK=1 / REVIEW_REQUIRED=0 / REJECTED=0`；DXF audit `0 errors/0 fixes`；PDF 单页 A3 横向。证据见 `docs/verification/2026-07-13-offline-part-drawing-engine.md`。

当前边界：尚未实现 Tekla 导出器的 `partDrawingSnapshot.v1` 生产端，也没有真实模型 smoke；当前 `OK` 只表示自动出图完整，不代表生产放行。

下一步：单独设计并实现 Tekla 快照生产端，选择真实平板件做首轮模型到 DXF/PDF 人工复核。禁止用几何相似替代 `partPosition`，禁止围绕零件号补特例。

## Handoff - 2026-06-26 H钢位置关系阶段收敛

当前仓库：`I:\zijinhuatekla`，分支 `main`，已推送到 `origin/main`。

最新提交：`55e7fc3 Add H beam side and station slice classifiers`。

已完成并已推送：

- 新增 H 钢四侧位置关系分类器：`src/zijinhua_tekla/classifiers/h_beam_part_sides.py`。
- 新增 H/GL station slice 主板识别：`src/zijinhua_tekla/classifiers/box_main_material_segments.py`。
- 新增回归测试：`tests/test_h_beam_part_sides.py`、`tests/test_main_material_segments.py`。
- 新增 H 钢、H/GL、direct H profile frame 相关验证记录。
- 最新验证：`python -m unittest tests.test_h_beam_part_sides tests.test_main_material_segments tests.test_box_main_material_segments tests.test_pipeline_offline tests.test_reports_offline`，结果 `Ran 28 tests ... OK`；存在既有 openpyxl deprecation warning，不影响断言。

本次不处理 `I:\xingcaisuanfa` 现场；导出器 direct H profile frame 已在该仓库当前分支另行提交并 push。

当前 `I:\zijinhuatekla` 剩余未提交现场：主要是 2026-06-24 BOX station topology / BOX 内外关系 / offline report pipeline 相关改动，尚未收敛提交。包括：

- 修改：`docs/design/2026-06-23-main-material-segment-export-contract.md`、`pyproject.toml`、`src/zijinhua_tekla/classifiers/box_part_spatial_relations.py`、`src/zijinhua_tekla/cli.py`、`src/zijinhua_tekla/pipeline/offline.py`、`src/zijinhua_tekla/quality/manufacturing_scope.py`、`src/zijinhua_tekla/reports/offline.py`、`src/zijinhua_tekla/spatial_features.py`、多组 BOX/report/pipeline 测试。
- 未跟踪：`src/zijinhua_tekla/classifiers/box_station_topology_diagnostics.py`、`tests/test_box_station_topology_diagnostics.py`、多份 2026-06-24 BOX 验证记录、`docs/project-overview.md`、`聊天记录.md`。

下一步建议：先不要继续加新规则；优先将剩余 BOX/report pipeline 现场按主题拆成 2-3 个小提交，逐个验证后再 push。不要使用 `git reset --hard` 或 `git checkout --` 清理现场，除非用户明确指定要丢弃哪些文件。
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


2026-06-24：已将 BOX 内外关系层从 station 主壁板凸包升级为 Shapely 多 loop 拓扑，显式构建 outer_loop/inner_loops/cavity_geometries，新增凹形外轮廓和 inner/cavity loop 回归测试。真实 I:\zijinhuatekla\cache\20260624_092738 smoke 中主板仍保持 13 个确认编号，T3-GG-2 8 个实体仍为 OUTSIDE_ATTACHMENT；多 loop 证据下分布为 OUTSIDE_ATTACHMENT=115、INSIDE_BODY=87、MAIN_WALL=16、BOUNDARY_OR_THROUGH=41。该口径比旧凸包更严格，仍需下一步补 station 闭合失败原因和导出器显式 outer/inner 边证据。验证记录：docs/verification/2026-06-24-box-multiloop-topology.md。


2026-06-24：针对 T3-P-6203 误入 BOUNDARY_OR_THROUGH 的问题，已停止判定层修补，改为新增 BOX station topology 诊断报告 box-station-topology-diagnostics.json/csv。真实 T3 smoke 显示 152 个 station 中 CLOSED_WITH_CAVITY=33、STATION_TOPOLOGY_NOT_CLOSED=85、CLOSED_WITHOUT_CAVITY=34；86 个 station 存在退化/invalid 主壁板 loop，115 个 station 的主壁板 union 为多组件。根因定位到导出器当前 partLoops 实际是 solid face intersection point set，不是真正闭合截面 loop，后续必须整体修复导出器为 section segments/section loops 拓扑。验证记录：docs/verification/2026-06-24-box-station-topology-export-diagnostics.md。


2026-06-24：已整体修复 Tekla 导出器 BOX station topology 契约：`boxSectionEvidence` 从旧 point-set 升级为 `teklaSolidFaceSectionSegments.v2`，新增 station/part 级 `sectionSegments/sectionLoops/closedLoopCount/openChainCount/diagnostics`；Python 侧优先消费 exporter `sectionLoops`，再用 `segments` polygonize，最后兼容旧 `points`。新导出 `I:\zijinhuatekla\cache\20260624_144128` smoke 中 T3-5GKZ-10 拓扑由旧 `CLOSED_WITH_CAVITY=33 / STATION_TOPOLOGY_NOT_CLOSED=85` 改善为 `CLOSED_WITH_CAVITY=101 / STATION_TOPOLOGY_NOT_CLOSED=4`；`T3-P-6203` 4 个实体全部为 `INSIDE_BODY`，`T3-GG-2` 8 个实体全部为 `OUTSIDE_ATTACHMENT`，主壁板确认集合仍保持 13 个去重编号。验证记录：`docs/verification/2026-06-24-box-section-segment-topology-exporter-v2.md`。


2026-06-24：继续追查 section segment v2 后剩余 4 个不闭合 station，确认根因不是退化 loop，也不是导出器未闭合，而是所有零件 start/mid/end 采样带入了端部/附件触发 station。`T3-P-4919` 仍是确认主壁板；四个 station 位于该实体导出 solid 覆盖尾端 `axisStationEnd=10452.706` 之后，只有 `T3-P-4918 + 两个 T3-P-4917` 主壁板参与；同 station 的 `T3-P-4889/PL16` 虽有大面积 loop，但 `normalProjectionMagnitude=0.168825`，属于端部/过渡板证据，不应硬塞主壁板集合，也不代表 `T3-P-4919` 主板身份变化。诊断层已新增 `station_scope`，将 4 个 station 标为 `END_TRANSITION_NOT_BODY_CORE`；最新 smoke 分布为 `CLOSED_WITH_CAVITY=101`、`CLOSED_WITHOUT_CAVITY=47`、`END_TRANSITION_NOT_BODY_CORE=4`，核心 BODY station 不再有 topology failure。


2026-06-24：针对新选中构件 `T3-5GKZ-2` 主壁板只识别 4 个 seed 的回归，已定位为 BOX 主壁板 axis 扩展准入仍只接受旧 `wall_candidate/COLUMN` 口径，导致新导出器中的 `flange_candidate/web_candidate + isBodyWallPlateCandidate=true` 后续主板被挡在 station 连续判断之前。已修正为先要求 `isBodyWallPlateCandidate=true`，再接受 `wall_candidate/flange_candidate/web_candidate` 角色；不写死零件号。新 smoke 输出 16 个主壁板实体，包含用户指出的 `T3-P-4895/T3-P-4897/T3-P-4899/T3-P-4907`，并继续扩到中段/上段主板；T3-5GKZ-10 回归仍为 13 个唯一确认主板编号。验证记录：`docs/verification/2026-06-24-box-main-wall-axis-expansion-regression.md`。

2026-06-24：按用户要求基于新导出做全项目链路核对，发现并补齐两个遗漏：CLI 未打印 `box-part-spatial-relations` 与 `box-station-topology-diagnostics` 报告路径；reports/pipeline 测试未锁定 station topology 输出与 result 传播。已补 CLI、`tests/test_reports_offline.py`、`tests/test_pipeline_offline.py`，并将 `metadata.boxSectionEvidence.source=teklaSolidFaceSectionSegments.v2`、station/part `sectionLoops/sectionSegments/segments` 写入导出契约。真实 `T3-5GKZ-2` 与 `T3-5GKZ-10` smoke 均输出完整 23 个报告文件；全量单测 78 tests OK。验证记录：`docs/verification/2026-06-24-new-export-contract-project-audit.md`。

2026-06-24：按用户澄清完成新导出契约全项目迁移审计，不再只核对 BOX 主板。已修复三类旧契约依赖：BOX 主壁板 seed 现在优先消费 `metadata.boxSectionEvidence.stationLoops[].partLoops[].sectionLoops/segments`，旧 `member.Samples/SectionParts` 仅作 fallback；拓扑 seed 增加长轴向壁板候选与 `normalProjectionMagnitude` 过滤，避免短端部/附件 loop 被误吸进主材集合；附属件簇主体边界由 offline pipeline 传入已确认主壁板 ids，旧 `Classification.PartRoles/mainPartId` 仅作 fallback。回归 smoke：T3-5GKZ-2 主壁板 16 个实体/13 个唯一编号，保留 `T3-P-4897/T3-P-4895/T3-P-4907/T3-P-4899`；T3-5GKZ-10 主壁板 16 个实体/13 个唯一编号，missing/extra 为空，`T3-P-4918` 纳入、`T3-P-4916` 排除。验证记录：`docs/verification/2026-06-24-new-export-contract-project-audit.md`。
2026-06-24：按用户截图复核修正 BOX 内外关系纯几何判定：`T3-5GKZ-8` 中 16 个原 `BOUNDARY_OR_THROUGH` 实体实际位于主壁板内腔。根因是 start/mid/end 采样时选到只有局部单片壁板的 station topology，并把局部 `CLOSED_WITHOUT_CAVITY` 当成完整 BOX 截面判外侧。已改为存在完整 cavity station 参照时，跳过面积小于完整闭合截面 75% 的局部不完整 station，只用几何拓扑判断内腔/外侧，不依赖编号、名称或业务标签。新 smoke 中 T3-5GKZ-8 分布 `INSIDE_BODY=165`、`OUTSIDE_ATTACHMENT=58`、`MAIN_WALL=16`、`BOUNDARY_OR_THROUGH=0`；16 个目标实体全部为 `INSIDE_BODY`。T3-5GKZ-10 回归仍保留 `BOUNDARY_OR_THROUGH=2`。验证记录：`docs/verification/2026-06-24-box-internal-cavity-geometry-fix.md`。

2026-06-26：针对当前选择集 `T2-3GKZ-12` 暴露的复杂构件口径，已确认其不应只按单一 BOX 主材集合表达；下部是十字柱并带外侧翼缘板，上部是 BOX，外侧翼缘板在下部稳定十字柱区段中属于主板/主材。已新增组合截面主材设计：沿构件主轴自动切 N 个截面体系区段，每段只给每块板一个主角色，另一体系关系进入辅助解释；设计见 `docs/design/2026-06-26-composite-main-material-segments.md`。

2026-06-27：组合截面主材识别已完成 fresh Tekla 当前选择集验证；新导出 `I:\zijinhuatekla\cache\20260627_083740` 中 `T2-3GKZ-12` 切为 6 个轴向区段，输出 `CROSS_FLANGE_MAIN_PLATE=56`、`BOX_MAIN_WALL_PLATE=30`、`CROSS_CORE_MAIN_PLATE=23`；验证记录见 `docs/verification/2026-06-27-composite-main-material-segments.md`。

2026-06-29：H/BH/GL 主材分段已从 adapter 过渡为 composite native station frame 优先口径；`classify_composite_main_material_segments` 先消费 `metadata.hBeamSectionEvidence.stationFrames[].partSlices`，输出 `H_OR_BH_SECTION` 以及 `H_TOP_FLANGE_MAIN_PLATE/H_WEB_MAIN_PLATE/H_BOTTOM_FLANGE_MAIN_PLATE/H_FLANGE_MAIN_PLATE`，只有缺少 native frame 证据时才回退复用既有 `main_material_groups`。

2026-06-29：H/GL native composite 已迁入 station frame 主路径，但随后复核确认原先按 profile/name-like 连续扩展会误吸局部/端部板，`T2-3GL-55` 不能输出 5 块主板；正确口径必须改为收尾相连 + 同截面侧 + Weld/Contact 关系三条件，中文 `name` 仅可显示解释，不可作为识别判据。验证记录见 `docs/verification/2026-06-27-composite-main-material-segments.md`。

2026-06-30：H/GL 主板链算法已按三条件收敛：收尾相连、同截面侧、直接 Weld/Contact。native station frame 先取强种子，再从全 parts 池按三条件补齐未被切片命中的端部主板；同 `bodyFaceId` 优先作为同侧证据，允许板厚变化导致的投影中心偏移，但不允许仅按 name/profile 扩展。fresh Tekla 当前选择集重新导出 `I:\zijinhuatekla\cache\20260630_081919`，`T3-6GL-110` 输出 `T3-P-4866` 上翼缘、`T3-P-4753` 腹板、`T3-P-4863/T3-P-5555/T3-P-4862` 下翼缘；`T2-3GL-55` 回归输出 3 块主板 `T2-3B-526/T2-3B-508/T2-3B-797`，不再误吸 `T2-3B-540/T2-3B-502`。

2026-07-06：已确认 BOX 柱子渐进式构件图方向：步骤粒度按“能表达尺寸和位置关系的信息组/阶段”，不按每个小零件单独分页；第一阶段输出离线步骤计划，Tekla 2017 Drawing API 优先做出图 POC，CAD/DXF 作为兜底。设计见 `docs/design/2026-07-06-box-column-progressive-drawing-steps.md`。

2026-07-06：BOX 柱子渐进式构件图第一版已落地。离线 pipeline/report 输出 `box-assembly-drawing-steps.json/csv/md/dxf`；当前 Tekla 选中构件 `T3-3GZ-6` 生成 29 步（基准主板、侧壁、7 个内部组、盖板、19 个外部簇），DXF 预览见 `outputs/box-progressive-drawing-selected-20260706/T3-3GZ-6-box-assembly-drawing-steps.dxf`。Tekla 2017 POC 已定位并修复外部 API 连接前置条件 `SESSIONNAME=Console`，并验证 `DrawingCreator + ch_column.xdproc` 可生成构件图；自动打开生成图纸并套用隐藏/标注仍待下一步突破。验证记录：`docs/verification/2026-07-06-box-column-progressive-drawing-steps.md`。

2026-07-06：按参考 `4.西岑文化艺术中心地上三节柱组立图2026.07.03.dwg` 修正 BOX 渐进式 DXF 方向：旧步骤卡片式 DXF 已替换为主视组立图第一版。每步图框包含 station 比例主视、总长/阶段 station 尺寸、当前新增零件引出标注、阶段注释和材料表；剖面图暂不生成，仅作为主视表达不清时的后续增强。当前 `T3-3GZ-6` 已重新输出 DXF 和 PNG 预览：`outputs/box-progressive-drawing-selected-20260706/T3-3GZ-6-box-assembly-drawing-steps.dxf`、`outputs/box-progressive-drawing-selected-20260706/T3-3GZ-6-box-assembly-drawing-steps-preview-first3.png`。验证记录：`docs/verification/2026-07-06-box-column-main-view-assembly-drawing.md`。

2026-07-07：用户提供 Claude 工序图技术指导 v3 后，已将 BOX 柱 DXF 兜底图从“主视示意第一版”进一步修正为累计工序图口径。当前渲染器维护累计 installed parts；PartMark、局部详图和 BOM 优先显示本步新增项；焊缝说明累计保留并绑定文字；尺寸链改为外侧全部通高 + 内侧连续详细链；折弯柱按真实 segment 倾角投影并自动推断 Section 标记，不画折断符号/偏转角。`T3-3GZ-6` 已重新输出 DXF 和前三步预览，DXF TEXT 读回中文正常，PNG 预览因 matplotlib 字体缺中文会显示方块。设计见 `docs/design/2026-07-07-box-process-drawing-claude-guidance.md`，验证见 `docs/verification/2026-07-07-box-process-drawing-claude-guidance.md`。

2026-07-07 复核修正：用户指出当前输出仍与参考 `4.西岑文化艺术中心地上三节柱组立图2026.07.03.dxf` 差距很大。已对比确认根因是把 29 个步骤纵向堆成一个 640 x 23863.9 的长卷，而参考图是 596.5 x 420 的单张阶段图纸。已修正 `box-assembly-drawing-steps.dxf` 默认只渲染一个阶段图纸，优先选择第一个 `ADD_INTERNAL_GROUP` 阶段；支持 `render_step_no` 指定阶段；PartMark 改为靠近锚点并限制旧件，BOM 放右上并限行。当前输出 bbox 为 599 x 420，实体数约 244。仍未达到 Tekla 正式图纸水平，下一步必须补真实投影/剖面几何或转 Tekla drawing object 路线。

2026-07-07 二次修正：用户明确“多张工序图是对的，但每张必须用真实几何投影、零件标号、尺寸标注，折弯/弧形需角度或半径标注”。已定位上一版真正根因：`member_T3-3GZ-6.json` 的 95 个零件有 `SolidEdges`，但 `box-assembly-drawing-steps.json` 丢失了几何快照。现已将 `result.member.Parts` 的 `SolidEdges` 合并为 drawing payload 的 `projectionEdges`，DXF 默认恢复为 29 张阶段页、3 列 sheet 网格，每页主视优先画真实投影线，缺几何才 fallback 到 station 矩形；折弯测试输出 `BEND 8°`，弧形契约输出 `ARC/Rxxx`。真实 smoke 中 95/95 零件带 `projectionEdges`，总投影边 3349 条，DXF 29 页、66564 entities、Part 层非水平/垂直线 9336 条。设计见 `docs/design/2026-07-07-box-process-drawing-true-projection.md`，验证见 `docs/verification/2026-07-07-box-process-drawing-true-projection.md`。

2026-07-07 DXF 打开性修复：用户反馈 DXF 提示无效。已确认旧 `_DxfWriter` 声明 `AC1021/R2007`，但手写文件缺少完整 `TABLES/BLOCKS` 和 `AcDbEntity/AcDbLine/AcDbText` subclass 结构；本地 `ezdxf.audit()` 可读不代表严格 CAD 可打开。现已改用 `ezdxf.new("R2007", setup=True)` 正规写出 DXF，并新增依赖 `ezdxf`。重新生成的 `T3-3GZ-6-box-assembly-drawing-steps.dxf` 包含 `TABLES=3`、`BLOCKS=1`、`AcDbEntity=66577`、`AcDbLine=63105`、`AcDbText=6748`，audit `errors=0/fixes=0`，全量测试 `121 tests OK`。

2026-07-07 胎架/翻身/步骤合并修正：按用户反馈补入真实制造口径，`BASE_MAIN_WALL` 现在输出 `fixture_face/fixture_role` 并在 DXF note 中标注 `FIXTURE`；同一底面分段主板合并为一个基准步骤；外部零件簇先按空间簇起草，再按翻身面合并。真实外部件缺 `bodyFaceId` 时，使用 `box-part-spatial-relations` 的 `projected_centroid_u/v` 推断 `RADIAL_X/Y_POS/NEG` 工作面。当前 `T3-3GZ-6` smoke 从 29 步收敛为 14 步，其中 1 个胎架基准步骤、4 个外部翻身阶段；DXF 输出 `FIXTURE RADIAL_Y_NEG`、`UP FACE ...`、`FLIP 90`，`ezdxf.audit()` 为 `errors=0/fixes=0`，全量测试 `125 tests OK`。设计见 `docs/design/2026-07-07-box-process-fixture-flip-merge.md`，验证见 `docs/verification/2026-07-07-box-process-fixture-flip-merge.md`。

2026-07-07 Tekla Open API 既有构件图探测：当前 Tekla 2017 进程可连接，`DrawingHandler.GetDrawings()` 枚举到 2394 张图纸，当前 active drawing 为空；当前模型中有大量 `10#三节柱` 构件图，但没有匹配离线 cache 的 `T3-3GZ-6 / assembly 63737929`。`--selected-model` 读到当前模型选择集为 0。已用 `--inspect-drawing-model-id 28717373` 成功打开既有 `10-3GZ-.6 / G10-Z3-06` AssemblyDrawing，并读到 sheet 内 `Part=160`、`Mark=40`、`View=4`；未执行 hide/show/save。结论：以 Tekla 原生构件图为基准，通过隐藏/显示零件做阶段图的路线机械上可行，下一步应先让用户在当前 Tekla 模型选中目标构件，并在复制图纸上测试隐藏后尺寸/标注保留情况。验证见 `docs/verification/2026-07-07-tekla-openapi-existing-drawing-inspection.md`。

2026-07-07 以 `10-3GZ-.6 / G10-Z3-06` 做 Tekla 原生隐藏工序图 POC：新增 POC 命令 `--generate-process-drawings-model-id 28717373`，读取原图 sheet 0 的 40 个唯一 drawing part id 后关闭原图不保存，再为同一 assembly 新建 sheet 1-5。5 张新图纸已保存到 Tekla 图纸列表，Mark 分别为 `[10-3GZ-.6 - 1]` 至 `[10-3GZ-.6 - 5]`；每步可见唯一零件数为 8/16/24/32/40，对应保存日志 `matched=24/48/72/96/120`、`hidden=96/72/48/24/0`。生成计划文件 `outputs\tekla-process-drawings-10-3GZ-6\tekla-process-drawings-28717373.json`。这验证了“新建同构件 sheet + HideFromDrawingView/ShowInDrawingView”可以生成原生 Tekla 阶段图；当前步骤仍是机械均分 POC，不是最终工艺分组。

2026-07-07 sheet 1-5 读回复核：`--inspect-process-sheets-model-id 28717373` 已逐张打开现有图纸并统计对象。原图 sheet 0 为 `Part=160/Mark=40/Dimensions=96/Text=5/View=4`；新建 sheet 1-5 均为 `Part=120/Mark=40/Dimensions=0/Text=0/View=3/HiddenParts=0`。结论：当前 `new AssemblyDrawing(..., sheetNumber)` 生成的是 `STANDARD` 图，不能保留原构件图尺寸、注释和阶段隐藏状态，不可作为正式工序图基础。额外尝试 `new AssemblyDrawing(id, sheet, "10#三节柱")` 生成坏 sheet 6，Tekla 报“无法加载所选图纸，图纸文件不兼容”，已删除坏 sheet 6 并恢复现场。下一步 Tekla 原生路线必须先验证“克隆既有 sheet 0”能否保留尺寸/标注；若克隆不可稳定自动化，则改为新 sheet 上重建关键尺寸、PartMark 和阶段注释。验证见 `docs/verification/2026-07-07-tekla-openapi-existing-drawing-inspection.md`。

2026-07-07 克隆路线探测：已确认当前 TS2017 China 环境中 Drawing List 的 `diaSavedSearchOptionMenu=7` 可选中 `10-3GZ-.6` 原图 sheet 0；旧宏 value `10` 选不中。value `16` 会把 Tekla 切到“选择设置”界面并临时断开 DrawingHandler，已恢复模型并将探测上限限制为 15。执行 `--probe-clone-drawing-model-id 28717373` 时，宏能选中 sheet 0 并进入 Tekla 自带 `克隆图纸` 对话，但随后弹出 `视图` 可见性选择和早期版本提示，程序侧轮询被模态 UI 阻塞；已关闭对话并确认当前 active drawing 为空、目标仍只有原图 sheet 0，没有误生成克隆图。结论：克隆路线仍可继续，但必须继续宏化 `克隆图纸/视图` 对话；公开 Open API 本身没有直接 Clone/Copy drawing 方法。

2026-07-07 sheet 1-5 现场重开复核：按用户要求关闭遗留克隆对话后重新生成机械验证 sheet 1-5，并逐张打开读回。原图 sheet 0 仍为 `Part=160/Mark=40/Dimensions=96/Text=5/View=4`；sheet 1-5 均为 `Part=120/Mark=40/Dimensions=0/Text=0/View=3/HiddenParts=0`。结论再次确认：`new AssemblyDrawing(..., sheetNumber)` 新建副页不能继承原构件图尺寸、文字注释和稳定隐藏状态，不适合做正式工序图底图。记录见 `docs/verification/2026-07-07-tekla-openapi-existing-drawing-inspection.md`。

2026-07-07 Tekla 标注复制/阶段筛选继续探测：通过 `Text.Insert()` 与 `StraightDimensionSetHandler.CreateDimensionSet()` 已证明可把原图 sheet 0 的 `Text=5`、23 组直线尺寸复制到新建副页，副页读回可达到 `Dimensions=96/Text=5`。但阶段筛选仍未解决：`Hideable` 不持久；删除多余 Drawing Part 即时有效但重开后被 Tekla 恢复；反射设置 `View.Parts` 无实际筛选效果；剪裁后锁定 sheet 会导致该副页打不开，坏 sheet 1 已删除。当前 sheet 2-5 可打开并保留复制标注，但仍是全量零件。下一步 Tekla 原生路线应转为“副页上重建/绘制阶段几何 + 复制/重建关键尺寸、PartMark、注释”，不再依赖 Tekla 自动 Part 对象隐藏。记录见 `docs/verification/2026-07-07-tekla-openapi-existing-drawing-inspection.md`。

2026-07-07 追加打开 5 张新验证副页检查尺寸/标注保留：因 sheet 1 已删除，本轮生成 `10-3GZ-.6` 的 sheet 6-10，并明确从原图 sheet 0 复制 `Text=5` 和 23 组直线尺寸集。5 张副页关闭重开后均读回 `Parts=120/Marks=40/Dimensions=96/Text=5/Views=3/HiddenParts=0`。结论：尺寸和文字标注复制保存稳定，但 PartMark 和零件对象仍是全量，阶段隐藏仍不持久；正式工序图不能再靠 AssemblyDrawing 自动 Part 对象隐藏，应改为按工序步骤重建阶段几何并复制/重建关键尺寸、零件标号和阶段注释。记录见 `docs/verification/2026-07-07-tekla-openapi-existing-drawing-inspection.md`。

2026-07-08 胎架真实投影 GA 原型：已新增 Tekla POC 命令 `--probe-ga-fixture-projection-model-id`，针对 `10-3GZ-.6 / modelId=28717373` 生成 `PROCESS-FIXTURE-10-3GZ-6-S1`。第 1 步 8 个零件从 Tekla `Part.GetSolid().GetEdgeEnumerator()` 读取 248 条 solid edge，按胎架坐标投影后插入 248 条普通 Line，`failed=0`；frame 为 `MODEL_AXIS_2_HEIGHT_0_MIN_ON_FIXTURE`，即模型长轴 2 转图纸横向，模型轴 0 最小侧为胎架底面。重开读回 `lines=248/texts=4/dims=2/parts=0/marks=0/views=0`。结论：重建几何可稳定保存且不被 Tekla 自动 Part 对象污染；下一步要补可见边过滤、真实工艺步骤映射、PartMark 和定位尺寸避让。记录见 `docs/verification/2026-07-07-tekla-openapi-existing-drawing-inspection.md`。

2026-07-08 胎架 U-stage GA 原型：针对 `10-3GZ-.6 / modelId=28717373` 生成 `PROCESS-FIXTURE-U-10-3GZ-6-S1`。根因确认：该构件主壁板在 Tekla 中是单个 `BOX600*600*30*30` 主零件 `28705233 / 10-3Z-128`，不是 4 个独立板件；因此第一阶段“底板 + 两侧板”需要走 `VIRTUAL_DECOMPOSED_BOX_PROFILE` 虚拟拆解。输出图纸按 Tekla solid 外包尺寸与 BOX profile 厚度绘制 U 形主视投影，长度 `3505`、宽 `600`、壁厚 `30`，插入 `lines=12/texts=5/dims=4`，重开读回 `parts=0/marks=0/views=0`。证据：`outputs/tekla-process-drawings-10-3GZ-6/tekla-ga-fixture-u-stage-28717373-step1.json`。
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
5. 当前 BOX 渐进式构件图 DXF 已从 station/lane 简化图升级为多张阶段页 + per-part `projectionEdges` 真实主视投影，并已补胎架底面、主板分段合并、外部翻身面合并。下一步重点是提升尺寸/PartMark 自动避让、最佳视向选择、正式剖面/局部详图几何，以及让 `CAN_SIDE` 侧焊判定接入工艺阈值；也可切回 Tekla 2017 active drawing 套图路线，在 Tekla 图纸对象中控制阶段显示/隐藏、PartMark、尺寸和材料表。

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
- BOX 外轮廓 trace 验证：docs/verification/2026-06-23-box-wall-trace.md
- BOX 主壁板确认集合验证：docs/verification/2026-06-23-box-main-wall-confirmed-set.md
- BOX 内外关系层验证：`docs/verification/2026-06-23-box-part-spatial-relations.md`
- BOX station topology 诊断：`docs/verification/2026-06-24-box-station-topology-export-diagnostics.md`
- BOX section segment topology 导出器 v2 验证：`docs/verification/2026-06-24-box-section-segment-topology-exporter-v2.md`
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
2026-07-09：工序图标注/避让层第一版已落地。新增纯 Python `AnnotationLayout` 核心与 DXF adapter；Tekla U-stage POC 改为 `DrawingAnnotationLayout` DTO 后再用普通 `Line/Text` 渲染，避免 GA sheet 上原生 `StraightDimensionSet` 造成黑三角/粉色问号/乱码。目标 `10-3GZ-6 / modelId=28717373` 已生成 clean 图 `PROCESS-FIXTURE-U-10-3GZ-6-S1-CLEAN`，mark `[24]`；JSON 证据 `outputs/tekla-process-drawings-10-3GZ-6/tekla-ga-fixture-u-stage-28717373-step1.json` 显示 `annotation_layout_status=OK`、`annotation_collision_count=0`、`dimension_inserted=False`、`primitive_dimension_lines_inserted=True`、`layout lines=12/texts=9`、重开读回 `Lines=24/Texts=9/Dimensions=0/StraightDimensions=0/StraightDimensionSets=0/Parts=0/Marks=0/Views=0`。验证记录见 `docs/verification/2026-07-07-tekla-openapi-existing-drawing-inspection.md`。
