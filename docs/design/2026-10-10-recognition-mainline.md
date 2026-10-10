# 识别主线收敛

## 决策与范围

2026-10-10 用户确认：实验分支的最后成果已经人工验收，包括构件结构角色和分组跨度主轴。以当前 `experiment/part-role-geometry-assertions` 工作区为基线，在 `feat/recognition-mainline` 收尾；不得回退到最长零件主轴或按构件编号判角色。

正式主线包含构件角色、构件复杂度、零件特征三类识别。零件出图继续留在 `I:\tmp\zijinhuatekla-part-drawing-engine`、`codex/offline-part-drawing-engine`，本轮不修改该 worktree、不合并它的提交、不删除旧样例或图纸。

## 实现计划

1. 将已验收的角色分类器及连接复核纳入版本管理，保留现有规则和证据，不重新设计分类算法。
2. 统一消费导出器 `AlignedSpanMemberAxis` 的结果，来源为 `assemblyParts.alignedSpanCentroid`；保留 `Member.MainAxis` 主段和 `AxisSegments/GuidePolyline` 折线链的区别。主轴算法实现在 `I:\xingcaisuanfa`，Python 不复制一套算法。
3. 在现有合并 Excel 入口增加构件角色表，保留构件复杂度和零件特征表；连接缺失仍只产生复核候选，不自动确认连接。
4. 打通批量 CLI、GUI 和离线流水线；输出主轴来源及旧缓存提示，避免把历史最长零件主轴当作已验收主轴。
5. 将历史 STATUS/TASKLIST 内容原样保存到验证记录，重写短的项目状态、任务队列、README 和根 AGENTS 路标。忽略 CAD 锁文件和历史工具临时目录，不搬动正在使用的本地业务资料。
6. 最小相关回归、完整单元测试、离线样例检查和 CCG verify-change 后，仅提交本轮相关文件并推送收尾分支。

`I:\xingcaisuanfa` 的已验收主轴和外部连接实现也需要独立保存源码基线：仅收敛 `AlignedSpanMemberAxis`、`TeklaPartAxisSampler`、member extractor、bundle exporter 和 DTO，不带入该仓库其它业务资料和编译产物。Python 侧仅消费这套实现，不新增一份主轴算法。既有主材/加工口径算法保持不动，其字段不冒充构件结构角色。

## Acceptance Criteria

- 合并 Excel 固定提供 `构件角色`、`构件复杂度`、`零件特征` 三张主表；角色表保留装配身份、角色/子类、姿态、轴线形态/折点、规则、置信度和证据。
- 已验收规则经正式入口可观察，包括模型外下一节柱、花纹板休息平台、楼梯、埋件与倾斜单杆；未知/冲突继续保持未知。
- 构件编号不成为结构角色的判据，连接距离不成为焊缝/螺栓事实。
- 已验收主轴来源可追踪；折线角色按首尾弦判姿态，复杂度保留真实折点，主材仍使用主段。
- 历史缓存允许诊断，但必须明确标示需要重新导出，不能冒充新主轴验收结果。
- 构件行与零件行来自同一导出包；失败的装配可定位，不能只写部分主表后算成功。
- GUI 和 CLI 使用同一批量报告函数；出图 worktree 的分支、提交、文件状态保持不变。
- 已人工验收与本轮自动集成验证分开记录；不宣称本轮重新完成真实 Tekla 联调。

## Verification Plan

- 回归角色分类器和连接复核的现有用例。
- 增加正式 Excel 的角色、折线主轴、旧缓存提示、失败装配及缺失连接候选用例。
- 回归复杂度/零件特征及流水线，增加批量 CLI 和 GUI 完成提示验证。
- `python -m unittest discover -s tests`，完整输出落盘，聊天只报告计数和结论。
- 对本地导出缓存做有界离线 smoke，输出到独立 `outputs/recognition-mainline-20261010`，明确缓存主轴版本；不自动启动真实 Tekla 导出。
- 提交前运行 CCG `verify-change --mode staged`，检查相关设计、README 与测试同步。

## 2026-10-10 真实选择集补充：装配实例身份

979 个装配的真实导出暴露同号 member 文件覆盖：只有 652 个独立文件，327 个装配原先读取其它同号实例。完整 `members/batch_summary.json` 保留了全部实例，不需要重新推算几何或更改已验收算法。

批量入口优先按 `AssemblyId` 索引 batch 快照；编号只校验位置号一致。旧独立文件只在实例 ID 一致时使用，缺失的旧身份字段仅兼容单一位置号；同号多实例缺身份必须失败。重复 batch ID 必须明确拒绝，不能静默覆盖。单构件指定 assembly ID 时使用相同解析器。

Acceptance Criteria：同号水平/竖直实例保留各自轴线与姿态；不能恢复的实例进入识别失败；不遗留半套主表；已验收角色、复杂度、特征算法不变。

Verification Plan：同号不同姿态回归、缺失 batch / 重复 ID / 位置号不符 / 无独立文件但有完整 batch 的解析测试、单构件显式 ID 回归；随后用同一已导出的 979 装配包重新运行正式入口，并保留首次结果作为失败证据。
