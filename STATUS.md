# STATUS

## 当前阶段

2026-10-10：分支 `feat/recognition-mainline`。主材识别已适配新主轴下的局部截面证据，完整 BOX/H 证据不再被旧长度/整轴占比门槛否决。已验收主轴不变；新增主材及派生标记待人工确认。

## 已完成

- 正式 CLI / GUI 共用角色、复杂度、零件特征三表；算法集成基线 `0701e89` 已推送。
- 最新报告 979 / 979 / 7086 行、16998 件、0 运行失败；293 tests OK。32 个新旧 GKZ 实例牛腿数量及单元身份保持一致。
- 相对 `2750c1c` 交付，4 个 GKZ 从 UNKNOWN 恢复 BOX，4 个梁由局部三板证据确认 H 钢；角色全表、牛腿统计及加工字段不变。主材标记新增 74 行，关联说明/形状/BOX 内外关系变动已落盘。
- 此前已消除 327 个同号实例快照串用；新旧选择范围共同 264、新增 715、未选 25。
- 历史现场见 [收敛前记录](docs/verification/2026-10-10-pre-mainline-memory.md)，初次集成见 [主线验证](docs/verification/2026-10-10-recognition-mainline.md)。

## 版本与边界

- 主轴：`AlignedSpanMemberAxis`，source=`assemblyParts.alignedSpanCentroid`；`I:\xingcaisuanfa` 已保存源码基线 `feat/accepted-recognition-axis` / `71a95bb`，Runner 构建 0 警告、0 错误。
- 最新数据：`cache/selected-mainline-20261010-105609`；最终 Excel 为 `outputs/main-material-axis-20261010/delivery/徐汇T3_当前选择集.xlsx`。本轮复用缓存，未再导出 Tekla；`gkz-fixed/` 保留为本轮对比基线。
- 完整局部证据路径优先；缺证据兼容路径仍有历史阈值，不宣称全部旧门槛已清除。
- 零件出图留在 `I:\tmp\zijinhuatekla-part-drawing-engine`、`codex/offline-part-drawing-engine`，本轮不修改。
- 本地 `main` 仍在旧出图历史上，不是当前识别基线；先推送收尾分支，不直接改写 main。

## 下一步

新发现：T3-P-2219 的含孔加工分类被误写成外轮廓非矩形，且“平板无孔”描述过宽；已完成 [证据血缘调查](docs/verification/2026-10-10-part-evidence-contradiction.md)，本轮未改业务分类。

人工复核本轮 8 个主材类型变化及主材/派生零件标记；4 个 GKZ UNKNOWN 的算法问题已解决。另有 1 个零长度主轴待查；621 个未知角色保留证据不足/冲突。零件出图继续独立开发。

## 最新 Handoff

[局部截面主材验证](docs/verification/2026-10-10-local-section-main-material.md) 包含阈值适用边界、8 个类型变化、293 项测试、32/32 牛腿身份回归及抽象复盘。新增结果尚未人工验收；此前导出与实例修复见 [选择集记录](docs/verification/2026-10-10-selected-mainline-reexport-comparison.md)。

本轮之前已推送基线为 `2750c1c`。远端 `zhwyyt/zijinhuatekla` 为公开仓库，用户已明确授权推送；数据与 Excel 不进 Git。
