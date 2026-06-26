# Main Material Segment Export Contract

## Scope

为箱型柱/BOX 构件主材分段集合算法补 Tekla 导出字段。目标是用工程证据确认：同一壁板面、沿构件主轴连续、分段接缝相邻。

本契约不允许用同厚、近宽、长板、多段板作为最终强判据。厚度、宽度、长度只能作为辅助证据或候选排序字段。

## Exporter Changes

修改项目：`I:\xingcaisuanfa`

涉及文件：

- `TeklaSectionClassifier.Runner\BodyBracketExportDtos.cs`
- `TeklaSectionClassifier.Runner\BodyBracketBundleExporter.cs`

新增 assembly 级字段：

- `metadata.memberAxisEvidence.origin`
- `metadata.memberAxisEvidence.direction`
- `metadata.memberAxisEvidence.length`
- `metadata.memberAxisEvidence.source`

新增 part 级字段：

- `mainMaterialEvidence.axisStationStart`
- `mainMaterialEvidence.axisStationEnd`
- `mainMaterialEvidence.axisStationLength`
- `mainMaterialEvidence.bodyFaceId`
- `mainMaterialEvidence.bodyFaceOffset`
- `mainMaterialEvidence.isBodyWallPlateCandidate`
- `mainMaterialEvidence.evidenceSource`
- `mainMaterialEvidence.segmentAdjacency.previousPartId`
- `mainMaterialEvidence.segmentAdjacency.nextPartId`
- `mainMaterialEvidence.segmentAdjacency.previousGap`
- `mainMaterialEvidence.segmentAdjacency.nextGap`
- `mainMaterialEvidence.segmentAdjacency.evidenceSource`

## Semantics

`memberAxisEvidence` 是构件主轴证据，当前由 main part 的最长局部轴推导。后续如果接入更准确的 member axis 或 Tekla MCP，可以替换 source，但消费层字段保持稳定。

`axisStationStart/End` 表示零件包围盒投影到构件主轴后的区间，用于判断主轴方向分段顺序和接缝间隙。

`bodyFaceId` 当前是径向 face bucket 证据，不是最终工程壁板面编号。Python 侧主材分段算法必须把它当成 evidence，不得仅凭该字段自动定案。

`segmentAdjacency` 当前按同 `bodyFaceId` 的 station 排序生成 previous/next/gap，用于后续确认接缝相邻关系。

## Section Projection Evidence

2026-06-23 补充：异形 BOX 不能依赖包围盒或全局径向分桶判断内外。导出器在 `mainMaterialEvidence.sectionProjectionEvidence` 下新增真实截面投影证据：

- `evidenceSource`: 当前为 `memberAxisSectionProjection.v1`。
- `sectionPlaneOrigin`: 构件主轴原点。
- `sectionAxisU` / `sectionAxisV`: 垂直于构件主轴的截面坐标轴。
- `projectedCentroid`: 零件质心投影到截面 U/V 坐标。
- `projectedBoundsMin` / `projectedBoundsMax`: 零件投影点在截面上的包络。
- `projectedContour`: 优先使用 Tekla `ContourPlate` 轮廓点投影；无轮廓点时退回 solid bounding box 角点投影。
- `normalProjection`: 板法向在截面 U/V 坐标中的投影。
- `normalProjectionMagnitude`: 板法向落在截面平面的强度，可辅助区分沿主轴的横隔板与沿轴向延伸的壁板。
- `pointSource`: `contourPoints` 或 `solidBoundingBoxCorners`。

该字段只表达可复核的截面几何证据，不在导出器中直接声明 `INNER/OUTER/WALL`。下游应基于投影轮廓、焊接/接触关系、station 连续性和闭环拓扑综合判断。


## Box Section Topology Evidence

2026-06-24 补充：BOX 内外关系和主壁板复核不能再消费旧 point-set 作为闭合 loop。导出器在 `metadata.boxSectionEvidence` 下新增 Tekla solid 原生截面拓扑证据，当前 source 为 `teklaSolidFaceSectionSegments.v2`。

Assembly metadata 字段：

- `boxSectionEvidence.source`
- `boxSectionEvidence.stationLoops[].station`
- `boxSectionEvidence.stationLoops[].supportPartIds`
- `boxSectionEvidence.stationLoops[].sectionSegments`
- `boxSectionEvidence.stationLoops[].sectionLoops`
- `boxSectionEvidence.stationLoops[].closedLoopCount`
- `boxSectionEvidence.stationLoops[].openChainCount`
- `boxSectionEvidence.stationLoops[].degeneratePartLoopCount`
- `boxSectionEvidence.stationLoops[].diagnostics`

Part loop 字段：

- `boxSectionEvidence.stationLoops[].partLoops[].partId`
- `boxSectionEvidence.stationLoops[].partLoops[].segments`
- `boxSectionEvidence.stationLoops[].partLoops[].sectionLoops`
- `boxSectionEvidence.stationLoops[].partLoops[].closedLoopCount`
- `boxSectionEvidence.stationLoops[].partLoops[].openChainCount`
- `boxSectionEvidence.stationLoops[].partLoops[].loopStatus`
- `boxSectionEvidence.stationLoops[].partLoops[].area`
- `boxSectionEvidence.stationLoops[].partLoops[].isClosed`
- `boxSectionEvidence.stationLoops[].partLoops[].isValid`
- `boxSectionEvidence.stationLoops[].partLoops[].bounds`
- `boxSectionEvidence.stationLoops[].partLoops[].diagnostics`

下游消费顺序：

1. 优先使用 exporter `sectionLoops` 构建真实截面 topology。
2. 若 `sectionLoops` 缺失，则用 `segments` + geometry library polygonize。
3. 仅为兼容旧 cache，最后才 fallback 到旧 `points`。
4. station topology diagnostics 必须输出核心 BODY station 与端部/附件触发 station 的区别，避免把端部过渡误报为主体闭合失败。
## Algorithm Direction

下一步在 `I:\zijinhuatekla` 中新增 BOX 主材分段集合算法：

1. 读取新导出字段。
2. 按 `bodyFaceId` 先做候选分面。
3. 在同一面内按 `axisStationStart/End` 排序。
4. 用 `segmentAdjacency` 和 gap 判断连续/近连续/断开。
5. 结合 Case Bank 人工确认集合评估召回率，不把厚度不同的分段提前排除。
6. 输出 `BOX_MAIN_MATERIAL_SEGMENT_GROUP` 报告，作为制造范围映射的上游证据。

## Acceptance Criteria

- 新导出的 JSON 每个 assembly 有 `metadata.memberAxisEvidence`。
- 每个 part 有 `mainMaterialEvidence`。
- 新导出 JSON 的每个 part 有 `mainMaterialEvidence.sectionProjectionEvidence`。
- 新导出 JSON 的 BOX assembly 有 `metadata.boxSectionEvidence.source=teklaSolidFaceSectionSegments.v2`。
- station loop 证据优先提供 `sectionLoops`；缺失时可提供 `sectionSegments/segments`，Python 侧可 polygonize；旧 `points` 仅作兼容 fallback。
- 旧严格编号规则不变：普通 Excel 行仍必须精准匹配 `partPosition`。
- 主材分段集合算法不得用厚度相等作为必要条件。
- 若 `bodyFaceId` 或 adjacency 证据不足，进入 Data Quality Gate，不写特例规则。

## Verification

已运行：

```powershell
dotnet build I:\xingcaisuanfa\TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj
```

结果：构建成功，0 errors，4 warnings。警告为既有 nullable/可能 null 返回类型，不阻塞本次导出字段新增。

还需要用户重新从 Tekla 选择 `T3-5GKZ-10` 导出一份新 cache，然后在 `I:\zijinhuatekla` 中接入新字段做算法 smoke。
