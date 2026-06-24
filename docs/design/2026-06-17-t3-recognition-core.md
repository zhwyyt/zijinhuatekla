# T3 Recognition Core Design

## 目标

把本次 T3-5GKZ-10 分析中已经确认的业务口径，沉淀为 `I:\zijinhuatekla` 项目的第一版可运行识别核心。第一版先做离线 JSON/Excel 对齐，不绑定 Tekla MCP 或插件直连。

## 范围

- 输入：Tekla 导出的 `tekla-body-bracket-export.bundle.json`、`members/member_<构件>.json`，以及真实加工 Excel。
- 输出：对齐 CSV、JSON、Markdown 报告。
- 规则：BH 型钢拆板派生、ContourPlate 名义加工尺寸、同名冲突保留。

## 非范围

- 不在本阶段自动改 Tekla 模型。
- 不在本阶段自动生成图纸标注。
- 不把所有工序规则一次性做成 100% 完整，只迁入已经验证过的核心几何口径。

## 核心设计

`zijinhua_tekla.rules` 只负责纯规则：

- `norm_spec`：统一规格字符串。
- `parse_pl`：解析 `PL厚*宽`。
- `part_length_approx` / `part_width_approx`：计算零件加工口径尺寸。
- `row_part_score`：判断 Excel 行和 Tekla 零件是否规格、长度匹配。
- `is_derived_h_profile_plate`：判断 `T3-H-xxx[s/x/f]` 是否由 BH 型钢拆板派生。

`zijinhua_tekla.alignment` 负责数据对齐：

- 读取 Excel 指定构件行。
- 读取 Tekla bundle 指定 assembly。
- 先按 `partPosition` 找同名；同名但规格/长度冲突时标 `partPositionConflict`。
- 找不到同名时尝试 BH 派生、规格长度候选、宽松几何候选。
- 输出每行的匹配方式、候选证据和预测状态。

## 验收标准

- 单元测试覆盖 BH 拆板派生和 ContourPlate 轮廓边长尺寸。
- 对 `T3-H-558s/x/f` 输出 `derivedFromProfilePart`。
- 对 `T3-P-4869`、`T3-P-4885` 不再因为 OBB 尺寸偏大产生同名冲突。
- 能针对 T3-5GKZ-10 生成 CSV、JSON、Markdown 三类结果。
- ContourPlate 尺寸匹配必须使用成对候选，不能把同一条边同时当作长度和宽度。

## 验证计划

- `python -m unittest discover -s tests`
- `python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs`

## 首轮验证结论

2026-06-17 已完成首轮验证：62 行中 `MATCH=55`、`MATCH_CONFLICT=4`、`DATA_MISSING=3`。详见 `docs/verification/2026-06-17-t3-recognition-core.md`。
