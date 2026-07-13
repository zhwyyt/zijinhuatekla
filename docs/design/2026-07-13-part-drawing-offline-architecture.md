# 平板零件离线出图架构设计

## 文档状态

- 日期：2026-07-13
- 状态：已确认设计
- 第一阶段范围：平板零件、离线快照输入、独立 DXF/PDF 输出
- 核心决策：先稳定零件图底座，再升级构件工序图

## 背景

当前项目已经验证 BOX 构件步骤规划、Tekla solid 真实投影、DXF 输出和标注避让，但直接生成构件工序图同时耦合以下问题：

- 零件几何是否完整、可靠。
- 孔、切割、圆弧等加工特征是否被正确理解。
- 单个零件的必要加工尺寸是否完整。
- 多零件装配顺序、翻身面和焊接阶段是否正确。
- 累计视图、剖面、PartMark 和尺寸能否稳定排版。

任何一层不稳定都会影响整张构件图。第一阶段因此收敛为“可人工复核的平板零件加工图”：先完成单个零件的几何、特征、尺寸、布局和输出闭环，再把这些能力作为构件图基础设施。

## 目标

1. 从 Tekla 导出的标准离线快照生成独立 DXF 和 PDF 零件图。
2. 第一阶段支持平板件的任意外轮廓、内孔、开槽、切角和圆弧。
3. 同一 `partPosition`、同一几何版本的实体合并为一套图纸，并在标题栏记录数量。
4. DXF 和 PDF 使用同一份格式无关图纸模型，避免形成两套几何和标注规则。
5. 任何不确定性必须进入质量门，禁止通过猜测补齐加工语义。
6. 几何、特征、标注和布局能力可以在后续构件图中复用。

## 非目标

- 第一阶段不支持折弯板展开、卷板、H/BH/BOX 型材、圆管和复杂空间零件。
- 第一阶段不承诺图纸无需审核即可直接下发生产。
- 第一阶段不自动推断缺少明确证据的坡口、加工余量、公差和表面处理。
- 第一阶段不生成构件装配顺序、焊接顺序或翻身工序图。
- 第一阶段不依赖 Tekla 在线运行，也不生成 Tekla 原生零件图。
- 第一阶段不以几何相似替代 `partPosition`，也不自动修改零件编号。

## 核心原则

### 事实与表达分离

Tekla 导出器只负责提供模型事实；离线引擎负责理解几何、生成尺寸和排版；renderer 只负责将最终图纸模型写成目标格式。

### 单一图纸真相

DXF 和 PDF 必须由同一个 `PartDrawingDocument` 生成。任何 renderer 都不得重新识别特征、选择尺寸或修改业务文字。

### 证据不足不猜测

只允许执行不改变工程语义的机械修复，例如容差内首尾闭合、重复点去除和数值取整。不得自动填补缺边、猜测坡口或把不同几何的同编号零件合并。

### 审核状态不等于生产放行

`OK` 只表示自动识别和图面布局完整，可以进入人工审核；生产放行属于系统外的人工流程。

## 总体架构

```text
Tekla Exporter
    ↓
PartDrawingSnapshot
    ↓
SnapshotInput / Data Quality Gate
    ↓
PartDimensionEngine
    ├── GeometryAnalyzer
    ├── FeatureRecognizer
    ├── DimensionGenerator
    ├── DimensionOptimizer
    └── DrawingDocumentBuilder
    ↓
PartDrawingDocument
    ├── DxfRenderer
    ├── PdfRenderer
    └── QualityManifest
```

五个核心模块构成 `PartDimensionEngine`。`SnapshotInput`、质量门、pipeline 和输出 renderer 是外围系统边界，不改变核心算法架构。

## 系统边界

### Tekla Exporter

负责：

- 提取零件标识、编号、名称、材质、profile 和厚度。
- 提取板件坐标系、solid 边、轮廓段、孔、切割、fitting 等事实。
- 输出契约版本、导出器版本、模型标识和证据来源。

不负责：

- 选择最佳视图。
- 判断应该标哪些尺寸。
- 决定尺寸和文字在图面上的位置。
- 生成 DXF/PDF。

### 离线出图系统

负责：

- 校验快照完整性和同编号一致性。
- 将三维事实归一化为二维平板几何。
- 识别加工特征并生成可解释的标注意图。
- 完成布局、碰撞检查、DXF/PDF 输出和验证清单。

## 输入契约

`PartDrawingSnapshot` 是导出器和离线出图系统之间的唯一正式接口。

```text
identity
- part_id
- part_position
- assembly_id
- name
- profile
- material
- quantity

plate_properties
- thickness
- model_coordinate_system
- plate_local_frame
- normal_direction

geometry
- solid_edges
- outer_loop_candidates
- inner_loop_candidates
- line_segments
- arc_segments

operations
- holes
- cuts
- fittings
- contour_plates

provenance
- schema_version
- exporter_version
- model_identifier
- exported_at
- source_evidence
```

关键字段缺失时的处理规则：

- 缺少 `part_position`、厚度或可用几何：`REJECTED`。
- 缺少可靠局部坐标系，但能从单一平面轮廓稳定派生：允许派生并记录证据码。
- 无法证明零件为单一平板：`REJECTED`，不进入第一阶段出图。
- 缺少非必要属性：允许出审核图，同时记录 `REVIEW_REQUIRED`。

## 内部数据契约

```text
PartDrawingSnapshot
→ NormalizedPlateGeometry
→ RecognizedFeature[]
→ DimensionIntent[]
→ AnnotationLayout
→ PartDrawingDocument
→ DXF / PDF / DrawingManifest
```

### NormalizedPlateGeometry

包含：

- 统一后的二维局部坐标系。
- 一个闭合外轮廓和零个或多个闭合内环。
- 保留语义的直线、圆弧和圆段。
- 板厚、包围尺寸、面积和周长。
- 原始实体到二维图元的证据映射。
- 几何指纹和使用的容差版本。

默认容差：

- 坐标数值去噪：`0.01 mm`。
- 同编号几何比较：`0.1 mm`。
- 角度比较：`0.05°`。
- 厚度比较：`0.01 mm`。

所有实际使用的容差必须写入 `DrawingManifest`，后续调整必须通过版本化配置和回归案例完成。

### RecognizedFeature

每个特征至少包含：

- `feature_id`
- `feature_type`
- 几何参数和局部坐标
- 来源实体或操作 id
- `evidence_codes`
- `confidence`
- `review_reason`

第一阶段特征类型：

- 圆孔和规则孔组。
- 长圆孔。
- 多边形内孔或内切口。
- 外轮廓切角和缺口。
- 圆角和圆弧缺口。
- 显式坡口证据；没有明确证据时不自动识别坡口。

### DimensionIntent

只描述“标什么”，不包含最终图面位置：

- 尺寸类型和优先级。
- 模型真实值和格式化文字。
- 起止基准或目标锚点。
- 关联特征和零件 id。
- 证据码、是否允许合并及失败策略。

### AnnotationLayout

包含：

- 已放置的尺寸线、延长线、文字和引出线。
- 未放置意图及原因。
- 文字框、轮廓框和标题栏等障碍物。
- 碰撞数量和布局状态。

### PartDrawingDocument

是 DXF/PDF 的共同输入，包含：

- 页面尺寸、单位、比例和坐标映射。
- 主视轮廓、内环、中心线和中心标记。
- 尺寸、引出说明和审核警告。
- 标题栏字段和图纸状态。
- 图元到来源特征的追溯标识。

renderer 不得在此阶段增加或删除业务尺寸。

## 同编号归并规则

1. 按 `partPosition` 分组。
2. 对组内每个实体执行平移、旋转和轮廓起点无关的几何归一化。
3. 比较外轮廓、内环、孔槽、厚度和加工操作。
4. 几何一致时选择一个代表实体生成图纸，标题栏数量取组内实体数量。
5. 同编号存在超过容差的任何几何或厚度差异时，整组状态为 `PART_POSITION_CONFLICT`。
6. 冲突组不得生成标记为正式的 DXF/PDF，只生成冲突清单和证据 JSON。

几何相似只能用于人工复核，不得跨 `partPosition` 自动合并。

## 五个核心模块

### 1. GeometryAnalyzer

职责：把 Tekla 三维板件事实转换为稳定的二维加工几何。

- 校验板厚方向、局部坐标系和平面性。
- 将轮廓投影到板件局部 XY 平面。
- 重建一个外轮廓和零个或多个内环。
- 保留直线、圆弧和圆，不优先离散成短线段。
- 统一轮廓方向、起点和坐标原点。
- 计算长、宽、厚度、面积、周长和几何指纹。
- 检测开环、自交、重复边、极短边和多个不相连外轮廓。

输出 `NormalizedPlateGeometry`，不做特征命名、尺寸或排版决策。

### 2. FeatureRecognizer

职责：从标准几何和 Tekla 操作证据中识别加工语义。

- 圆孔的直径、中心和来源。
- 孔组的数量、方向和重复间距。
- 长圆孔的长度、宽度和方向。
- 多边形内孔、内切口和外轮廓缺口。
- 切角、圆角和圆弧缺口。
- 显式导出的坡口证据。

不能可靠解释的几何保留为普通轮廓，并输出 `FEATURE_AMBIGUOUS`，不得根据单个项目或零件号添加特例。

### 3. DimensionGenerator

职责：生成格式无关的加工标注意图。

尺寸优先级：

1. 必要尺寸：总长、总宽、板厚。
2. 加工尺寸：孔径、孔中心定位、槽长宽、切角、缺口和圆弧半径。
3. 辅助尺寸：重复间距、对称关系和数量说明。
4. 参考信息：面积、重量和加工提示，不进入关键尺寸链。

默认规则：

- 以板件局部左下基准边作为定位基准。
- 总尺寸位于尺寸链最外层。
- 孔和内部特征优先采用共同基准的坐标尺寸。
- 规则孔组合并为首孔位置、间距和数量表达。
- 不生成可由其他尺寸完全推导的重复尺寸。
- 不形成冗余闭合尺寸链。
- 无法完整标注的特征进入 `DIMENSION_INCOMPLETE`。

### 4. DimensionOptimizer

职责：将尺寸和说明放入有限图面并验证可读性。

- 图面划分为主视区、上下尺寸区、左右标注区和标题栏区。
- 按优先级从高到低放置。
- 同方向尺寸自动分层并保持稳定层距。
- PartMark 和特征说明从有限候选位置中选择碰撞成本最低的位置。
- 检测文字、尺寸线、引出线、轮廓和标题栏碰撞。
- 放不下时输出 `NEEDS_DETAIL_VIEW` 或 `REVIEW_REQUIRED`，不无限缩小文字或允许重叠。

### 5. DrawingOutput

职责：把 `PartDrawingDocument` 写成目标格式，不再解释几何和尺寸语义。

DXF renderer：

- 使用 `ezdxf` 生成规范 DXF。
- 输出后必须执行 `ezdxf.audit()`。
- 使用稳定图层：`PART_CONTOUR`、`PART_INNER`、`PART_CENTER`、`DIMENSION`、`ANNOTATION`、`TITLE_BLOCK`、`REVIEW`。

PDF renderer：

- 直接生成矢量 PDF，不依赖外部 CAD 程序将 DXF 转 PDF。
- 与 DXF 使用相同的页面、比例、图元和文字内容。
- 中文文字使用可嵌入的 CJK TrueType 字体；字体不可用时该批次 PDF 输出失败并明确报告，不静默替换为乱码字体。

## 图纸内容

第一阶段每套图纸默认包含：

- 一个平板主视图。
- 外轮廓、内孔、开槽、切角和圆弧。
- 必要的中心线和中心标记。
- 总长、总宽和板厚。
- 孔槽、切口、切角和圆弧加工尺寸。
- 零件号、名称、材质、profile 和数量。
- 比例、单位、快照版本和自动出图状态。
- 数据不足或需要人工复核的醒目标记。

单位统一为毫米。图纸比例根据可用主视区自动选择标准比例，实际加工尺寸始终来自模型值，不从缩放后图面反算。

## 处理流程

```text
读取快照
→ 按 partPosition 分组
→ 契约校验
→ 几何归一化和同编号一致性检查
→ 选择代表实体
→ 特征识别
→ 尺寸意图生成
→ 标注布局和避让
→ 构建 PartDrawingDocument
→ 分别渲染 DXF/PDF
→ 读回验证
→ 输出 DrawingManifest 和批次摘要
```

建议命令入口：

```powershell
python -m zijinhua_tekla.cli draw-parts --snapshot-root <snapshot-directory> --out <output-directory>
```

批量任务以 `partPosition` 为隔离单元。单个零件失败不得阻断其他零件，但命令最终必须返回非零状态并在批次摘要中列出失败项。

## 输出结构

```text
<output-directory>/
├── parts/
│   └── <safe-part-position>/
│       ├── <safe-part-position>.dxf
│       ├── <safe-part-position>.pdf
│       └── <safe-part-position>.drawing.json
├── conflicts/
│   └── <safe-part-position>.conflict.json
└── part-drawing-batch-summary.json
```

文件名中的非法路径字符必须以稳定规则替换，但 `drawing.json` 和标题栏始终保留原始 `partPosition`。

## 状态与错误分类

### 输出状态

- `OK`：自动识别和布局完整，可以进入人工审核。
- `REVIEW_REQUIRED`：图纸已生成，但存在未识别特征、未放置标注或证据不足。
- `REJECTED`：输入冲突或基础几何不可靠，只输出错误证据，不生成 DXF/PDF。

### 问题码

- `SNAPSHOT_INVALID`
- `PART_POSITION_CONFLICT`
- `GEOMETRY_INVALID`
- `FEATURE_AMBIGUOUS`
- `DIMENSION_INCOMPLETE`
- `LAYOUT_OVERFLOW`
- `NEEDS_DETAIL_VIEW`
- `RENDER_FAILED`

每个问题必须记录所属阶段、关联 part id、证据字段、建议动作和是否阻断输出。

## 建议代码结构

```text
src/zijinhua_tekla/part_drawing/
├── contracts.py
├── geometry_analyzer.py
├── feature_recognizer.py
├── dimension_generator.py
├── dimension_optimizer.py
├── drawing_output.py
├── quality.py
└── pipeline.py
```

现有 `reports/annotation_layout.py` 中通用的标注意图和碰撞检测能力可以通过小范围抽取或适配复用。第一阶段不为复用而重写现有构件图 POC，也不把 C# Tekla 探测代码迁入离线零件图核心。

## 升级到构件图

零件图阶段完成后，构件图可以直接复用：

- 标准几何和真实投影。
- 孔、槽、切角和圆弧语义。
- 尺寸意图规则。
- 标注布局和碰撞检查。
- DXF/PDF renderer。
- 质量门、审核状态和验证清单。

构件图仍需独立解决：

- 零件之间的焊接、接触、螺栓和空间关系。
- 装配顺序、翻身面和焊接阶段。
- 多零件累计视图。
- 构件级定位尺寸、剖面和局部详图。

因此零件图是构件图的稳定基础，但不会替代构件级工艺规划。

## 风险与取舍

### Tekla 快照字段不足

如果当前导出数据不能重建可靠轮廓、圆弧或孔切操作，必须先升级快照契约和导出器，禁止在 Python 侧根据不完整边集合猜测加工特征。

### 相同几何的数值噪声

通过版本化容差和归一化几何指纹解决。容差不得扩大到可能合并真实不同零件的程度。

### PDF 中文字体

PDF 输出必须嵌入明确配置的 CJK 字体。部署检查需要在批量出图前验证字体存在和可嵌入性。

### 自动尺寸不完整

第一阶段优先保证必要尺寸正确和可解释，不追求一次覆盖所有车间标注习惯。缺失特征进入审核状态，不通过追加零件号特例解决。

## Acceptance Criteria

1. 给定合法的矩形平板快照，系统能生成包含外轮廓、总长、总宽、板厚和标题栏的 DXF、PDF、drawing JSON。
2. 给定带圆孔、规则孔组、长圆孔、切角、内切口和圆弧的回归快照，图纸能表达对应几何和必要加工尺寸。
3. DXF 和 PDF 来自同一 `PartDrawingDocument`，图元语义和标注文字一致。
4. 同一 `partPosition` 的平移或旋转等价实体合并为一套图纸并记录正确数量。
5. 同一 `partPosition` 存在超过容差的轮廓、孔槽或厚度差异时，整组被标记为 `PART_POSITION_CONFLICT`，只输出冲突证据，不生成 DXF/PDF。
6. 开环、自交、多外轮廓或无法证明为平板的输入被标记为 `GEOMETRY_INVALID` 或 `REJECTED`。
7. 证据不足的坡口或复杂加工特征不会被自动猜测，图纸和 manifest 明确显示 `REVIEW_REQUIRED`。
8. 布局结果不存在未报告的文字或尺寸碰撞；无法放置时返回 `LAYOUT_OVERFLOW` 或 `NEEDS_DETAIL_VIEW`。
9. DXF 通过 `ezdxf.audit()`，PDF 非空、页面边界正确且关键文字可读。
10. 每个输出都能通过 manifest 追溯到快照版本、几何指纹、规则版本、容差和问题码。
11. 批量任务中单个零件失败不会阻断其他零件，批次摘要准确报告各状态数量并以非零退出码表示存在失败。
12. 生产代码和测试中不存在围绕单个项目名、构件号或零件号的硬编码判定。

## Verification Plan

### 单元测试

新增最小快照 fixture，覆盖：

- 普通矩形板。
- 带切角板。
- 带圆弧外轮廓板。
- 单孔和规则孔组。
- 长圆孔。
- 多边形内切口。
- 同编号旋转、平移等价实体。
- 同编号几何冲突。
- 开环、自交和多外轮廓。
- 标注密集并触发人工复核。

重点断言：

- 几何归一化的平移、旋转和轮廓起点不变性。
- 特征类型、数量、参数和证据码。
- 必要尺寸完整性及无冗余闭合尺寸链。
- 标注碰撞数、未放置项和布局状态。
- `PartDrawingDocument` 可序列化且不含 renderer 专用业务规则。

### 输出测试

- 对生成的 DXF 执行 `ezdxf.audit()`，要求无错误。
- 读回 DXF，核对关键图层、实体数量、轮廓边界和文字。
- 读回 PDF，核对页数、MediaBox、非空矢量内容和关键文字。
- 对同一 `PartDrawingDocument` 的 DXF/PDF 输出比较图元统计和标注文字集合。
- 验证非法文件名替换稳定，标题栏仍保留原始编号。

### Pipeline 测试

- 验证按 `partPosition` 分组、数量汇总和代表实体选择。
- 验证 `OK / REVIEW_REQUIRED / REJECTED` 状态传播。
- 验证单零件失败隔离、批次摘要和退出码。
- 验证冲突组只输出冲突证据，不输出正式图纸。

### 最小命令验证

```powershell
python -m unittest tests.test_part_drawing_geometry
python -m unittest tests.test_part_drawing_features
python -m unittest tests.test_part_drawing_dimensions
python -m unittest tests.test_part_drawing_output
python -m unittest tests.test_part_drawing_pipeline
python -m unittest discover -s tests
```

### 人工验收

从至少一个真实 Tekla 模型导出一组平板零件快照，抽查：

- 外轮廓、孔槽、切角和圆弧是否与模型一致。
- 加工尺寸是否完整、无歧义且不形成错误闭合链。
- 零件号、材质、厚度和数量是否正确。
- DXF 在目标 CAD 中可正常打开、量测和编辑。
- PDF 中文、线型、比例和标题栏是否可读。
- 所有不确定特征是否被显式标记，没有静默猜测。

真实 smoke 的命令、输入摘要、输出统计和人工结论写入 `docs/verification/YYYY-MM-DD-part-drawing-offline-smoke.md`，不在聊天中粘贴完整输出。
