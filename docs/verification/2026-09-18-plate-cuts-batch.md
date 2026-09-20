# 2026-09-18 大批量选择集导出与识别

Tekla 当前选择集整跑：先 dump，再模型→识别 Excel。

## Dump

- 目录：`I:\xingcaisuanfa\cache\20260918_plate_cuts_batch`
- 导出器：`xingcai-runner-body-bracket-0.3.2-plate-face`
- schema：`tekla-body-bracket-export.v2-plate-face`
- assembly：979
- 不重复构件号 JSON：652（同号 `member_*.json` 会被覆盖）
- bundle：`tekla-body-bracket-export.bundle.json`（约 348MB）
- 耗时约 3.4h。慢点主要是每个 assembly 全模型扫描 EdgeChamfer / Fitting / CutPlane。

## 识别结果

- 总表：`outputs/model-first-plate-cuts-batch/recognition-all.xlsx`
- sidecar：`recognition-all.json`、`recognition-summary.json`
- 979 根全部跑完，失败 0。
- 零件行 7086。

| 项 | 值 |
| --- | --- |
| 方块 | 1636（全部工序=下料） |
| 异形 | 1498 |
| 异形主材 | 2571 |
| 形状空（型材，不参与方块/异形） | 1328 |
| UNKNOWN | 53 |
| 剖口=是 | 836 |
| 倒角=是 | 1622 |
| 洞口=是 | 2018 |
| 方块且倒角或洞口 | 0 |
| 方块且剖口 | 48 |

53 条 UNKNOWN 全是「同号零件分类不一致」（同一 `partPosition` 在同一装配里形状/角色不唯一），不是导出失败。
