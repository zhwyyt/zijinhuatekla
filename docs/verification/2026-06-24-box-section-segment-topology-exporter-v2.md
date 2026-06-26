# BOX Section Segment Topology Exporter v2 Verification

## Context

用户要求整体修复 Tekla 导出器，不能只针对 `T3-P-6203` 或某个 loop 写判定规则。根因是旧 `metadata.boxSectionEvidence.stationLoops[].partLoops[].points` 实际只是 solid face 与 station 平面的相交点集，不是真正闭合截面 loop。Python 侧把点集当 polygon 使用时，在上部 station 出现退化、多组件、缺 cavity。

本轮把导出器截面证据从 point-set 升级为 segment/loop topology，并让 Python 优先消费真实 `sectionLoops`，再退回 `segments` polygonize，最后才兼容旧 `points`。

## Exporter Changes

修改位置：`I:\xingcaisuanfa\TeklaSectionClassifier.Runner`

- `BodyBracketExportDtos.cs`
  - `ExportedBoxSectionStationLoop` 新增：`sectionSegments`、`sectionLoops`、`closedLoopCount`、`openChainCount`、`degeneratePartLoopCount`、`diagnostics`。
  - `ExportedBoxSectionPartLoop` 新增：`segments`、`sectionLoops`、`loopStatus`、`area`、`isClosed`、`isValid`、`bounds`、`diagnostics`。
  - 新增 `ExportedSectionSegment`、`ExportedSectionLoop`、`ExportedSectionBounds` DTO。
- `BodyBracketBundleExporter.cs`
  - `IntersectSolidFacesWithPlane` 不再只返回点；共面 edge 以 `EDGE_ON_PLANE` segment 输出，普通 face-loop 穿越以 `FACE_LOOP_PLANE_CROSSING` segment 输出。
  - 导出端按 segment graph 追踪闭合 loops，输出 part 级和 station 级 loop/diagnostic。
  - `metadata.boxSectionEvidence.source` 升级为 `teklaSolidFaceSectionSegments.v2`。

## Python Consumer Changes

修改位置：`I:\zijinhuatekla`

- `src/zijinhua_tekla/classifiers/box_part_spatial_relations.py`
  - `_station_topology_from_part_loops` 优先使用 `sectionLoops`。
  - 其次用 `segments` + Shapely `polygonize`。
  - 最后才 fallback 到旧 `points`。
  - evidence code 透传 `EXPORTED_SECTION_LOOP_TOPOLOGY` / `EXPORTED_SECTION_SEGMENT_POLYGONIZE` / `SHAPELY_BOX_SECTION_TOPOLOGY`。
- `src/zijinhua_tekla/classifiers/box_station_topology_diagnostics.py`
  - 诊断统计优先识别 exporter `sectionLoops`，避免旧 points 造成假退化。
- `tests/test_box_part_spatial_relations.py`
  - 新增回归：当旧 `points` 退化但新 `sectionLoops` 有效时，必须按新拓扑判定 cavity 内部点。

## Verification Commands

```powershell
dotnet build I:\xingcaisuanfa\TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj
python -m unittest discover -s tests
I:\xingcaisuanfa\TeklaSectionClassifier.Runner\bin\Debug\net48\TeklaSectionClassifier.Runner.exe --body-bracket-export --out I:\zijinhuatekla\cache\20260624_section_segments_v2
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260624_144128 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\box-section-segments-v2-smoke-20260624
```

## Results

- Exporter build: succeeded, 0 errors, 7 nullable warnings.
- Python tests: 77 tests OK. Existing `openpyxl datetime.utcnow()` warning remains unrelated.
- New cache: `I:\zijinhuatekla\cache\20260624_144128`.
- New JSON contains `teklaSolidFaceSectionSegments.v2`, `sectionSegments`, `sectionLoops`, `closedLoopCount`.

Smoke output: `outputs\box-section-segments-v2-smoke-20260624`.

空间关系分布：

- `INSIDE_BODY=150`
- `OUTSIDE_ATTACHMENT=75`
- `BOUNDARY_OR_THROUGH=18`
- `MAIN_WALL=16`

Station topology 分布：

- `CLOSED_WITH_CAVITY=101`
- `CLOSED_WITHOUT_CAVITY=47`
- `STATION_TOPOLOGY_NOT_CLOSED=4`

对比旧 `20260624_092738` 诊断：

- 旧：`CLOSED_WITH_CAVITY=33`、`STATION_TOPOLOGY_NOT_CLOSED=85`、`CLOSED_WITHOUT_CAVITY=34`。
- 新：`CLOSED_WITH_CAVITY=101`、`STATION_TOPOLOGY_NOT_CLOSED=4`、`CLOSED_WITHOUT_CAVITY=47`。
- 旧退化主壁板 loop 86 个 station；新剩余 4 个不闭合 station 的 `degenerate_loop_count=0`，问题变成末端只有 3 个主壁板组件参与，非旧 point-set 退化。

关键零件核对：

- `T3-P-6203` 4 个实体全部为 `INSIDE_BODY`，`section_relation=projected_centroid_in_cavity_loop`，证据包含 `POINT_IN_CAVITY_LOOP;EXPORTED_SECTION_LOOP_TOPOLOGY`。
- `T3-GG-2` 8 个实体全部为 `OUTSIDE_ATTACHMENT`，`section_relation=projected_centroid_outside_enclosure`，证据包含 `EXPORTED_SECTION_LOOP_TOPOLOGY`。
- BOX 主壁板确认集合仍为 16 个 Tekla 实体 / 13 个去重 partPosition：`T3-P-4917`、`T3-P-4918`、`T3-P-4919`、`T3-P-5571`、`T3-P-5576`、`T3-P-5577`、`T3-P-5579`、`T3-P-6268`、`T3-P-6269`、`T3-P-6270`、`T3-P-6271`、`T3-P-6272`、`T3-P-6284`。

## Remaining Risk

剩余 4 个 `STATION_TOPOLOGY_NOT_CLOSED` station：`10488.737`、`10520.073`、`10558.408`、`10585.001`。这些 station 不再是退化/invalid loop，而是 `UNION_HAS_MULTIPLE_COMPONENTS` 且只有 3 个主壁板 loop，后续应作为末端采样/支撑壁板缺席诊断继续处理，不应回到规则硬判定。

## Follow-up: Four Non-Closed Stations Root Cause

用户指出剩余 4 个 `STATION_TOPOLOGY_NOT_CLOSED` 不应存在。本轮继续诊断后确认：它们不再是导出器 loop 退化，也不是主壁板 solid 截面无法闭合，而是 station 采样范围混入了端部/附件触发点。

四个 station：

- `10488.737`
- `10520.073`
- `10558.408`
- `10585.001`

证据：

- 这四个 station 的主壁板 part loop 均 `isClosed=true`，`degenerate_loop_count=0`，`openChainCount=0`。
- 参与主壁板只有 3 个：`T3-P-4918`、`T3-P-4917`、`T3-P-4917`。
- `T3-P-4919` 仍是人工确认的主壁板之一；其导出 solid 覆盖的 `axisStationEnd=10452.706`。这 4 个 station 均在该实体截面尾端之后，因此这里不能再按“4919 仍参与截面”的四壁板闭合要求判失败。
- 同 station 存在大面积 `T3-P-4889 / PL16` 截面，范围 `10438.913-10601.233`，但其 `normalProjectionMagnitude=0.168825`，明显不同于主壁板接近 `1.0` 的外壁法向证据，更像端部/过渡板，而不是漏掉的第四块侧壁。
- 这些 station 的触发源来自非主壁零件 start/mid/end，例如 `T3-P-4889`、`T3-P-6203`、`T3-P-6240`、`T3-P-6189`、`T3-PR-15`。

处理方式：

- 不把 `T3-P-4889` 硬塞进主壁板集合。
- 不对 `T3-P-6203` 或任意零件号加规则。
- 在 station topology diagnostics 中新增 `station_scope`：
  - `BODY_CORE`
  - `END_TRANSITION_OR_ATTACHMENT_TRIGGERED`
  - `INSUFFICIENT_SCOPE_EVIDENCE`
- 对端部/附件触发 station 输出 `END_TRANSITION_NOT_BODY_CORE`，不再算作核心 BOX 截面闭合失败。

最新 smoke：`outputs\box-section-segments-v2-scope-smoke-20260624`。

最新分布：

- `CLOSED_WITH_CAVITY=101`
- `CLOSED_WITHOUT_CAVITY=47`
- `END_TRANSITION_NOT_BODY_CORE=4`
- `BODY_CORE=148`
- `END_TRANSITION_OR_ATTACHMENT_TRIGGERED=4`

`T3-P-6203` 仍为 `INSIDE_BODY=4`；`T3-GG-2` 仍为 `OUTSIDE_ATTACHMENT=8`。

