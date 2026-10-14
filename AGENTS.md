# Zijinhua Tekla Agent Notes

本项目用于沉淀 Tekla 深化模型识别、加工工序判断、零件角色关系和配送口径。

## 工作约定

- `STATUS.md` 记录当前阶段、最新进展、风险和下一步。
- `TASKLIST.md` 记录可执行任务队列。
- 业务设计、验收和验证方案写入 `docs/design/`。
- 验证记录写入 `docs/verification/`，聊天只汇报结论和关键路径。
- `src/zijinhua_tekla/` 放可复用识别代码；`tests/` 放对应单元测试。
- 不把一次性分析脚本直接当生产逻辑；先抽出规则，再接入导出数据或 Tekla MCP。
- 不默认调用 superpowers，只有用户明确要求时才调用。
- 文档沿用 `STATUS.md + TASKLIST.md`；旧状态和已完成任务归档到 `docs/verification/`，不另建第二套活文档。

## 当前重点

2026-10-14：主目录 `I:\zijinhuatekla` 已切换为 `codex/offline-part-drawing-engine`，当前工作是平板零件离线出图。

- 最小读取集：`STATUS.md`、`TASKLIST.md`、`docs/design/2026-07-13-part-drawing-offline-architecture.md`；几何证据问题再读 `docs/design/2026-07-14-part-drawing-v2-geometry-evidence-and-annotations.md`。
- 正式入口：CLI `draw-parts` → `part_drawing.pipeline.run_part_drawing_batch`；消费 `partDrawingSnapshot.v1/v2`，输出 DXF、PDF 和 drawing JSON。
- 先稳定平板零件图，再扩展构件工序图。折弯板、曲面板和型材仍由质量门阻断自动出图；`OK` 不等于生产放行。
- 识别主线保留在 `feat/recognition-mainline`（已验收基线 `635cdd9`），不把该分支代码或旧 main 混入出图工作。
- 本地 `main` 保留旧出图基线 `7a9fb37`，不是当前开发入口；未经明确要求不移动或推送 main。
- 旧目录 `I:\tmp\zijinhuatekla-part-drawing-engine` 保留为 detached HEAD `7a9fb37` 历史现场；继续开发使用主目录，不重复检出同一分支。
- 不删除或搬动根目录 CAD/Excel、cache、outputs、dist；它们是忽略的本地资料，不代表待提交文件。

## Git 与文档收尾

- 改动前核对 `git status --short --branch` 和 `git worktree list`。仅暂存本次明确文件，不把本地资料全量加入索引。
- 提交标题使用 `<type>: <summary>`；默认由全局 Stop hook 收尾，用户明确要求提交/推送时可在会话中执行并核验。
- 推送后核对当前 HEAD 与远端分支 SHA，以及 ahead/behind；工作区干净不代表已有提交已推送。
- 全局 `check-docs.ps1` 对本项目返回豁免，不构成内容审核通过。收尾必须核对 README 与实际契约/入口一致、STATUS 只写现状与验证、TASKLIST 只保留当前未完成任务、引用存在。
- 文档/忽略规则整理运行 `git diff --check` 和引用检查；代码变更运行相关测试，发布出图基线前运行 `python -m unittest discover -s tests`。测试时确认导入来自当前 `src`。
- 每轮验证写入 `docs/verification/`，区分本轮实测与历史验收；STATUS 下一步不超过三条。共享全局 hook 配置不随本项目文档整理修改。

## 防规则堆砌规则

新增或修正识别逻辑时，禁止直接围绕单个构件号、零件号、项目名写死规则。

## 编号与拆板硬约束

- Excel 清单来自 Tekla 模型导出时，普通零件编号必须与 Tekla `partPosition` 精准一致。
- 不允许用几何相似、规格相似、长度相近自动替代编号匹配；这类结果只能进入候选复核报告。
- 拆板/派生加工件不是编号漂移，必须走独立的制造口径映射，例如 `*-H-xxx[s/x/f]` 可证明来自 `*-H-xxx` 的 BH 型钢母件。
- 拆板映射必须有母件名、母件 profile、后缀语义、厚度/宽度/长度证据；否则进入 Data Quality Gate。
- 制造整板与 Tekla 分段模型差异必须归入 `MANUFACTURING_MODEL_SCOPE_MISMATCH` 复核候选；不得把候选段当作自动编号匹配成功。
- 报告字段里如果出现几何候选，只表示复核证据，不表示自动匹配、自动改号或确认编号漂移。

每个失败案例必须先归因：

- 数据问题：模型缺件、Excel 错号、编号漂移、制造口径与建模口径不一致。
- 特征缺失：导出数据没有支撑判断所需的几何、孔、切割、焊接、空间关系。
- 评分问题：已有特征足够，但权重、阈值或证据优先级不合理。
- 新类型：现有类别体系表达不了真实工程角色或工艺。

对应处理方式：

- 数据问题进入 Data Quality Gate，不允许用分类规则硬凑命中。
- 特征缺失先补 Feature Snapshot / 导出器字段，再写分类逻辑。
- 评分问题调整可解释评分或策略，并加入回归案例。
- 新类型必须补类别定义、验收样例和测试，不允许只加一个特例分支。

任何规则变更都必须同时留下：

- 失败案例或最小复现数据。
- 期望标签或人工确认口径。
- 证据字段说明。
- 回归测试或验证记录。

优先改“特征层、评分层、案例反馈层”，避免在业务判断里堆叠零散 `if/else`。
