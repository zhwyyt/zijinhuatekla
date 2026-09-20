# 2026-09-18 剖口导出与识别

对象：当前 Tekla 选择集 `T3-5GKZ-8` + `T3-7GKL-6`  
Dump：`I:\xingcaisuanfa\cache\20260918_edge_bevels_v3`  
识别 Excel：`outputs/model-first-edge-bevel-t3-5gkz-8`、`outputs/model-first-edge-bevel-t3-7gkl-6`

## 导出器

- schema `tekla-body-bracket-export.v2-section-bevels`（此前 `v2-edge-bevels`）
- 新增 `edgeBevels` / `edgeBevelCount` / `hasEdgeBevel`
- 来源：`EdgeChamfer`、`BOOLEAN_WELDPREP`、相对板厚倾斜的 `Fitting`/`CutPlane`、沿板边的厚度向 `BOOLEAN_CUT` 楔体
- 轮廓 `ContourPoint.Chamfer` 仍是倒角，不进剖口
- `GetBooleans()` 在 Tekla 2017 只返回 `BooleanPart`；补了 `GetChildren` 和按 Father 索引的 `EDGE_CHAMFER`/`FITTING`/`CUTPLANE`
- 剖口布尔不再计入 `holeLikeFeatureCount`

## 本选择集事实

- 模型里没有 `EdgeChamfer` 对象
- `Fitting`/`CutPlane` 共 17 条，与板法向夹角约 86–90°，判定为直角切割，不是剖口
- 剖口 10 条，全部是沿板边的 `BOOLEAN_CUT` 楔体（约 `t × t × 边长`）
  - `T3-5GKZ-8` 主壁板 `T3-P-5589/5604/5606/5605`：18×18×1100
  - `T3-7GKL-6` `T3-PX-229`：14×14×1150

## 识别

- 证据出现 `板边剖口`
- `T3-PX-229` 外轮廓仍是标准矩形；因螺栓孔记为异形，不是因为剖口
- 主壁板无轮廓点，形状仍为 `UNKNOWN`/`异形主材`（缺 Feature，不是剖口误伤）
- 单元测试：矩形 + 剖口 → 方块；平面倒角仍为异形

## T3-H-574 漏识别（已修规则，待重导）

`T3-H-574` 是轧制 `BH950*400*16*30`，不是板。两端各有：

- 上下翼缘剖口楔体约 `83×90×700`（相对 tf=30）
- 端部腹板坡口切割盒约 `110×700×880`
- 跨中腹板开孔 `300×200×300`，不是剖口
- 两端 Fitting 法向约 90°，是直角切头，不是剖口

漏判原因：导出器把梁的 `thickness=400`（翼缘宽度）拿去当板厚，楔体长边门槛变成 3200mm，翼缘剖口 700mm 全部落空。

已改为用规格里的 tw/tf（16/30）判定板件楔体，并用梁端 + 沿梁向浅切判定型钢端剖口。跨中开孔仍排除。

2026-09-18 重导 `cache/20260918_t3h574_bevel`：`hasEdgeBevel=true`，`edgeBevelCount=6`（两端翼缘楔体 4 + 端腹板盒 2）；两端 Fitting 仍为直角切头；跨中 4 孔未计入剖口。识别 Excel 证据含「板边剖口」，工序仍为「不下」。

## 型材剖口/倒角/洞口（2026-09-18）

导出器 `0.3.1-section-bevels`：壁厚候选不再只认 H。C/L/T/U/PIPE/CHS/RHS/SHS/D 等用规格数字里 2–80mm 的壁/翼缘厚；四段规格取第 3、4 个数。板边楔体最短边必须是 O(t)，避免梁上 BOOLEAN_CUT 的 AABB 误记到邻板。型材端部、非剖口的 BOOLEAN_CUT 记 `endChamferCount`。

识别：

- 型材工序仍为不下/成品槽/挂钩，不改成下料。
- 证据：剖口=`板边剖口`，倒角=`倒角`，洞口=`洞口`（螺栓孔或去掉剖口/端部倒角后的剩余切割）。
- 板件大 LINE 倒角（如 350×30）记「平面倒角」。梯形无 Chamfer 规格仍不是倒角。
- 连接板上 AABB 远大于零件的 BOOLEAN_CUT 不当剖口。

仍缺：Beam 建模 PL 无轮廓，倒角/方块无法证明；8 边台阶板是缺口不是倒角；型材倒角依赖端部 BOOLEAN_CUT，45° Fitting 斜切还可能进剖口。需要新 dump 才能验证 C/L/管的剖口几何。

## 零件板剖口/倒角/洞口（2026-09-18）

对象仍是 `cache/20260918_edge_bevels_v3`（255 块板：ContourPlate 74 / Beam 176 / PolyBeam 5）。识别不依赖新 dump；导出器 `0.3.2-plate-face` 给后续 Beam 板补板面四角。

规则：

- 剖口：厚度向楔体 / EdgeChamfer / 倾斜 Fitting，不否定方块。
- 倒角：平面轮廓切角，或无轮廓 Beam 板的角部 BOOLEAN_CUT。否定方块。
- 洞口：螺栓孔或板内贯穿切割。否定方块，工序下料割孔。
- 邻件 AABB 切到本板、体积主要在板外：外来切割，既不当剖口也不当洞口。
- 共线毛刺顶点按点到边距离清掉，不把 0.1mm 五边形当异形。
- 台阶/缺口仍是异形；若同时有正尺寸 ARC/ROUNDING，证据并列「平面缺口」+「平面倒角」。
- 梯形/平行四边形不是倒角。PolyBeam 不重建矩形。

现有 dump 核对（0 条方块夹带倒角/洞口/缺口；0 条 Beam 板 UNKNOWN）：

| 口径 | 零件 | 结果 |
| --- | --- | --- |
| 无轮廓矩形 Beam 板 | `T3-P-4462` | 下料 / 方块 |
| 邻梁 BOOLEAN_CUT + LINE 倒角 | `T3-P-4427` | 下料 / 异形 / 平面倒角（外来切割不进洞口） |
| 板边楔体剖口 + 螺栓 | `T3-PX-229` | 下料割孔 / 异形 / 板边剖口+洞口 |
| 矩形内孔 | `T3-P-5643` | 下料割孔 / 异形 / 洞口 |
| 无轮廓主壁板剖口+螺栓 | `T3-P-5589` | 下料割孔 / 异形 / 板边剖口+洞口 |
| 角部切割盒 | `T3-P-6112` | 下料 / 异形 / 平面倒角（不是洞口） |
| 板内贯穿棒 | `T3-P-5606` 剩余切割、`T3-P-4891` | 洞口 |
| 8 边台阶 + ROUNDING | `T3-P-5390` | 平面缺口+平面倒角+洞口 |
| 12 边零尺寸 ARC_POINT | `T3-DR-6` | 平面缺口，无倒角 |
| 0.1mm 共线第五点 | `T3-P-4125/4124` | 方块 |
| 梯形/斜四边 | `T3-P-4549/4886` | 异形，无倒角 |

单元测试 `187 OK`。C# Runner 0 error / 16 既有 nullable warning。新 dump 才会带 Beam `contourPoints`；当前识别已用 OBB 去厚重建。
