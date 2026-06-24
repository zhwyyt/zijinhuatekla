# Tekla AI Agent Architecture Skeleton

## 目标

先搭好 `I:\zijinhuatekla` 的工程架构骨架，让后续主材、牛腿、零件角色、工序、配送、组立顺序都沿稳定边界演进，而不是继续把规则散落在 CLI 或单个脚本里。

## 架构层级

代码层级定义在 `src/zijinhua_tekla/architecture.py`。

1. `adapters`
   - 读取 Tekla bundle、member JSON、Excel、teklatest、未来 MCP/plugin 数据。
   - 只做来源适配，不做业务分类。
2. `quality`
   - Data Quality Gate。
   - 处理缺件、同名冲突、编号漂移、制造口径和建模口径差异。
3. `features`
   - Feature Snapshot。
   - 把几何、孔、切割、焊缝、尺寸、轮廓等变成事实字段。
4. `spatial`
   - 空间/关系层。
   - 负责附属件簇、root contact、overhang、端部信号、焊接/螺栓/接触关系证据。
5. `classifiers`
   - 分类器接口。
   - 主材、零件角色、牛腿、工序、形状分类必须输出 label、confidence、evidence。
6. `cases`
   - Case Bank。
   - 人工确认、失败归因、期望标签和回归样例。
7. `pipeline`
   - 流水线编排。
   - 统一串联 adapter -> quality -> features -> spatial -> classifiers -> reports。
8. `reports`
   - 报告输出。
   - CSV、JSON、Markdown、未来图纸标注和组立顺序图。

## 当前代码落点

- `architecture.py`
  - 架构层级清单和责任说明。
- `quality/gate.py`
  - 第一版 Data Quality Gate 报告对象：`DataQualityReport`、`DataQualityIssue`。
- `pipeline/offline.py`
  - 第一版离线流水线结果对象：`OfflinePipelineResult`。
- 既有模块暂时保留：
  - `features.py`
  - `spatial_features.py`
  - `member_classifier.py`
  - `part_roles.py`
  - `bracket_classifier.py`
  - `casebank.py`
  - `rules.py`
  - `cli.py`

后续迁移时优先保持兼容，不一次性大搬目录，避免破坏已经验证过的 T3 对齐结果。

## 变更规则

- 新数据源先进入 `adapters`。
- 数据问题先进入 `quality`，不允许靠分类器硬凑。
- 缺字段先补 `features` 或导出器。
- 空间关系先进入 `spatial`，不塞进角色规则。
- 分类器只能消费事实特征和证据，输出 label/confidence/evidence。
- 人工反馈必须进入 `cases`，并产生回归验证。

## 验收标准

- 架构层级可由测试固定顺序和责任。
- Data Quality Gate 能从 aligned rows 产出缺件/冲突问题。
- 离线流水线结果能统一携带 member、assembly、aligned rows、quality report。
- 原 T3-5GKZ-10 对齐结果不退化。

## 验证计划

```powershell
python -m unittest tests.test_architecture_skeleton
python -m unittest discover -s tests
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\algorithm-extraction-smoke-20260617
```
