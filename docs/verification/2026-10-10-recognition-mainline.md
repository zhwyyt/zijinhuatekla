# 识别主线收尾验证

## 基线与人工验收

2026-10-10 用户明确确认最后实验成果已人工验收，主轴必须使用实验算法。本轮从 `experiment/part-role-geometry-assertions` 的 `4625d14` 和已验收工作区建立 `feat/recognition-mainline`，不推倒算法、不合并零件出图分支。

导出器已验收源码另外保存在 `I:\xingcaisuanfa` 的 `feat/accepted-recognition-axis`、提交 `71a95bb`。保存范围是分组跨度主轴、实体采样、member extractor、bundle exporter 和 DTO；其它未提交业务资料和编译产物保留现场。来源为 `assemblyParts.alignedSpanCentroid`。

## 本轮改动

- 角色分类器接入正式合并 Excel、单构件流水线和 JSON；保留单参数实验接口及原规则。
- 正式批量报告固定三张主表：构件角色、构件复杂度、零件特征。CLI `export-excel` 与 GUI 共用入口。
- `GuidePolyline/AxisSegments` 保留实际折线链；角色按首尾弦判姿态，牛腿方向优先使用 `Member.MainAxis` 主段。
- 主轴同时检查 bundle/member 的 source，旧缓存或来源不一致在角色表及 GUI 明确提示。
- 连接缺失仅写辅助复核表；失败装配不遗留部分主表行，并写失败表，批量 CLI 返回非零。
- 原 STATUS/TASKLIST（含原未提交更新）原样保存在 `2026-10-10-pre-mainline-memory.md`；根路标改为短的当前状态。
- 本地 CAD/Excel、cache、outputs 及出图参考资料没有删除或搬动；锁文件、历史工具临时目录和本地出图参考从 Git 现场中排除。

## 自动验证

- `python -m unittest discover -s tests`：`Ran 269 tests ... OK`。
- 正式入口新增覆盖：模型外下一节柱、三张主表、真实折线链/主段、旧主轴/混合来源、编号不补角色、连接候选不改角色、失败装配行一致性、单构件 JSON 和 GUI/CLI。
- 既有角色、楼梯/花纹平台/埋件几何、主材、复杂度、零件特征和连接复核用例保持通过。
- 导出器 `dotnet build ... --no-restore -v:q`：0 警告、0 错误。
- 测试及离线日志：`outputs/recognition-mainline-20261010/full-tests.log`、`offline-smoke.log`、`summary.json`。
- 初次新增 Excel 读回测试出现 Windows 文件锁，改为从 BytesIO 读取小测试工件后通过；未修改生产分类规则来绕过失败。

## 离线真实数据 smoke

输入 `cache/20260922_173818`，通过正式批量 CLI 运行：

```powershell
python -m zijinhua_tekla.cli export-excel --root cache/20260922_173818 --project-name 主线离线验证 --project-area 历史选择集 --out outputs/recognition-mainline-20261010
```

结果：角色 289 行、复杂度 289 行、零件特征 4044 行、识别失败 0、主轴需复核 289、缺失连接候选 0。Excel 为 `outputs/recognition-mainline-20261010/主线离线验证_历史选择集.xlsx`。

该历史包的构件角色均为 `UNKNOWN`，不能用这次 smoke 宣称真实角色识别精度通过；正式入口的已验收规则由新增集成回归验证，用户此前完成的人工验收单独成立。

本地已导出 cache 的 source 都是 `mainPart.longestLocalAxis`，包括 `external-links-20260928`；因此此次 smoke 证明入口和历史数据诊断闭环，不宣称真实数据已重新使用新主轴。用户已完成的算法人工验收仍有效，现场只需用当前 Runner 更新数据。

## 独立工作区与提交检查

零件出图 worktree `I:\tmp\zijinhuatekla-part-drawing-engine` 仍为 `codex/offline-part-drawing-engine`、`7a9fb37`，工作区干净，本轮未修改。

提交前执行 CCG verify-change 并核对 staged 文件范围、Git numstat、设计、README 和相关测试。CCG 的 staged 模式不统计行数，且当前脚本不把 `.cs` 识别为代码；导出器另用源码范围核对、构建和用户人工验收作为证据，不能把该脚本的零行统计当作无代码改动。

## 抽象复盘

适用场景：模型导出器与离线识别分属不同仓库，存在实验算法、正式入口及历史缓存。

核心认知：算法人工验收、正式入口接通和缓存版本更新是三个独立事实。交付需同时保存源码基线、验证输出入口、检查 bundle/member 来源并保留主段与完整折线的语义；状态文件只记录当前事实，历史证据独立保存。

可防止的失败：把已验收但未接入的能力当正式输出，把新算法配旧缓存当新结果，把主段方向替代整件首尾姿态，或只读旧交接就回退算法。

已验证证据：正式报告三表与 269 回归通过；289 根历史主轴全部明确进入需重导提示；独立出图 worktree 保持原提交及干净状态。

## 未做与后续

本轮未连接真实 Tekla、未重新导出选择集，未做新图纸图面验收，也未重写或推送 main。后续开发从识别收尾分支继续，真实导出更新和零件出图分别安排独立阶段。
