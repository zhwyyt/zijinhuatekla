# BOX Station Topology Export Diagnostics

## Context

用户指出 `T3-P-6203` 在模型截图中完全位于 BOX 空腔内，但当前多 loop 拓扑 smoke 将其判为 `BOUNDARY_OR_THROUGH`。本轮不在判定层加规则，而是诊断 station topology 为什么在上部切面没有闭合出内腔。

## Python Diagnostic Output

新增 offline 输出：

- `T3-5GKZ-10-box-station-topology-diagnostics.json`
- `T3-5GKZ-10-box-station-topology-diagnostics.csv`

smoke 命令：

```powershell
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260624_092738 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\box-station-topology-diagnostics-smoke-20260624-v3
```

诊断统计：

- station rows: 152
- `CLOSED_WITH_CAVITY=33`
- `STATION_TOPOLOGY_NOT_CLOSED=85`
- `CLOSED_WITHOUT_CAVITY=34`
- `DEGENERATE_OR_INVALID_MAIN_WALL_LOOP=86` stations
- `UNION_HAS_MULTIPLE_COMPONENTS=115` stations
- `STATION_HAS_INNER_CAVITY_LOOP=33` stations

退化主壁板 loop 涉及 partPosition 次数：

- `T3-P-4917=60`
- `T3-P-5579=41`
- `T3-P-5577=41`
- `T3-P-5571=37`
- `T3-P-5576=34`
- `T3-P-4918=28`
- `T3-P-6268=24`
- `T3-P-6269=24`
- `T3-P-4919=4`
- 少量：`T3-P-6284/T3-P-6272/T3-P-6271/T3-P-6270`

## T3-P-6203 Root Cause Evidence

`T3-P-6203` 的 probe station：

- 约 9515.5：附近 station 可闭合出 cavity，点关系为 `cavity`。
- 约 10005.7：附近 station 未闭合出 cavity，点关系被判为 `outside`。
- 约 10495.9：附近 station 未闭合出 cavity，点关系被判为 `outside`。

对应 station 诊断示例：

### station 10005.648746

主壁板 `partLoops`：

- `T3-P-4919 / 72806723`: area `27397.7`, valid `true`
- `T3-P-4918 / 72806741`: area `0.0`, valid `false`, repaired area `6849.2`
- `T3-P-4917 / 72806751`: area `0.0`, valid `false`, repaired area `6392.8`
- `T3-P-4917 / 72806761`: area `0.0`, valid `false`, repaired area `6392.8`

union result：`MultiPolygon`, 4 components, inner loop `0`。

### station 10488.737156 / 10520.072898

- `T3-P-4919` 主壁板 loop 已缺失。
- 剩余 `T3-P-4918` 与两段 `T3-P-4917` loop 均为退化/invalid。
- union result：`MultiPolygon`, inner loop `0`。

结论：`T3-P-6203` 本身不是边界或穿透件；疑义来自 station topology 特征失败。

## Exporter Root Cause

当前导出器：`I:\xingcaisuanfa\TeklaSectionClassifier.Runner\BodyBracketBundleExporter.cs`

关键逻辑：

- `BuildBoxSectionEvidence` 对每个 station 调用 `IntersectSolidFacesWithPlane(part, ...)`。
- `IntersectSolidFacesWithPlane` 遍历 solid face loops，将每条 face loop 与切面相交得到的点加入 `points`。
- `ExportedBoxSectionPartLoop.Points` 保存的是这些去重后的 intersection points。

问题：字段名是 `partLoops`，但内容并不是真正的截面闭合 loop；它只是无序/弱有序的 intersection point set。切面经过板侧面、边界或与 face loop 共面时，常得到共线点、重复点或局部边点，Python 侧将其当 polygon 会出现：

- `area=0`
- `is_valid=false`
- `MultiPolygon` 多组件
- inner/cavity loop 缺失

因此这是导出契约问题，不应该在 Python 判定层硬规则修补。

## Required Exporter Fix

导出器需要从“导出点集”升级为“导出截面边/环拓扑”：

- 对每个 part/station 输出 `sectionSegments`：相交线段的两个端点、source face/loop id、segment length。
- 或直接输出 `sectionLoops`：由相交线段组装出的闭合环，带 `area/isClosed/isValid/bounds`。
- station 级输出 `outerLoop/innerLoops` 不能来自凸包，应来自 segment polygonize / loop tracing。
- 对退化情况输出 `diagnostics`：共面边、重复点、open chain、gap length、component count。

Python 侧当前新增诊断报告作为 Data Quality Gate，不应将 `STATION_TOPOLOGY_NOT_CLOSED` 当作 outside 强证据。

## Verification

- `python -m unittest discover -s tests`：76 tests OK。
- smoke 输出已生成 station topology diagnostics 文件。
