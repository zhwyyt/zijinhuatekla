# STATUS

## 当前阶段

2026-10-12：分支 `feat/recognition-mainline`。用户确认 Qt6 界面及 exe 打包相关源码已验证无问题，桌面交付验收完成。主材识别已适配新主轴局部截面证据；新增业务标签的人工复核边界仍按原记录保留。

## 已完成

- 正式 CLI / GUI 共用角色、复杂度、零件特征三表；算法集成基线 `0701e89` 已推送。
- Qt6 两模块支持指定输入/输出目录、后台执行、实时日志和错误提示；修复打包 ICU DLL 冲突，302 tests OK，实际 exe 启动验证通过，用户已确认验收。
- 最新报告 979 / 979 / 7086 行、16998 件、0 运行失败；293 tests OK。32 个新旧 GKZ 实例牛腿数量及单元身份保持一致。
- 相对 `2750c1c` 交付，4 个 GKZ 从 UNKNOWN 恢复 BOX，4 个梁由局部三板证据确认 H 钢；角色全表、牛腿统计及加工字段不变。主材标记新增 74 行，关联说明/形状/BOX 内外关系变动已落盘。
- 此前已消除 327 个同号实例快照串用；新旧选择范围共同 264、新增 715、未选 25。
- 历史现场见 [收敛前记录](docs/verification/2026-10-10-pre-mainline-memory.md)，初次集成见 [主线验证](docs/verification/2026-10-10-recognition-mainline.md)。

## 版本与边界

- 主轴：`AlignedSpanMemberAxis`，source=`assemblyParts.alignedSpanCentroid`；`I:\xingcaisuanfa` 已保存源码基线 `feat/accepted-recognition-axis` / `71a95bb`，Runner 构建 0 警告、0 错误。
- 桌面程序：`dist/ZijinhuaTekla/ZijinhuaTekla.exe`，Qt 6.11.2，Windows 10/11 64 位；模块1依赖本机 Tekla 2017/.NET 4.8。exe 和真实数据不进 Git。
- 最新数据：`cache/selected-mainline-20261010-105609`；最终 Excel 为 `outputs/main-material-axis-20261010/delivery/徐汇T3_当前选择集.xlsx`。本轮复用缓存，未再导出 Tekla；`gkz-fixed/` 保留为本轮对比基线。
- 完整局部证据路径优先；缺证据兼容路径仍有历史阈值，不宣称全部旧门槛已清除。
- 零件出图留在 `I:\tmp\zijinhuatekla-part-drawing-engine`、`codex/offline-part-drawing-engine`，本轮不修改。
- 本地 `main` 仍在旧出图历史上，不是当前识别基线；先推送收尾分支，不直接改写 main。

## 下一步

T3-P-2219 的证据来源已解释；用户确认沿用既有带孔矩形→异形/异形主材口径及证据，不列修复项，见 [口径确认](docs/verification/2026-10-10-part-evidence-contradiction.md)。

人工复核本轮 8 个主材类型变化及主材/派生零件标记；4 个 GKZ UNKNOWN 的算法问题已解决。另有 1 个零长度主轴待查；621 个未知角色保留证据不足/冲突。零件出图继续独立开发。

## 最新 Handoff

[Qt6 桌面验收](docs/verification/2026-10-12-qt6-desktop-acceptance.md) 保存用户确认、302 项测试、DLL 根因和发行校验值。业务算法边界仍见 [局部截面主材验证](docs/verification/2026-10-10-local-section-main-material.md)；桌面验收不替代逐零件标签复核。

桌面收尾前已推送基线为 `1853090`。远端 `zhwyyt/zijinhuatekla` 为公开仓库，用户已明确授权自动提交推送；本次将桌面源码、测试及文档一并保存。
