# H 钢弧形梁零件侧面修正验证

日期：2026-06-26

## 背景

用户复核 `T3-7GL-126` 时指出：`T3-L-301` 与 `T3-P-3226` 肉眼明显位于腹板两侧，但旧算法可能把它们判到同侧。

## 根因

1. 新导出的 H 钢主材名称为 `GL4015-1`，不再包含 `上翼缘/下翼缘/腹板` 中文名；旧分类器只靠名称找主材，无法稳定建立 H 钢截面框架。
2. 弧形梁腹板的 `sectionProjectionEvidence.projectedBounds` 是整件沿轴线扫掠后的投影范围，不能把 `web_min_u..web_max_u` 当作真实腹板厚度。旧算法把扫掠宽度当腹板半厚度，导致腹板左右侧被吞进不可分类区或误判。
3. 同一 `partPosition` 在构件内可能有多个 Tekla 实体实例；输出侧面时必须保留 `partId`，不能只按零件编号聚合成单行。

## 修正

- `classify_h_beam_part_sides(assembly, member)` 支持从 `member.Classification.PartRoles` 获取 H 钢主材：
  - `flange_candidate` 依据截面 V 方向高低区分上/下翼缘。
  - `wall_candidate` / `web_candidate` 作为腹板。
- 腹板左右分界仍使用截面 U 方向，但腹板半厚度优先来自 `thickness` / `profileString` 的板厚证据，不再使用弧形梁整件扫掠包络宽度。
- offline pipeline 已改为传入 `member`，使离线报告能消费 `PartRoles`。

## 回归测试

命令：

```powershell
python -m unittest tests.test_h_beam_part_sides tests.test_reports_offline tests.test_pipeline_offline
```

结果：

```text
Ran 8 tests in 0.830s
OK
```

备注：测试过程中存在既有 `openpyxl datetime.utcnow()` DeprecationWarning，不影响本次断言。

## 真实导出 smoke

数据：`I:\zijinhuatekla\cache\20260626_100404`

命令摘要：直接加载 `tekla-body-bracket-export.bundle.json` 与 `members/member_T3-7GL-126.json`，调用 `classify_h_beam_part_sides(assembly, member)`。

目标零件实例结果：

| partPosition | partId | side | confidence | 说明 |
| --- | --- | --- | ---: | --- |
| T3-P-3226 | 71485426 | WEB_RIGHT | 1.000 | 腹板右侧 |
| T3-P-3226 | 71485811 | WEB_RIGHT | 0.800 | 腹板右侧，局部轮廓有少量跨界投票 |
| T3-L-301 | 71603918 | WEB_RIGHT | 0.550 | 腹板右侧，低置信度 |
| T3-L-301 | 71604726 | WEB_LEFT | 0.600 | 腹板左侧 |
| T3-P-4309 | 71485508/71485532/71485892/71485916 | TOP_FLANGE_OUTER | 0.714 | 上翼缘上侧 |
| T3-P-4230 | 71485442/71485827 | TOP_FLANGE_OUTER | 1.000 | 上翼缘上侧 |
| CP-1 | 71485516/71485524/71485900/71485908 | TOP_FLANGE_OUTER | 1.000 | 上翼缘上侧 |
| T3-L-279 | 71603848 | WEB_RIGHT | 0.550 | 腹板右侧，低置信度 |
| T3-L-279 | 71604657 | WEB_LEFT | 0.550 | 腹板左侧，低置信度 |
| T3-P-1715 | 多个实例 | WEB_RIGHT 为主，71485948 为 WEB_LEFT | 0.667-1.000 | 同编号多实例分布在不同 station/侧面 |

## 仍需注意

当前导出没有提供 H 钢 station-local section loops，因此本次修正仍基于投影点、板厚和 PartRoles。对弧形梁更严谨的最终口径，应让导出器补充 H 钢局部 station 截面 loop / 局部腹板中心线证据。
