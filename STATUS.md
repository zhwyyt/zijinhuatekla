# STATUS

## 当前阶段

2026-10-10：分支 `feat/recognition-mainline`。识别主线集成后，用户指出 GKZ 牛腿归零；已修复长主轴下分段 BOX 壁板特征消费，正式重跑并完成新旧单元回归。已验收主轴保持不变，新增派生字段复核不冒充全量人工验收。

## 已完成

- 正式 CLI / GUI 共用角色、复杂度、零件特征三表；算法集成基线 `0701e89` 已推送。
- 最新报告 979 / 979 / 7086 行、16998 件、0 运行失败；16 个 GKZ 牛腿恢复 2～8，32 个新旧实例数量及牛腿单元身份均与旧基线一致；279 tests OK。
- 与上一版相比，角色全表及其余 963 个装配字段完全一致；GKZ 的主材/内外关系及派生形状变动已单列追踪。
- 此前已消除 327 个同号实例快照串用；新旧选择范围共同 264、新增 715、未选 25。
- 历史现场见 [收敛前记录](docs/verification/2026-10-10-pre-mainline-memory.md)，初次集成见 [主线验证](docs/verification/2026-10-10-recognition-mainline.md)。

## 版本与边界

- 主轴：`AlignedSpanMemberAxis`，source=`assemblyParts.alignedSpanCentroid`；`I:\xingcaisuanfa` 已保存源码基线 `feat/accepted-recognition-axis` / `71a95bb`，Runner 构建 0 警告、0 错误。
- 最新数据：`cache/selected-mainline-20261010-105609`；最终 Excel 以 `outputs/selected-mainline-20261010-105609/gkz-fixed/` 为准。`corrected/` 为牛腿修复前版本，`corbel-fixed/` 为范围保护前失败证据。
- 零件出图留在 `I:\tmp\zijinhuatekla-part-drawing-engine`、`codex/offline-part-drawing-engine`，本轮不修改。
- 本地 `main` 仍在旧出图历史上，不是当前识别基线；先推送收尾分支，不直接改写 main。

## 下一步

复核剩余 6 个主材类型变化（含 4 个 BOX → UNKNOWN）及 1 个零长度主轴；核对分段主体派生零件标记，不按编号硬补，不回退已验收主轴。621 个未知角色保留规则的不足/冲突。零件出图继续独立开发。

## 最新 Handoff

[GKZ 牛腿回归记录](docs/verification/2026-10-10-gkz-corbel-regression.md) 包含根因、32/32 数量与单元身份、279 项回归、979 装配字段对比及抽象复盘；未新增逐零件人工验收。此前导出与实例修复见 [选择集记录](docs/verification/2026-10-10-selected-mainline-reexport-comparison.md)。

修复提交 `f5e0ffc` 和交付记录 `6309a5e` 已推送至 `origin/feat/recognition-mainline`。远端 `zhwyyt/zijinhuatekla` 为公开仓库；此前自动审批拒绝后，用户明确回复“推送”，已批准此次公开发布。数据与 Excel 未进 Git。
