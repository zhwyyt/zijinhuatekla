# 2026-09-21 BOOLEAN_CUT 固体切割证明

失败案例：`T3-6GKL-4` / `T3-PX-187` (`partId=70797915`)。模型无剖口；旧 dump 把邻居 `BOOLEAN_CUT`（1052×30×30）挂到该板，Excel 剖口=是。

期望：只有 Tekla 确认切掉了该零件未切割实体的 BOOLEAN_CUT 才进剖口/洞口/倒角；切不到的一律否。

## 证据

Tekla 2017 没有 CSG 体积。百分百口径：

1. `Part.GetSolid(SolidCreationTypeEnum.RAW)` 取未切割父体。
2. `fatherRaw.GetCutPart(cutter.GetSolid())` 返回带 Face 的 Shell → 切到了（`cutProof=GET_CUT_PART`）。
3. 固体 AABB 不相交 → 百分百没切到（`AABB_MISS`），不再调用 GetCutPart。
4. 空 Shell / 调用失败 / 固体不可用 → 不宣称切到（宁漏勿误报）。

导出器版本：`xingcai-runner-body-bracket-0.3.3-solid-cut-proof`。schema 仍是 `tekla-body-bracket-export.v2-plate-face`。未改截面采样、未改主材。

`booleanCutDetails` / `edgeBevels` 新增：

- `cutsFatherSolid`（bool，权威）
- `cutProof`：`GET_CUT_PART` / `AABB_MISS` / `NO_SHELL` / `GET_CUT_PART_FAILED` / `SOLID_UNAVAILABLE`

`BOOLEAN_CUT` 进 `edgeBevels` 必须先 `cutsFatherSolid=true`，再走原来的板边楔体判定。

Python：字段在则认 GetCutPart；缺字段才退回 AABB（不相交=否，相交仍不是固体证明）。GetCutPart=true 仍要过 `t×t×边` 才算剖口，长条切割不算剖口。

## 回归

- 导出器：`dotnet build I:\xingcaisuanfa\TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj -c Debug`，0 error。exe：`I:\xingcaisuanfa\TeklaSectionClassifier.Runner\bin\Debug\net48\TeklaSectionClassifier.Runner.exe`
- Python：`PYTHONPATH=src python -m unittest tests.test_plate_cuts tests.test_normalized_adapter tests.test_part_feature_excel tests.test_shop_geometry` → 48 tests OK。

旧 cache `20260920_weld_backing_shop_process` 无 `cutsFatherSolid`。AABB 已能否定 `T3-PX-187`（Z 向间隙约 190mm）。AABB 相交但未真切的案例必须用新 exe 重导后再出 Excel。

## 当前选择集实测 2026-09-21

Tekla 当时选择集只有 `T3-6GKL-4`（1 装配 / 45 零件实体 / Excel 19 行）。

- dump：`I:\xingcaisuanfa\cache\20260921_solid_cut_proof`
- Excel：`outputs/selection-solid-cut-proof/recognition-main-plus-features.xlsx`
- 导出器：`xingcai-runner-body-bracket-0.3.3-solid-cut-proof`
- 失败 0。构件类型 H，主材 `T3-H-471` 型钢。焊接垫板 `T3-P-4462` / `T3-P-345`。

`booleanCutDetails` 7 条：`GET_CUT_PART` 6、`AABB_MISS` 1。

| 零件 | 固体证明 | Excel 剖口 |
| --- | --- | --- |
| T3-PX-187 `70797915` | `cutsFatherSolid=false` `cutProof=AABB_MISS`，未进 edgeBevels | 否 |
| T3-PX-187 `70797667` | 无 BOOLEAN_CUT | 否（同号合并） |
| T3-H-471 | 2 条 BOOLEAN_CUT 楔体 `GET_CUT_PART` | 是 |

`T3-PX-187` 工序=UNKNOWN、洞口=是：同号两件合并，一件有螺栓孔证据，不是那条 AABB_MISS 切割被当成洞口。

## 固体切割证明优先

失败口径：20mm 板的邻居切割盒 30×30 曾被尺寸阈值卡死，导致工序 UNKNOWN；螺栓孔也曾被写成洞口。

期望：BOOLEAN_CUT 是否算剖口只由 Tekla `GetCutPart` 实体切割证明决定；没有证明时宁漏勿误报；洞口只认多出来的内孔。

- `edgeBevels` 中的 BOOLEAN_CUT 只认 `cutsFatherSolid=true`。
- `boolean_cut_count` 不计 `cutsFatherSolid=false` / AABB 不相交。
- 只有 `hole_like > bolt` 才写洞口；螺栓孔仍让矩形板进异形。

回归：`PYTHONPATH=src python -m unittest tests.test_plate_cuts tests.test_normalized_adapter tests.test_part_feature_excel tests.test_shop_geometry tests.test_algorithm_interfaces` → 63 tests OK。

重出表（原 xlsx 被占用）：`outputs/selection-solid-cut-proof/recognition-main-plus-features-relaxed.xlsx`。`T3-PX-187`：剖口=否、洞口=否、割孔=否、工序=下料+钻孔、数量=2。
