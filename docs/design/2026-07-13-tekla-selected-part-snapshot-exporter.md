# Tekla 当前选择集零件图快照导出器设计

## 文档状态

- 日期：2026-07-13
- 状态：已确认设计
- 实现仓库：`I:\xingcaisuanfa`
- 消费端仓库：`I:\tmp\zijinhuatekla-part-drawing-engine`
- 范围：Tekla Structures 2017 当前选中平板 `Part` 到 `partDrawingSnapshot.v1`

## 背景与目标

离线零件图引擎已经能够消费 `partDrawingSnapshot.v1` 并生成 DXF、PDF 和 drawing JSON。当前缺口是 Tekla 生产端：现有导出器会把选择集中的零件解析成所属构件，不能只导出直接选中的零件，也没有输出零件图所需的有序最终轮廓。

本阶段新增独立命令行模式，只读取 Tekla 当前选择集中的平板 `Part`，每个实体输出一份严格匹配离线消费端的快照。C# 导出器不启动 Python，也不负责归并编号、生成尺寸或渲染图纸。

## 非目标

- 不生成 DXF、PDF 或 Tekla 原生零件图。
- 不自动扩展到选中零件所属的整个 Assembly。
- 不支持折弯板、型钢、空间零件或不能证明为单一平面的零件。
- 不用几何相似替代、修正或推断 `partPosition`。
- 不对无法恢复工程语义的曲线静默折线化。
- 不重构现有构件识别和 Body/Bracket 导出流程。

## 命令与数据流

```powershell
TeklaSectionClassifier.Runner.exe `
  --export-part-drawing-snapshots `
  --output <output-directory>
```

处理流程：

```text
Runner 参数分流
-> Tekla 当前选择集中的直接 Part
-> FlatPlateEligibilityChecker
-> PartGeometryExtractor
-> PartDrawingSnapshotBuilder
-> JSON writer
-> export-summary.json
```

新参数必须在默认构件导出流水线之前分流。未传入参数时，现有行为保持不变。

## 选择集语义

1. 只消费选择集中直接出现的 `Part`。
2. 不把 `Part` 扩展为 Assembly，也不导出同构件其他零件。
3. Assembly、BoltGroup 和其他对象不作为零件快照输入，写入汇总的 `SKIPPED` 明细。
4. 以 Tekla `Identifier.ID` 去重，避免同一实体重复输出。
5. 空选择集返回非零退出码，并输出可执行的错误说明。

## 平板质量门

首期接受：

- `ContourPlate`。
- profile 明确为 `PL...`、且能证明为单一平面的普通 `Part`。

首期拒绝：

- `BentPlate` 或其他折弯证据明确的零件。
- H、BH、BOX、管材等型材。
- 厚度、`partPosition`、局部坐标系或最终闭合轮廓缺失。
- 主面不平行、存在多个不相连外轮廓或不能证明为单一平板。
- 包含无法恢复圆心和方向的曲线边界。

厚度按明确证据优先级读取：Tekla report property、板件 profile 属性、可验证的 `PL` profile 解析。包围盒最小尺寸不得作为正式厚度来源。

## 几何提取

### 局部坐标系

使用零件坐标系原点和 X/Y 轴；法向由 X、Y 叉积并归一化得到。坐标系必须正交且非退化。所有轮廓点仍按三维模型坐标写入快照，局部坐标系负责下游投影。

### 最终轮廓

1. 从 `Part.GetSolid()` 枚举与板法向平行的面。
2. 按投影面积和法向厚度位置选择一个最终主面。
3. 保留 Tekla face loop 的原生顶点顺序，容差内闭合并去除相邻重复点。
4. 在局部 XY 平面计算有符号面积；绝对面积最大的闭环为 `outerLoop`，其余被外环包含的闭环为 `innerLoops`。
5. 每个环必须无自交、无极短边，并与外环拓扑一致。

最终 Solid 是切割后的几何真相。ContourPlate 原始轮廓只用于补充明确的 Chamfer/圆弧语义，不得覆盖最终 Solid 中已经发生的切割。

### 直线、圆弧和孔槽

- 直线边输出 `kind=LINE`、`start` 和 `end`。
- 仅当 Tekla ContourPoint/Chamfer 或其他原生证据能确定圆心、端点和方向时输出 `kind=ARC`。
- Tekla 2017 `Solid.Edge` 只暴露类型和端点，不能提供圆心；因此不能只凭 curved edge 类型猜测 ARC。
- BoltGroup 作用于目标零件时，根据 `BoltPositions`、`BoltSize`、`HoleType`、`SlottedHoleX/Y` 和坐标系输出圆孔或长圆孔。
- Boolean cut 和 fitting 写入 `cuts` 及来源证据；其最终效果仍必须出现在主面环中。
- 无法证明的曲线返回 `UNSUPPORTED_CURVE_GEOMETRY`，不得静默离散成折线并标记成功。

## 快照契约

每个实体输出一个完整 `partDrawingSnapshot.v1`：

```text
schemaVersion = partDrawingSnapshot.v1
exporterVersion
modelIdentifier
exportedAt
part
  partId
  partPosition
  assemblyId
  name
  profile
  material
  quantity = 1
  thickness
  localFrame
  outerLoop
  innerLoops
  holes
  cuts
  sourceEvidence
```

`quantity` 固定为单实体事实 `1`。同一 `partPosition` 的数量归并和制造指纹冲突检查由 Python 消费端执行。

## 输出与状态

```text
<output-directory>/
└── part-drawing-snapshots/
    ├── <safe-partPosition>-<partId>.json
    └── export-summary.json
```

单个零件状态：

- `EXPORTED`：快照完整写出。
- `SKIPPED`：选择对象不是直接 Part，或明确不在首期范围。
- `REJECTED`：对象是候选平板，但关键属性或几何不可靠。

一个零件失败不阻断其他零件。存在任意 `REJECTED` 时命令返回非零；只有 `SKIPPED` 且至少一个 `EXPORTED` 时可成功返回。

汇总至少包含选择对象数、唯一 Part 数、三类状态数量、输出文件、part id、`partPosition`、原因码和消息。不得包含异常堆栈或过量 Tekla 对象转储。

## 代码边界

实现仓库新增：

- `TeklaSectionClassifier/PartDrawingSnapshotContracts.cs`：JSON DTO。
- `TeklaSectionClassifier/PartDrawingGeometry.cs`：纯几何、环分类和质量门。
- `TeklaSectionClassifier/Tekla2017PartDrawingSnapshotExporter.cs`：Tekla 2017 选择集和模型事实适配。
- `TeklaSectionClassifier.Tests/`：纯逻辑和契约测试。

最小修改：

- `TeklaSectionClassifier.Runner/Program.cs`：新模式分流。
- `TeklaSectionClassifier.Runner/TeklaSectionClassifier.Runner.csproj`：必要引用。
- `README.md`：使用说明。

既有 `Tekla2017MemberExtractor`、`BodyBracketBundleExporter` 和 Web3D 导出流程不作为本功能入口，也不因本功能重构。

## 错误码

- `EMPTY_SELECTION`
- `NOT_A_PART`
- `UNSUPPORTED_PART_TYPE`
- `PART_POSITION_MISSING`
- `THICKNESS_UNRESOLVED`
- `LOCAL_FRAME_INVALID`
- `SOLID_UNAVAILABLE`
- `PLATE_PLANARITY_INVALID`
- `OUTER_LOOP_INVALID`
- `MULTIPLE_OUTER_LOOPS`
- `INNER_LOOP_INVALID`
- `UNSUPPORTED_CURVE_GEOMETRY`
- `SNAPSHOT_SERIALIZATION_FAILED`

错误码描述事实缺口，不围绕项目名、构件号或零件号写特例。

## Acceptance Criteria

1. 选中一个普通平板 Part 后，新命令只导出该实体，不导出所属 Assembly 的其他零件。
2. 选中多个平板实体时，每个实体生成独立 JSON；同编号文件不互相覆盖。
3. JSON 可被 Python `load_part_snapshot()` 直接读取，无需字段转换。
4. `partPosition`、材质、profile、厚度、assembly id 和局部坐标系与 Tekla 模型事实一致。
5. 直线外轮廓和内环保持有序、闭合、无自交，并正确区分 outer/inner。
6. 明确的圆孔和长圆孔输出正确中心、直径或长宽及方向。
7. 明确的轮廓圆弧输出 ARC；无法恢复圆心的曲线被拒绝，不静默折线化。
8. 非平板、折弯板和缺失关键证据的零件不产生正式快照，汇总包含稳定原因码。
9. 单零件失败不阻断其他零件；存在 REJECTED 时命令退出码非零。
10. 未传入新参数时，现有构件导出行为保持不变。
11. 生产代码和测试中不存在项目名、构件号或零件号硬编码。

## Verification Plan

### 自动测试

- DTO 序列化字段名和三维数组结构与 fixture 一致。
- 文件名清理稳定，同编号不同 part id 不冲突。
- 环闭合、方向、投影面积、outer/inner 分类和多外环拒绝。
- 退化局部坐标系、缺厚度和缺编号拒绝。
- 圆孔与长圆孔参数映射。
- 无原生圆心证据的 curved edge 拒绝。
- Runner 参数解析和默认模式不回归。

### 构建与跨语言验证

```powershell
dotnet test I:\xingcaisuanfa\TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj
dotnet build I:\xingcaisuanfa\TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj
python -m unittest tests.test_part_drawing_contracts tests.test_part_drawing_geometry tests.test_part_drawing_pipeline
```

使用 Python `load_part_snapshot()` 读取至少一个 C# 测试产物，核对 `schemaVersion`、标识、厚度、局部坐标系、外环、内环和孔槽。

### 真实 Tekla smoke

1. 在 Tekla 2017 中只选中至少一个普通平板 Part。
2. 运行新命令并检查 `export-summary.json`。
3. 用 Python `draw-parts` 消费输出目录，生成 DXF/PDF/drawing JSON。
4. 对 DXF 执行 audit，对 PDF 做页尺寸和非空读回。
5. 人工核对轮廓、孔槽、编号、材质和厚度。
6. 将命令摘要和人工结论写入 `docs/verification/2026-07-13-tekla-selected-part-snapshot-exporter.md`。

真实 Tekla 未连接或没有合适选择集时，只能声明自动测试和构建通过，不得声称真实模型闭环完成。
