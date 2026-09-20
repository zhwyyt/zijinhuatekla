# TASKLIST

- [x] 导出器 0.3.3-index-once：剖口对象全模型只索引一次；GitHub 标签 `rollback/exporter-0.3.3-index-once-20260920`。
- [x] 导出器 0.3.4-single-pass：识别导出关闭截面采样，选择集 Extract+Bundle 合成一次循环；工作平面仍未改。
- [x] 用 Tekla 当前选择集实测 0.3.4：289 装配，剖口 0 差异，识别 4044 行失败 0。
- [x] 收紧 Box/H 叠层：闭合环与 H frame 同时存在时不覆盖（避免 6GL 主材打成 BOX主壁板）。
- [ ] 重导当前选择集，确认 6GL 恢复 H 上/下翼缘/腹板，5GKZ 主材仍为 BOX主壁板。
- [x] 确认 Tekla 当前选择集零件图快照导出器设计：命令行独立模式、只处理直接选中的平板 Part、每实体一份 `partDrawingSnapshot.v1`、Python 单独出图。
- [x] 在隔离 worktree `I:\tmp\xingcaisuanfa-part-snapshot-exporter` 按 TDD 实现 `--export-part-drawing-snapshots`、DTO、平板质量门、最终面环、孔槽与汇总输出。
- [x] 完成 C# 构建/测试和 Python 跨语言契约回归：C# 26 tests、Python focused 11 tests、完整 165 tests。
- [x] 用真实 Tekla 平板 `T3-PX-317` 跑通 snapshot -> DXF/PDF：导出 EXPORTED=1，出图 REVIEW_REQUIRED=1，DXF audit 0/0，PDF A3 单页。
- [ ] 修复/提升孔径与孔定位尺寸布局：当前 17 annotations unplaced，图纸保持 REVIEW_REQUIRED。
- [ ] 建立零件图子技能架构：参考 SolidWorks `autocad-automation` 子技能模式，将离线出图 5 个模块抽成 6 个独立子技能（snapshot-exporter、geometry-normalizer、feature-recognizer、dimension-generator、layout-optimizer、drawing-renderer），每个子技能有独立 SKILL.md、契约 schema、约束规则和典型错误库；设计见 `docs/design/2026-07-28-part-drawing-subskills-architecture.md`。
- [ ] 补 ARC 原生圆心证据导出与真实弧形平板验收；无法证明的曲线继续拒绝。
- [ ] 用真实 Tekla 平板选择集跑通 snapshot -> DXF/PDF，并完成人工图面复核后再决定是否合并 PR #1。
- [x] 建立可复用规则层：规格标准化、PL 解析、名义加工尺寸、BH 拆板派生。
- [x] 建立 Excel/Tekla bundle 对齐层：按零件号、规格、长度、几何候选匹配。
- [x] 输出 T3-5GKZ-10 对齐结果：CSV、JSON、Markdown。
- [x] 写入验证记录：单元测试结果和样例分析命令。
- [ ] 下一阶段补充构件类型、零件角色、焊接/螺栓/空间关系和配送顺序。
- [ ] 建立构件装配顺序数据契约与报告。
- [ ] 建立焊接顺序数据契约与报告。
- [ ] 建立配送顺序数据契约与报告。
- [ ] 建立图纸自动标注数据契约与报告。
- [x] 建立 BOX 柱子渐进式构件图步骤计划与第一版可查看输出：已输出 `box-assembly-drawing-steps.json/csv/md/dxf`，按信息组/阶段逐步增加主壁板、内部组和外部簇；Tekla 2017 POC 已验证 API 连接与 AutoDrawing 生成构件图，CAD/DXF 作为当前第一版查看兜底；设计见 `docs/design/2026-07-06-box-column-progressive-drawing-steps.md`，验证见 `docs/verification/2026-07-06-box-column-progressive-drawing-steps.md`。旧卡片式 DXF 已被主视组立图第一版替代，随后又被 Claude v3 累计工序图版本替代。
- [x] 按 Claude v3 指导修正 BOX 渐进式 DXF 的表达方向，并在用户复核后纠正“29 步纵向长卷”错误：曾短暂改为默认单阶段图纸，但用户随后明确多张工序图是正确方向，关键是每张必须是真实构件图表达。该中间修正记录见 `docs/verification/2026-07-07-box-process-drawing-claude-guidance.md`。
- [x] 将 BOX 工序 DXF 从 station/lane 简化图升级为真实投影原型：`box-assembly-drawing-steps.json` 现在从 `result.member.Parts.SolidEdges` 合并 `projectionEdges`，`box-assembly-drawing-steps.dxf` 默认输出 29 张阶段页、3 列 sheet 网格，每页主视优先画真实投影线并保留 PartMark、尺寸链和 BOM；折弯测试输出 `BEND 8°`，弧形契约支持 `ARC/Rxxx`。当前 `T3-3GZ-6` 已生成 `outputs/box-progressive-drawing-selected-20260706/T3-3GZ-6-box-assembly-drawing-steps.dxf` 与 `outputs/box-progressive-drawing-selected-20260706/T3-3GZ-6-box-assembly-drawing-steps-preview-first-row-true-projection.png`；设计见 `docs/design/2026-07-07-box-process-drawing-true-projection.md`，验证见 `docs/verification/2026-07-07-box-process-drawing-true-projection.md`。
- [x] 修复 BOX 工序 DXF 在严格 CAD 中提示无效的问题：旧手写 DXF 缺完整 R2007 `TABLES/BLOCKS` 与 subclass 结构，现改用 `ezdxf` 正规写出；已重新生成 `outputs/box-progressive-drawing-selected-20260706/T3-3GZ-6-box-assembly-drawing-steps.dxf`，读回 `TABLES=3/BLOCKS=1/AcDbLine=63105/AcDbText=6748`，audit `errors=0/fixes=0`。
- [x] 补入 BOX 工序图胎架/翻身/步骤合并口径：基准主板按胎架底面合并输出 `fixture_face`，真实外部件缺 `bodyFaceId` 时用 `projected_centroid_u/v` 推断 `RADIAL_*` 工作面，外部零件簇按翻身面合并。当前 `T3-3GZ-6` 从 29 步收敛为 14 步，DXF note 输出 `FIXTURE/UP FACE/FLIP`，设计见 `docs/design/2026-07-07-box-process-fixture-flip-merge.md`，验证见 `docs/verification/2026-07-07-box-process-fixture-flip-merge.md`。
- [ ] 下一阶段不要回退到 station 简化图：继续提升真实投影页的尺寸/PartMark 自动避让、最佳视向选择、正式剖面/局部详图几何，并将 `CAN_SIDE` 侧焊判定接入工艺阈值；或切回 Tekla 2017 active drawing 套图路线，用 Tekla 图纸对象控制阶段显示/隐藏、PartMark、尺寸和材料表。
- [x] 读回 Tekla 2017 active drawing 机械 5 步 sheet 的尺寸/标注保留效果：原图 sheet 0 为 `Part=160/Mark=40/Dimensions=96/Text=5/View=4`；新建 sheet 1-5 均为 `Part=120/Mark=40/Dimensions=0/Text=0/View=3/HiddenParts=0`。结论：`new AssemblyDrawing(..., sheetNumber)` 生成的 `STANDARD` 图不能保留原构件图尺寸、文字注释和阶段隐藏状态，不可作为正式工序图基础；探测 `new AssemblyDrawing(id, sheet, "10#三节柱")` 生成坏 sheet 6，已删除并记录。验证见 `docs/verification/2026-07-07-tekla-openapi-existing-drawing-inspection.md`。
- [ ] 继续 Tekla 2017 原生路线：已确认 Drawing List filter value `7` 可选中原图 sheet 0，旧 value `10` 不可用；`CloneDrawing.cs` 可进入 `克隆图纸` 对话但未能对同一构件生成可读克隆 sheet。已证明原图 `Text=5` 与 23 组直线尺寸可复制到副页，sheet 6-10 五张新验证页关闭重开后均稳定读回 `Dimensions=96/Text=5`；但 `Hideable`、删除 Drawing Part、`View.Parts`、锁定剪裁都不能稳定形成阶段零件集合，且 PartMark/Part 仍是全量。下一步应停止依赖 AssemblyDrawing 自动 Part 隐藏，转为在新 sheet/GA 图纸上按工序步骤重建/绘制阶段几何，同时复制/重建关键尺寸、PartMark、阶段注释和必要局部视图，再接正式 BOX 工序 planner。已生成首张胎架真实投影 GA 原型 `PROCESS-FIXTURE-10-3GZ-6-S1`：8 个零件、248 条 Tekla solid edge、248 条普通 Line，重开后 `lines=248/texts=4/dims=2/parts=0/marks=0/views=0`。
- [x] 建立箱型柱主壁板制造整板与 Tekla 分段复核候选报告。
- [x] 人工确认 T3 箱型柱主材分段集合，并补 Case Bank 回归样例。
- [x] 补轴线 station 与连续性初版证据，制造范围报告输出 `station_ranges/continuity_gaps/continuity_level`。
- [x] 在 `I:\xingcaisuanfa` 导出器补 `memberAxisEvidence/mainMaterialEvidence`，提供壁板面候选、主轴 station、相邻 gap 证据。
- [x] 重新导出 T3-5GKZ-10 新 cache，并在 `I:\zijinhuatekla` 消费新字段建立 BOX 主材分段集合算法。
- [x] 将主材分段算法上抽为统一入口，并接入 H/GL 梁策略与 BOX fallback。
- [x] 补 Python 侧 BOX 截面候选证据，派生 WALL_CORE/OUTER_ATTACHMENT/INNER_STIFFENER_OR_DIAPHRAGM/UNKNOWN 并接入主材分段 evidence summary。
- [x] 建立 BOX 内外关系层 `BOX_PART_SPATIAL_RELATION`，先区分 `MAIN_WALL/INSIDE_BODY/OUTSIDE_ATTACHMENT/BOUNDARY_OR_THROUGH/INSUFFICIENT_EVIDENCE`，不在本阶段细分零件角色。已升级为 Tekla solid 原生 station loop + 每零件 start/mid/end 三点判定。
- [x] 修正 BOX 内腔纯几何判定：跳过局部不完整 station topology，避免内腔竖向板/横板被误判为 `BOUNDARY_OR_THROUGH`；T3-5GKZ-8 的 16 个目标实体已全部回到 `INSIDE_BODY`，T3-5GKZ-10 仍保留真实边界候选。
- [ ] 继续提升统一主材分段算法：H/GL 已将 station frame 主路径迁入 composite native，并将主板轴向连续性收敛为收尾相连 + 同截面侧 + Weld/Contact 三条件；native 可从全 parts 池补齐未被 station 切片命中的端部主板，旧 `main_material_groups` 仅作 fallback；BOX 已形成闭合截面外轮廓 trace 种子、主轴 station 连续扩展和截面复核的最终确认集合，并修复 `T3-5GKZ-2` 中 seed 后续 `flange_candidate/web_candidate` 主板段未扩展的问题；下一步继续稳定四壁板 face chains、降低对 Case Bank 反馈的依赖；T 型/十字/圆管新增策略，并将报告文件名迁移为通用 `main-material-segment-groups`。
- [x] 建立组合截面构件主材识别：沿构件主轴自动切 N 个截面体系区段，分别识别十字柱核心板、外侧翼缘主板、BOX 主壁板、过渡主板以及 H/BH/GL 翼缘/腹板主板；已用 fresh Tekla 当前选择集验证 `T2-3GKZ-12` 输出 6 个区段和 `CROSS_FLANGE_MAIN_PLATE=56`，并已将 H/GL station frame 主路径迁入 composite native，按收尾相连 + 同截面侧 + Weld/Contact 三条件补齐主板链，允许有链证据的变厚主板但禁止 name 判定，旧主材组适配仅作 fallback，记录见 `docs/verification/2026-06-27-composite-main-material-segments.md`。
- [x] 固化普通零件编号精准一致硬约束，禁止几何相似自动匹配。
- [ ] 建立缺失/冲突零件复核工具：全模型搜索、候选排序、几何候选复核报告。
- [x] 建立 `PartFeatureSnapshot` 契约，承接 `I:\autoweb\teklatest` 的零件特征提取结果。
- [x] 建立 `MemberBodyClassifier` 接口，承接已有分类和 `BH/H/BOX` profile-family 证据。
- [x] 建立 `PartRoleClassifier` 接口，并从 CLI 抽出角色、工序、形状推断。
- [x] 建立 `BracketClassifier` 入口，承接 `I:\lingjianjuesemimo` 的牛腿 evidence code。
- [x] 建立 Case Bank：每个人工确认案例必须有失败归因、期望标签、证据字段和回归测试。
- [x] 建立 bundle/member 到 `AppendageClusterFeatures` 的空间特征适配层。
- [x] 建立架构层级骨架：`architecture`、`quality`、`pipeline`。
- [x] 在导出器补 `sectionProjectionEvidence` 截面投影证据，替代异形 BOX 内外判断对包围盒/径向分桶的依赖。
- [x] 补 `MemberBodyClassifier` 的截面 trace、station topology、closed loop 消费逻辑；BOX 内外关系已接入 Shapely 多 loop 拓扑和内腔 loop 输出，并新增 station topology diagnostics。已整体修复导出器：输出 `sectionSegments/sectionLoops`，替代旧退化 point set。
- [x] 建立 `adapters` 包，并把 Tekla bundle/member/Excel 读取从 CLI 迁入。
- [x] 建立 `reports` 包，并把 CSV/JSON/Markdown 输出从 CLI 迁入。
- [x] 建立 `classifiers` 包门面，逐步包住现有 `member_classifier`、`part_roles`、`bracket_classifier`。
- [x] 建立完整 offline pipeline orchestration，把 adapters、quality、features、classifiers、reports 串成可复用入口。
- [x] 将空间关系层接入 offline pipeline，并在报告中输出附属件簇角色摘要。
- [x] 输出空间分类明细 CSV/JSON，并在 Markdown 中列出 Bracket 候选供人工复核。
- [x] 在空间分类明细中输出 cluster 内部 Tekla part ids，支持模型定位复核。
- [x] 输出 Data Quality Gate 问题明细 CSV/JSON，支持缺失/冲突零件复核。
- [x] 将 Data Quality Gate 问题转换为质量复核任务 JSON，区分全模型搜索和编号/规格冲突核对。
- [x] 将质量复核任务同时输出 CSV，支持 Excel 人工筛查。
- [x] 输出质量复核摘要 JSON/CSV，按问题类型和建议动作分组。
- [x] 建立缺失零件全模型候选搜索只读内核。
- [x] 将缺失零件候选搜索接入报告输出。
- [x] 建立同名冲突/几何候选复核报告。
- [ ] 人工复核 T3 空间诊断中的 2 个 Bracket 候选，并沉淀为 Case Bank 样例。
- [ ] 依据复核结果决定是否补 C# 导出器的 root/contact/overhang 精细字段。
- [x] 将 Case Bank 持久化为 JSON/CSV，并接入回归样例加载。
















- [x] 继续处理 BOX 末端 4 个 `STATION_TOPOLOGY_NOT_CLOSED` station：已归因为端部/附件触发 station，新增 `station_scope=END_TRANSITION_OR_ATTACHMENT_TRIGGERED` 与 `END_TRANSITION_NOT_BODY_CORE`，不再误报核心 BOX 截面失败。


- [x] 新导出契约全链路核对：已补齐 CLI 报告打印、offline report/pipeline 测试、section segment v2 设计契约；继续迁移旧契约消费者，BOX 主壁板 seed 优先用 `boxSectionEvidence.sectionLoops/segments`，附属件簇主体边界优先用确认主壁板 ids，制造范围/拓扑诊断优先用新 station/loop 字段；已用 T3-5GKZ-2/T3-5GKZ-10 smoke 验证完整报告输出和主壁板回归。



## 现场收敛待办 - 2026-06-26

- [x] H 钢位置关系阶段已收敛并推送：`55e7fc3 Add H beam side and station slice classifiers`。
- [x] H 钢 direct profile frame 导出器已在 `I:\xingcaisuanfa` 另行提交并 push，本仓库本轮不继续处理 xingcaisuanfa。
- [ ] 收敛剩余 BOX station topology / BOX 内外关系现场：核对 `box_part_spatial_relations.py`、`box_station_topology_diagnostics.py`、相关 BOX 测试和 2026-06-24 验证记录。
- [ ] 收敛剩余 offline report/pipeline 现场：核对 `cli.py`、`pipeline/offline.py`、`reports/offline.py`、`tests/test_pipeline_offline.py`、`tests/test_reports_offline.py`。
- [ ] 判断 `pyproject.toml` 新增依赖和 `docs/design/2026-06-23-main-material-segment-export-contract.md` 修改是否属于 BOX topology 提交范围。
- [ ] 对未跟踪文件分组：BOX 验证记录保留并提交；`聊天记录.md`、`docs/project-overview.md` 需人工确认是否入库。
- [ ] 每个收敛提交前运行最小相关测试；最终再跑 `python -m unittest discover -s tests` 或当前可行的完整测试集合。







- [x] 生成 `10-3GZ-6` 第一阶段“底板 + 两侧板”Tekla GA 工序图：确认主壁板是单个 `BOX600*600*30*30` 主零件而非独立板件，已用 `VIRTUAL_DECOMPOSED_BOX_PROFILE` 从 Tekla solid 外包尺寸和 profile 厚度生成 `PROCESS-FIXTURE-U-10-3GZ-6-S1`，重开读回 `lines=12/texts=5/dims=4/parts=0/marks=0/views=0`，证据见 `outputs/tekla-process-drawings-10-3GZ-6/tekla-ga-fixture-u-stage-28717373-step1.json`。
- [x] 抽出工序图 AnnotationIntent / AnnotationLayout 标注与避让层：已实现纯 Python `AnnotationLayout` 核心、DXF renderer adapter，以及 Tekla U-stage layout DTO；`10-3GZ-6` 新 clean 图 `PROCESS-FIXTURE-U-10-3GZ-6-S1-CLEAN` / `[24]` 输出总长、截面宽、壁厚、PartMark、胎架/阶段说明，读回 `LayoutStatus=OK/CollisionCount=0/dimension_inserted=False/primitive_dimension_lines_inserted=True/StraightDimensions=0/StraightDimensionSets=0`，证据见 `docs/verification/2026-07-07-tekla-openapi-existing-drawing-inspection.md`。
