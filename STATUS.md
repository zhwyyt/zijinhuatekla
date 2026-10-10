# STATUS

## 当前阶段

2026-10-10：分支 `feat/recognition-mainline`。识别主线集成已收敛，已完成真实 Tekla 当前选择集重新导出与新旧对比；发现并修复同号装配实例快照串用。已验收实验算法保持不变，新增现场复核项单列，不冒充全量人工验收。

## 已完成

- 正式 CLI / GUI 共用角色、复杂度、零件特征三表；算法集成基线 `0701e89` 已推送。
- 最新导出 979 装配，最终报告 979 / 979 / 7086 行、16998 件、0 运行失败；分组跨度主轴 978 个有效来源一致，1 个几何轴回退需复核。
- 新旧共同 264 个装配，新增选择 715、旧包本次未选 25；57 个角色由未知变为梁/柱，104 个复杂度结果变化。
- 实例解析改为按装配 ID 读完整 batch，327 个快照串用消除，纠正 2 个姿态和 3 个牛腿统计；274 tests OK。
- 历史现场见 [收敛前记录](docs/verification/2026-10-10-pre-mainline-memory.md)，初次集成见 [主线验证](docs/verification/2026-10-10-recognition-mainline.md)。

## 版本与边界

- 主轴：`AlignedSpanMemberAxis`，source=`assemblyParts.alignedSpanCentroid`；`I:\xingcaisuanfa` 已保存源码基线 `feat/accepted-recognition-axis` / `71a95bb`，Runner 构建 0 警告、0 错误。
- 最新数据：`cache/selected-mainline-20261010-105609`；最终 Excel 和对比以 `outputs/selected-mainline-20261010-105609/corrected/` 为准。父目录首次报告仅保留失败证据。
- 零件出图留在 `I:\tmp\zijinhuatekla-part-drawing-engine`、`codex/offline-part-drawing-engine`，本轮不修改。
- 本地 `main` 仍在旧出图历史上，不是当前识别基线；先推送收尾分支，不直接改写 main。

## 下一步

复核 6 个主材类型变化（含 4 个 BOX → UNKNOWN）及 1 个零长度主轴；不按编号硬补类型，不回退已验收主轴。621 个未知角色保留规则的不足/冲突，不等于运行错误。零件出图继续独立开发。

## 最新 Handoff

[选择集重新导出与对比记录](docs/verification/2026-10-10-selected-mainline-reexport-comparison.md) 包含范围、最终成果、实例修复、274 项回归和待复核案例。下一步优先查主材分段/特征消费与新长轴的关系，再按现场证据确定策略；本轮没有确认这些新增现场标签全部人工验收。
