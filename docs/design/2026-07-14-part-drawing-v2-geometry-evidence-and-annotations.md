# 零件图 v2 几何证据与原生标注设计

## 文档状态

- 日期：2026-07-14
- 状态：已确认方向，待实施
- 导出器仓库：`I:\tmp\xingcaisuanfa-part-snapshot-exporter`
- 离线引擎仓库：`I:\tmp\zijinhuatekla-part-drawing-engine`
- 首个真实验收件：`T3-PX-317 / partId=45416496`

## 背景

`partDrawingSnapshot.v1` 已能支持普通平板外轮廓、圆孔和 Boolean cut 摘要，但真实 CAD 复核暴露三个问题：

1. 圆孔只输出圆，没有圆心十字线。
2. 孔组数量/直径被错误地放进直径 `DIMENSION`，CAD 显示为穿孔斜线且文字不稳定；样板需要独立引出标注。
3. Tekla 模型中的板边坡口在快照中只剩 `BOOLEAN_CUT` 包围盒，没有坡口边、两张主面轮廓、深度或角度，离线端无法可靠识别和绘制坡口线。

只给 `BOOLEAN_CUT` 增加坡口特例字段会继续形成规则堆砌。后续折弯、弧形、切角和复杂切口同样需要完整几何证据，因此导出器必须升级为通用、版本化的 selected-part 几何事实契约。

## 核心决策

1. 新增 `partDrawingSnapshot.v2`，导出选中零件的完整 solid faces、ordered loops、edges 和操作几何。
2. v2 保存模型事实，不在导出器中决定图纸尺寸、标注位置或最终加工表达。
3. 离线端继续兼容读取 v1；新导出器默认输出 v2。
4. 无法证明圆心、半径、曲面类型或操作参数时保留 `UNRESOLVED` 证据，不静默折线化，也不丢弃整个原始事实。
5. “契约可以承载某类型”不等于“该类型已完成自动出图”。每种新类型必须有真实样件、期望表达和回归验证后才升格。
6. 圆心标记与孔组引出属于独立图纸对象：中心线用 `PART_CENTER` 图层，孔组使用原生 CAD `MLEADER`，不再伪装为尺寸实体。

## 非目标

- 本阶段不完成折弯板自动展开。
- 本阶段不承诺任意自由曲面可生成加工图。
- 本阶段不根据 Boolean cutter 包围盒猜测坡口。
- 本阶段不把未知曲线离散成折线后标记为可靠圆弧。
- 本阶段不修改构件工序图、BOX 出图或 Tekla Drawing API 路线。

## 总体数据流

```text
Tekla selected Part
  -> partDrawingSnapshot.v2
       identity / manufacturing properties
       local frame / part form
       complete final solid topology
       explicit model operations and operative solids
       provenance / unresolved evidence
  -> SnapshotInput / Data Quality Gate
  -> GeometryAnalyzer / FeatureRecognizer
  -> DimensionPlanner / AnnotationPlanner
  -> PartDrawingDocument
  -> DXF native DIMENSION + MLEADER / PDF
```

## partDrawingSnapshot.v2

### 顶层结构

```text
schemaVersion = partDrawingSnapshot.v2
exporterVersion
modelIdentifier
exportedAt
part
  identity
  manufacturing
  localFrame
  partForm
  finalGeometry
  holes
  operations
  provenance
  qualityIssues
```

### partForm

枚举：

- `FLAT_PLATE`
- `BENT_PLATE`
- `CURVED_PLATE`
- `PROFILE`
- `UNKNOWN`

`partForm` 是来源类型和几何事实分类，不表示离线引擎已支持该类型出图。首期自动出图仍只接受 `FLAT_PLATE`。

### finalGeometry

```text
finalGeometry
  faces[]
  edges[]
  vertices[]
  principalFaceIds[]
  bounds
```

每个 face：

```text
faceId
surfaceType: PLANE / CYLINDER / CONE / SPHERE / NURBS / UNKNOWN
normal
origin
axis
radius
relationToPartFrame: NORMAL_POSITIVE / NORMAL_NEGATIVE / SIDE / OBLIQUE
loops[]
  orderedEdgeIds[]
  orderedVertices[]
sourceEvidence
```

每个 edge：

```text
edgeId
curveType: LINE / ARC / CIRCLE / ELLIPSE / SPLINE / UNKNOWN
start
end
center
axis
radius
startAngle
endAngle
clockwise
adjacentFaceIds[]
curveEvidenceStatus: PROVEN / UNRESOLVED
sourceEvidence
```

规则：

- Tekla API 能提供圆心/轴/半径时输出参数化曲线。
- Tekla 2017 只提供 curved edge 端点时输出 `curveType=UNKNOWN`、端点和 `UNRESOLVED`，不得猜 ARC。
- face loop 必须保持 Tekla 原生拓扑顺序。
- `principalFaceIds` 只标记与板法向平行、面积有效的两张主要面；不得只保留面积最大的一张。
- 所有坐标保留模型坐标，同时由 `localFrame` 支撑下游稳定投影。

### operations

```text
operationId
operationType: BOOLEAN_CUT / FITTING / CHAMFER / BEND / CONTOUR / UNKNOWN
targetPartIds[]
nativeParameters
operativeGeometry
  faces[]
  edges[]
  vertices[]
sourceEvidence
qualityIssues
```

Boolean cutter 不再只输出 `boundsMin/boundsMax`。包围盒可以保留为索引信息，但必须同时输出可读取的 operative solid 几何。Tekla 原生 Chamfer、Fitting 或 Bend 参数存在时写入 `nativeParameters`；不存在时保持空并依靠最终 solid 事实，不编造参数。

### provenance 和 qualityIssues

每个事实必须能够追溯到以下一种或多种来源：

- `TEKLA_FINAL_SOLID_FACE`
- `TEKLA_FINAL_SOLID_EDGE`
- `TEKLA_BOOLEAN_OPERATIVE_SOLID`
- `TEKLA_CONTOUR_CHAMFER`
- `TEKLA_FITTING`
- `TEKLA_BENT_PLATE`
- `TEKLA_BOLT_GROUP`

典型质量码：

- `CURVE_PARAMETERS_UNRESOLVED`
- `SURFACE_TYPE_UNRESOLVED`
- `PRINCIPAL_FACE_PAIR_MISSING`
- `OPERATIVE_SOLID_UNAVAILABLE`
- `BEND_PARAMETERS_INCOMPLETE`
- `PART_FORM_UNSUPPORTED_FOR_DRAWING`

原始事实可导出但当前不能出图时，快照仍可写出并携带质量问题；是否阻断零件图由消费端 Data Quality Gate 决定。

## v1 兼容

- `SnapshotInput` 同时接受 v1 和 v2。
- v1 映射为最小兼容内部结构：既有 `outerLoop/innerLoops/holes/cuts` 保持行为不变。
- v2 使用 `finalGeometry` 构建同一内部 `PartDrawingSnapshot`，同时保留完整 face/edge/operation evidence。
- 不允许把 v2 缺失字段静默降级成 v1 成功；缺少必要主面事实时进入质量门。
- 制造指纹加入几何 schema 和 principal-face evidence 版本，避免 v1/v2 不同证据被错误归并。

## 通用特征覆盖策略

### 平板与孔

- 完整主面轮廓、孔和孔组继续自动出图。
- 每个圆孔绘制水平/垂直十字中心线，中心线在纸面上越过圆周固定距离，并使用 `PART_CENTER` 图层及中心线型。
- 孔组数量/直径由 `AnnotationPlanner` 合并为一次 `6Φ27` 等表达。

### 坡口

严格证据路径按优先级：

1. Tekla 原生坡口/Chamfer 参数。
2. 明确的 operative cutter solid 与目标板最终 solid。
3. 两张 principal face 外轮廓之间可证明的单边退让。

只有在以下条件同时满足时自动识别板边坡口：

- 两张 principal face 均可靠且法向相反。
- 对应边可按拓扑和空间位置稳定配对。
- 两面在该边存在超过容差的退让差，其他邻接边关系保持一致。
- 板厚、退让深度和坡口方向可计算。

输出 `BEVEL_EDGE`：坡口边、正反面、退让深度、计算角度、来源 face/edge/operation id 和证据码。图纸绘制独立 `BEVEL` 图层坡口线；参数完整时生成坡口引出，参数不完整时画证据线并标记 `REVIEW_REQUIRED`，不得猜角度。

### 切角与缺口

- 主面最终轮廓中的直线切角继续由轮廓事实识别。
- operative solid 用于区分显式加工操作，但不能覆盖最终 solid 真相。
- 多处切角按几何和操作 id 分别输出，不围绕零件号写规则。

### 圆弧和弧形切口

- `curveEvidenceStatus=PROVEN` 且存在圆心/半径时自动构建 ARC/CIRCLE。
- 只有曲线端点时保留 `UNKNOWN + UNRESOLVED`，图纸状态为复核或拒绝。
- 圆柱面可为孔或卷曲证据，但必须结合面拓扑和操作来源，不能只凭曲面类型命名特征。

### 折弯和曲面板

- v2 必须保存 BentPlate 类型、完整 faces/edges、可读取的 bend line、半径、角度和方向。
- 缺少 Tekla 原生 bend 参数时记录 `BEND_PARAMETERS_INCOMPLETE`。
- 当前平板图引擎对 `BENT_PLATE/CURVED_PLATE` 返回 `PART_FORM_UNSUPPORTED_FOR_DRAWING`，但不得丢弃快照。
- 后续自动展开必须单独设计中性层、折弯扣除和展开验证，并使用真实折弯样件验收。

## 图纸原生对象修正

### 圆心十字线

- `PartDrawingDocument` 为每个圆孔生成两条正交 `DrawingLine`。
- 线段通过孔中心，纸面长度为孔径加两侧固定越界量。
- DXF 使用 `PART_CENTER` 图层和中心线型；PDF 使用同一几何。
- 中心线不参与尺寸语义，但作为视图障碍参与引出避让。

### 孔组 MLEADER

- 新增独立 `PlannedCallout` / `PlacedCallout`，不再转换成 `PlacedDimensionKind.DIAMETER`。
- DXF 使用 ezdxf `add_multileader_mtext()` 生成原生 `MULTILEADER`。
- 内容采用样板口径 `6Φ27`；文字样式、箭头、落点和引线长度由版本化 callout style 控制。
- 引线箭头落在代表孔圆周，不穿过孔中心。
- PDF 从同一 `PlacedCallout` 绘制引线、箭头和文字。
- 单孔也走 callout，不使用穿圆直径尺寸线，除非未来明确选择标准直径 DIMENSION 表达。

## 代码边界

### 导出器仓库

建议新增或修改：

- `PartDrawingSnapshotContracts.cs`：v2 face/edge/operation DTO。
- `PartDrawingSolidEvidence.cs`：纯几何 DTO、face/edge id、拓扑和 principal face 配对逻辑。
- `Tekla2017PartDrawingSnapshotExporter.cs`：Tekla API 适配，读取 final/operative solid。
- `PartDrawingSnapshotBuilder.cs`：v2 质量门和序列化。
- `TeklaSectionClassifier.Tests/`：双主面、坡口 wedge、弧边 unresolved、折弯证据契约测试。

现有 bin/obj 生成文件不作为业务改动提交。

### 离线引擎仓库

建议新增或修改：

- `contracts.py` / `snapshot_input.py`：v1/v2 兼容内部契约。
- `geometry_analyzer.py`：principal faces 和曲线证据归一化。
- `feature_recognizer.py`：严格 `BEVEL_EDGE` 识别。
- `dimension_planner.py`：坡口和孔组 callout 规划。
- `dimension_optimizer.py`：独立 callout 布局。
- `drawing_output.py`：中心线、BEVEL 和 MULTILEADER/PDF renderer。
- 对应单元、pipeline 和输出测试。

## 分阶段实施

### 阶段 A：图面对象修正

- 圆孔中心十字线。
- 独立 `PlacedCallout`。
- 原生 DXF MULTILEADER 和 PDF 等价表达。
- 使用当前 v1 快照重新生成 `T3-PX-317`，确认问题 1、2 修复。

### 阶段 B：v2 通用几何导出

- 完整 final solid faces/edges/vertices。
- 双 principal faces。
- 完整 Boolean operative solid。
- v1/v2 跨语言契约测试。

### 阶段 C：坡口闭环

- 重新在 Tekla 中选择真实 `T3-PX-317` 导出 v2。
- 离线识别坡口边、退让和角度证据。
- 生成坡口线和引出，人工对照模型。

### 阶段 D：后续类型案例化验收

- 分别收集折弯、原生圆弧、切角、弧形切口真实样件。
- 每类补期望表达、证据字段、质量门和回归测试。
- 未完成真实验收的类型只标记“契约可承载”，不标记“自动出图支持”。

## Acceptance Criteria

### 图面对象

1. 每个圆孔都有两条可读中心线，DXF `PART_CENTER` 非空。
2. `T3-PX-317` 只有一个孔组引出 `6Φ27`，DXF 对象类型为 `MULTILEADER`。
3. 孔组引线箭头落在孔圆周且不穿孔中心，不再存在伪装孔组说明的直径 DIMENSION。
4. PDF 与 DXF 的孔组文字、箭头目标和中心线一致。

### v2 契约

5. v2 快照包含 selected part 的全部 final solid faces、ordered loops、edges 和 vertices。
6. 平板至少包含两张方向相反的 principal face，不能只输出面积最大面。
7. Boolean cut 包含 operative solid 几何，不再只有包围盒。
8. 无参数曲线明确输出 `UNKNOWN/UNRESOLVED`，不静默折线化。
9. v1 快照仍可由离线引擎读取并保持既有普通平板回归。
10. v2 快照可由 Python 直接读取，无字段转换脚本。

### 坡口

11. 真实 `T3-PX-317` v2 快照能追溯坡口相关 principal faces、edges 和 Boolean operation。
12. 离线端输出至少一个有边、方向、深度/角度状态和 evidence id 的 `BEVEL_EDGE`。
13. DXF/PDF 绘制与 Tekla 模型一致的坡口线；参数证据完整时生成坡口引出，不完整时显式复核。
14. 生产代码和测试中不存在 `T3-PX-317`、项目名或固定几何坐标硬编码。

### 未来类型护栏

15. 折弯、弧形、切角 fixture 能证明 v2 契约保存相应事实或明确 unresolved，不能无记录丢失。
16. 未经真实样件验收的折弯/弧形类型不得返回自动出图 `OK`。

## Verification Plan

### C# 单元和契约测试

- 双平行主面及 side faces 的稳定 id、关系和 ordered loops。
- wedge bevel solid：两面边缘退让证据保留。
- Boolean operative solid 的 faces/edges/vertices 完整序列化。
- line、proven arc、unresolved curve 三种 edge。
- BentPlate/curved form 和缺失 bend 参数质量码。
- v2 JSON 可由 Python fixture 直接消费。

### Python 单元和输出测试

- v1/v2 parser 兼容。
- principal face 配对、严格坡口识别及非坡口反例。
- 每孔两条中心线，长度和图层正确。
- `PlacedCallout` 与尺寸对象分离。
- DXF 读回存在 `MULTILEADER`，不存在孔组伪直径 DIMENSION。
- PDF/DXF callout 文字集合一致。
- 坡口线和 evidence 可序列化。

### 最小命令

```powershell
dotnet test I:\tmp\xingcaisuanfa-part-snapshot-exporter\TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj
dotnet build I:\tmp\xingcaisuanfa-part-snapshot-exporter\TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj
python -m unittest tests.test_part_drawing_contracts tests.test_part_drawing_features tests.test_part_drawing_dimensions tests.test_part_drawing_layout tests.test_part_drawing_output tests.test_part_drawing_pipeline
python -m unittest discover -s tests
```

### 真实 Tekla 验收

1. 选择 `T3-PX-317` 并重新导出 v2。
2. 摘要记录 face/edge/operation/principal-face 数量，不在聊天粘贴完整 JSON。
3. 运行 `draw-parts` 生成 DXF/PDF/drawing JSON。
4. 对照 Tekla 模型检查坡口所在边、方向、坡口线和说明。
5. 在目标 CAD 中检查中心线、MULTILEADER、原生尺寸和图层。
6. 完整命令、统计和人工结论写入 `docs/verification/2026-07-14-part-drawing-v2-geometry-smoke.md`。

