# TASKLIST

- [x] 建立可复用规则层：规格标准化、PL 解析、名义加工尺寸、BH 拆板派生。
- [x] 建立 Excel/Tekla bundle 对齐层：按零件号、规格、长度、几何候选匹配。
- [x] 输出 T3-5GKZ-10 对齐结果：CSV、JSON、Markdown。
- [x] 写入验证记录：单元测试结果和样例分析命令。
- [ ] 下一阶段补充构件类型、零件角色、焊接/螺栓/空间关系和配送顺序。
- [ ] 建立构件装配顺序数据契约与报告。
- [ ] 建立焊接顺序数据契约与报告。
- [ ] 建立配送顺序数据契约与报告。
- [ ] 建立图纸自动标注数据契约与报告。
- [x] 建立箱型柱主壁板制造整板与 Tekla 分段复核候选报告。
- [x] 人工确认 T3 箱型柱主材分段集合，并补 Case Bank 回归样例。
- [x] 补轴线 station 与连续性初版证据，制造范围报告输出 `station_ranges/continuity_gaps/continuity_level`。
- [x] 在 `I:\xingcaisuanfa` 导出器补 `memberAxisEvidence/mainMaterialEvidence`，提供壁板面候选、主轴 station、相邻 gap 证据。
- [x] 重新导出 T3-5GKZ-10 新 cache，并在 `I:\zijinhuatekla` 消费新字段建立 BOX 主材分段集合算法。
- [x] 将主材分段算法上抽为统一入口，并接入 H/GL 梁策略与 BOX fallback。
- [x] 补 Python 侧 BOX 截面候选证据，派生 WALL_CORE/OUTER_ATTACHMENT/INNER_STIFFENER_OR_DIAPHRAGM/UNKNOWN 并接入主材分段 evidence summary。
- [x] 建立 BOX 内外关系层 `BOX_PART_SPATIAL_RELATION`，先区分 `MAIN_WALL/INSIDE_BODY/OUTSIDE_ATTACHMENT/BOUNDARY_OR_THROUGH/INSUFFICIENT_EVIDENCE`，不在本阶段细分零件角色。已升级为 Tekla solid 原生 station loop + 每零件 start/mid/end 三点判定。
- [ ] 继续提升统一主材分段算法：H/GL 减少对 name 的依赖，BOX 已形成闭合截面外轮廓 trace 种子、主轴 station 连续扩展和截面复核的最终确认集合，下一步需要导出更多 station samples 稳定四壁板 face chains、降低对 Case Bank 反馈的依赖；T 型/十字/圆管新增策略，并将报告文件名迁移为通用 `main-material-segment-groups`。
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
- [ ] 补 `MemberBodyClassifier` 的截面 trace、station topology、closed loop 消费逻辑；BOX 内外关系已先接入 Tekla solid station loop，后续需补真正多 loop 拓扑和内腔 loop 输出。
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













