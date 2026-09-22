# 2026-09-21 主材原口径 + 零件特征另列出表

## 做法

主材分类器未改。Excel 按原先配送分叉写主材列：

- 构件类型用 member JSON：`MainClass=1/H/BH` → H，`2/BOX` → BOX。
- H：只认 `H_OR_BH_SECTION` 主板；若导出已是 `directHProfileSectionFrame.v1`，`mainPartId` 写「型钢」。不把 BOX/十字主壁板写进 H 构件。
- BOX：`MAIN_WALL` / 确认集写「BOX主壁板」，`INSIDE_BODY` 写 BOX 内。

剖口、倒角、割孔、洞口、工序、焊接垫板另列，不覆盖主材列。

## 输出

`outputs/selection-main-plus-features/recognition-main-plus-features.xlsx`

289 装配 / 4044 行 / 失败 0。工序「不下」=0。焊接垫板列 141（分类器命中数，不再被主壁板角色盖掉）。

## T3-6GKL-4

| 零件 | 规格 | 构件类型 | 主材 | 主材说明 | 焊接垫板 |
| --- | --- | --- | --- | --- | --- |
| T3-H-471 | BH950*400*16*30 | H | 是 | 型钢 | 否 |
| T3-P-4462 / T3-P-345 | PL6*30 | H | 否 |  | 是 |
| 连接板/马板等 | PL* | H | 否 |  | 否 |

16 根 `T3-6GKL-*` 全部是 H，主材各 1 根 BH 型钢。

## T3-PX-187 剖口误报

同号两件，其中 `70797915` 挂了一条 `BOOLEAN_CUT`（1052×30×30）。零件 AABB 在 z=30580–31070，切割盒子在 z=31258–31288，三维重叠为 0，洞口分类已标 `foreign`。剖口原先只看切割三条边是否像楔体，没问盒子有没有切到零件。已改为：BOOLEAN_CUT 必须与零件 AABB 三向相交，平板剖口还须约 `t×t×边长`。

`python -m unittest tests.test_part_feature_excel tests.test_emit_excel tests.test_weld_backing tests.test_normalized_adapter tests.test_plate_cuts`

后续固体证明见 `docs/verification/2026-09-21-solid-cut-proof.md`。AABB 已能否掉本例；AABB 相交时必须用 `0.3.3-solid-cut-proof` 重导。
