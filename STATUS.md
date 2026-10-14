# STATUS

更新时间：2026-10-14

## 当前阶段

主目录 `I:\zijinhuatekla` 已切换到 `codex/offline-part-drawing-engine`。当前基线为可人工复核的平板零件离线 DXF/PDF 出图，先稳定零件图，再扩展构件工序图。

## 已完成与版本边界

- CLI `draw-parts` 调用 `part_drawing.pipeline.run_part_drawing_batch`，消费 v1/v2 快照，共享图纸模型输出 DXF、PDF、drawing JSON 和质量摘要。
- 已有尺寸链规划、布局避让、原生 DIMENSION/MULTILEADER、孔中心线，以及双主面证据支持的坡口识别。
- 历史真实 v2 样件验证：12 条中心线、1 个孔组 MULTILEADER、9 个 DIMENSION、1 条 BEVEL，ezdxf audit 0/0。详见 [v2 验证](docs/verification/2026-07-14-part-drawing-v2-geometry-smoke.md)；本轮未重新连接 Tekla 或做 CAD 人工验收。
- 折弯板、曲面板、型材仍由 `PART_FORM_UNSUPPORTED_FOR_DRAWING` 阻断；无参数曲线不猜圆弧。缺孔、混合孔径、非正交孔阵仍需质量复核；`OK` 不代表生产放行。
- 识别主线保留在 `feat/recognition-mainline` / `635cdd9`。本地 main 保留旧出图基线 `7a9fb37`，不作当前入口；旧出图 worktree 保留为 detached 历史现场。

## 本次交接与验证

- 已归档原 STATUS/TASKLIST，更新 README、AGENTS 和本队列，补齐环境、凭据、CAD 锁文件及原本地资料的忽略规则；业务代码未改。
- 2026-10-14 在主目录确认导入本 checkout 的 src，完整 unittest 回归 **190 tests OK**。仅有既有 openpyxl deprecation warning。
- Git、文档引用和 CLI smoke 等本轮证据见 [整理验证](docs/verification/2026-10-14-drawing-workspace-cleanup.md)。全局文档脚本返回豁免，不计作内容审核。
- 旧现场和已完成任务保留在 [历史快照](docs/verification/2026-10-14-pre-drawing-cleanup-history.md)，不再作为当前待办；本地 CAD/Excel、cache、outputs、dist 保留。

## 下一步

1. 在目标 AutoCAD 打开现有 DXF，复核原生尺寸、孔组引出和坡口表达并记录验收。
2. 收集真实折弯、圆弧、切角和弧形切口样件，先补证据和验收口径，再决定扩展自动出图范围。
3. 按人工反馈确定孔阵/等距尺寸链扩展优先级；详细待办见 [TASKLIST](TASKLIST.md)。
