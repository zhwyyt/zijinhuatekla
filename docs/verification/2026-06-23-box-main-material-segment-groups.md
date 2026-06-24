# BOX Main Material Segment Groups Verification

## Scope

基于新导出的 Tekla cache `I:\xingcaisuanfa\cache\20260623_103323`，在 Python 侧建立 BOX 主材分段集合算法与离线报告输出。

本轮不改变普通零件编号精准匹配规则，不把几何相似或制造分段候选当作自动匹配成功。

## Implemented Boundary

- 新增 `src\zijinhua_tekla\classifiers\box_main_material_segments.py`。
- 核心证据来自 `part.mainMaterialEvidence`：
  - `bodyFaceId`
  - `axisStationStart/axisStationEnd`
  - `segmentAdjacency`
- 输出 `BOX_MAIN_MATERIAL_SEGMENT_GROUP` 候选，字段包含：
  - `face_id`
  - `part_ids`
  - `part_positions`
  - `station_ranges`
  - `gap_summary`
  - `continuity_level`
  - `evidence_codes`
  - `confidence`
  - `issue_category`
- 厚度、profile 只写入 `evidence_summary`，不作为强过滤条件。
- 同 `bodyFaceId` 内按 station 排序并切分 station run；单段候选保留为 `INSUFFICIENT_EVIDENCE`，不自动确认连续。
- offline report 新增：
  - `T3-5GKZ-10-box-main-material-segment-groups.json`
  - `T3-5GKZ-10-box-main-material-segment-groups.csv`

## New Cache Field Check

```powershell
$json = Get-Content -Raw -LiteralPath I:\xingcaisuanfa\cache\20260623_103323\tekla-body-bracket-export.bundle.json | ConvertFrom-Json
```

结果摘要：

- `metadata.memberAxisEvidence`：存在。
- assembly parts：259。
- parts with `mainMaterialEvidence`：259。
- `isBodyWallPlateCandidate=true`：247。

## TDD Coverage

新增 `tests\test_box_main_material_segments.py`，覆盖：

- 厚度不同但同 face + station 连续 + adjacency 相邻时仍归为同组。
- 不同 `bodyFaceId` 不归为同组。
- gap 过大时标记 `GAPPED`，不自动确认。
- 同 face 大断点切分 station runs，避免合成整面大桶。
- 单段候选保留为 `INSUFFICIENT_EVIDENCE`。
- 缺失 `mainMaterialEvidence` 标记为 `FEATURE/INSUFFICIENT_EVIDENCE`。

## Verification Commands

```powershell
python -m unittest tests.test_box_main_material_segments tests.test_reports_offline tests.test_pipeline_offline
```

结果：8 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m unittest discover -s tests
```

结果：56 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_103323 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\box-main-material-segments-smoke-20260623
```

## T3 Smoke Result

输出文件：

- `outputs\box-main-material-segments-smoke-20260623\T3-5GKZ-10-box-main-material-segment-groups.json`
- `outputs\box-main-material-segments-smoke-20260623\T3-5GKZ-10-box-main-material-segment-groups.csv`

结果摘要：

- segment group 候选数：181。
- 连续性分布：`CONTINUOUS=6`、`NEAR_CONTINUOUS=29`、`INSUFFICIENT_EVIDENCE=146`。
- 用户确认的 13 个主材分段编号中，新 cache 自动候选证据覆盖 13 个。
- 已确认：`T3-P-4914` 是误写成主材分段编号，已从人工确认集合移除；新 cache 对正确 13 个主材分段编号召回 `13/13`。

## Remaining Risk

- 当前 `bodyFaceId` 是径向 face bucket evidence，不是最终工程壁板面编号。
- `isBodyWallPlateCandidate=true` 的导出候选仍偏宽，包含耳板/夹板等，需要后续补更精细的主材面归属或 role evidence 来提升 precision。
- 单段候选只作为 `INSUFFICIENT_EVIDENCE` 保留，不进入自动组立/配送/出图结论。

## 2026-06-23 Topology Refinement

用户指出单纯按 face bucket 的算法偏粗，应结合焊接关系和主轴方向。本轮将算法调整为：

- `bodyFaceId` 仍作为防止全局装配关系泛滥的候选护栏，不作为最终工程壁板面强结论。
- 同一 `bodyFaceId` 内按主轴 station 排序。
- 只有同时满足 station 相邻/小重叠窗口和 Weld/Contact 关系的相邻零件才合为同一 segment group。
- 大 station 重叠的关系件不合组，避免夹板、耳板、横向附件把整根柱关系图串成巨大组件。
- 单段候选保留为 `INSUFFICIENT_EVIDENCE`，不自动确认。

新增测试覆盖：

- 同 face + station 邻近但无 Weld/Contact 不合组。
- 同 face + station 邻近 + Weld/Contact 合组。
- 跨 face 即使有关系，当前缺少更精细主材面证据时不合组。
- 大 station overlap 的关系件不合组。

验证：

```powershell
python -m unittest discover -s tests
```

结果：59 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

T3 smoke 仍使用：

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_103323 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\box-main-material-segments-smoke-20260623
```

拓扑修正后结果摘要：

- segment group 候选数：201。
- 连续性分布：`GAPPED=14`、`NEAR_CONTINUOUS=12`、`INSUFFICIENT_EVIDENCE=175`。
- 最大 group 零件数：4，已消除全局 Weld/Contact 图导致的 200+ 巨型组件。
- 人工确认的 13 个主材分段编号中，新 cache 候选证据覆盖 13 个。
- 已确认：`T3-P-4914` 是误写成主材分段编号，已从人工确认集合移除；新 cache 对正确 13 个主材分段编号召回 `13/13`。

Remaining Risk 更新：当前 precision 仍受 `isBodyWallPlateCandidate` 偏宽和 `bodyFaceId` 粗 bucket 限制。下一步应在导出器或特征层补更精细的主材面/零件角色证据，而不是继续堆规则。



## 2026-06-23 Human Confirmation Correction

用户确认修正：`T3-P-4914` 是误写成主材，不属于 T3-5GKZ-10 的主材分段集合。当前正确人工确认集合为 13 个：

- `T3-P-4916`
- `T3-P-4917`
- `T3-P-4919`
- `T3-P-6272`
- `T3-P-5577`
- `T3-P-6269`
- `T3-P-6268`
- `T3-P-5571`
- `T3-P-6284`
- `T3-P-6271`
- `T3-P-5579`
- `T3-P-5576`
- `T3-P-6270`

更新内容：

- `cases\seed.json` 已从 `box-column-main-material-segments` human note 中移除 `T3-P-4914`。
- `tests\test_casebank_persistence.py` 不再期待 `T3-P-4914` 属于主材分段集合。
- `tests\test_manufacturing_scope.py` 增加 `T3-P-4914` 不应获得 `confirmed_segment_positions` 标记的断言。

验证：

```powershell
python -m unittest tests.test_casebank_persistence tests.test_manufacturing_scope
```

结果：12 tests OK。

```powershell
python -m unittest discover -s tests
```

结果：59 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

T3 smoke 摘要保持：候选组 201 个，`GAPPED=14`、`NEAR_CONTINUOUS=12`、`INSUFFICIENT_EVIDENCE=175`，最大组 4 个零件。按修正后的 13 个确认主材分段编号计算，新 cache 候选证据召回 `13/13`。
