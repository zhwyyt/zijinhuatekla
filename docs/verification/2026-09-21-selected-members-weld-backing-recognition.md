# 2026-09-21 Tekla 当前选择集识别

## 输入

- 导出：`I:\xingcaisuanfa\cache\20260920_weld_backing_shop_process`
- 导出器：`xingcai-runner-body-bracket-0.3.3-index-once`
- schema：`tekla-body-bracket-export.v2-plate-face`
- 选择集：289 装配 / 271 不重复构件号（T3-6GL 232、T3-6GKL 16、T3-5GKZ 16、T3-4HXZ 13、T3-4HXL 8、T3-4HMS 4）
- 识别脚本：`outputs/model-first-weld-backing-selection/run_batch_recognition.py`

## 输出

- `outputs/model-first-weld-backing-selection/recognition-all.xlsx`
- `outputs/model-first-weld-backing-selection/recognition-all.json`
- `outputs/model-first-weld-backing-selection/recognition-summary.json`
- `outputs/model-first-weld-backing-selection/recognition-errors.json`

识别 289/289，零件行 4044，失败 0。耗时约 1701s。

## 工序

`process_不下 = 0`，没有任何工序文本含「不下」。

| 工序 | 行数 |
| --- | --- |
| 工序1：下料 | 2167 |
| 工序1：下料；工序2：下料钻孔 | 845 |
| 工序1：下料割孔；工序2：下料钻孔 | 252 |
| 工序1：下料；工序2：下料折弯 | 149 |
| 工序2：下料钻孔 | 82 |
| 工序1：下料割孔 | 70 |
| 工序1：下料；工序2：下料折弯+下料钻孔 | 54 |
| 工序1：下料割孔；工序2：下料折弯 | 40 |
| 工序1：下料割孔；工序2：下料折弯+下料钻孔 | 6 |
| 空（角钢/圆杆/槽钢/套筒等非板） | 342 |
| UNKNOWN（同号分类不一致） | 37 |

空工序来自 L/D/C/BH/套筒，不是推断「不下」。

## 焊接垫板

Excel `角色=焊接垫板`：38 行，33 个构件，全部是 T3-6GL。规格以 `PL6*30` 为主，另有 `PL12*44`×3、`PL10*34`×1。证据均为窄长几何 + Weld/Contact/焊缝几何，不读名称。其中 4 行零件名称不含「衬垫/垫板」，仍因接缝接触命中。

对照（名称只作复核，不参与分类）：

| 口径 | 数量 |
| --- | --- |
| 名称含衬垫/垫板/衬条 的 (装配,零件号) | 127 |
| 分类器 `classify_weld_backing_plates` 命中 (装配,零件号) | 141（零件实体 294） |
| Excel 角色=焊接垫板 | 38 |
| 分类器命中且 Excel 也是焊接垫板 | 38 |
| 分类器命中但 Excel 被写成主壁板/板件/UNKNOWN | 103 |

103 条漏到 Excel 角色的原因是评分顺序：`infer_role` 先看 `MAIN_WALL` / `main_material_role`，后看 `weld_backing`。T3-6GKL/T3-5GKZ/T3-4HXZ 上窄条垫板已被截面主材算法标成主壁板或组合截面主板，Excel 证据只剩「截面主壁板」或「组合截面主板」，垫板证据被盖掉。这是评分问题，不是缺 Weld/Contact。

分类器按构件系列命中：(T3-6GL 51, T3-5GKZ 42, T3-6GKL 33, T3-4HXZ 11, T3-4HXL 4)。

## 其他

- 剖口=是 480，倒角=是 1086，洞口=是 1286。
- 方块且倒角或洞口：7 行，待形状分类复核。
