# STATUS

## 当前阶段

2026-10-10：识别主线收尾，分支 `feat/recognition-mainline`。范围为构件角色、构件复杂度、零件特征；用户已确认实验成果及分组跨度主轴人工验收通过，本轮做正式入口集成和项目状态收敛。

## 已完成 / 进行中

- 已保留实验成果和原有主材/零件特征算法，角色接入批量 Excel、单构件流水线及报告。
- 批量 CLI 与 GUI 共用三张主表；旧主轴、连接缺失和装配失败可定位复核。
- 原 STATUS/TASKLIST 已原样保存到 [收敛前现场](docs/verification/2026-10-10-pre-mainline-memory.md)。
- 自动回归 269 tests OK；289 构件历史 smoke 输出 289 角色 / 289 复杂度 / 4044 零件，0 识别失败。
- 验收与证据见 [主线验证](docs/verification/2026-10-10-recognition-mainline.md)，设计见 [主线设计](docs/design/2026-10-10-recognition-mainline.md)。

## 版本与边界

- 主轴：`AlignedSpanMemberAxis`，source=`assemblyParts.alignedSpanCentroid`；`I:\xingcaisuanfa` 已保存源码基线 `feat/accepted-recognition-axis` / `71a95bb`，Runner 构建 0 警告、0 错误。
- 已有本地导出 cache 均是旧主轴，不能冒充新主轴数据；新模型运行时需用当前 Runner 重新导出。
- 零件出图留在 `I:\tmp\zijinhuatekla-part-drawing-engine`、`codex/offline-part-drawing-engine`，本轮不修改。
- 本地 `main` 仍在旧出图历史上，不是当前识别基线；先推送收尾分支，不直接改写 main。

## 下一步

后续识别开发以 `feat/recognition-mainline` 为基线。真实 Tekla 重新导出更新数据属于后续现场阶段，不要求重做用户已确认的算法人工验收。零件出图继续独立开发。
