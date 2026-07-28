# Tekla 零件图自动化子技能架构设计

> 参考 SolidWorks Automation Skill 的子技能结构，建立 Tekla 零件图出图的可控、可复用、可验证子技能体系。

## 背景

当前 Tekla 零件图离线架构已建立 5 个核心模块：

1. `GeometryAnalyzer` - 三维到二维投影
2. `FeatureRecognizer` - 孔槽切角识别
3. `DimensionGenerator` - 标注意图生成
4. `DimensionOptimizer` - 布局避让优化
5. `DrawingOutput` - DXF/PDF 渲染

但这些模块还缺少"子技能级别"的封装和调用约定。参考 SolidWorks 的 4 个子技能：

- `autocad-automation` - AutoCAD COM 绘图、图层、标注、导出
- `solidworks-vibecad` - 参数化规划、制造规则检查
- `solidworks-threaded-holes` - 螺纹孔建模规范
- `solidworks-fillet-chamfer-cnc` - 倒角圆角 CNC 规则

需要建立类似的子技能结构，避免 Tekla 工序图 POC 的"功能散落、规则耦合、难以复用"问题。

---

## 设计目标

1. **模块化**：每个子技能独立可测试，不依赖完整出图流程。
2. **约束驱动**：像 AutoCAD 子技能的 `engineering-patterns.md`，显式定义"什么是错误的图纸"。
3. **契约清晰**：输入/输出 DTO 有明确 schema 和验证规则。
4. **可替换**：Tekla Drawing API 和 DXF 兜底可以互换，不影响上层调用。
5. **可审查**：每个子技能输出可解释的证据和 manifest，支持人工复核。

---

## 子技能划分

### Subskill 1: `tekla-part-snapshot-exporter`

**职责**：从 Tekla 当前选择集导出零件快照，作为离线出图的输入契约。

**契约**：
- 输入：Tekla 选中的 Part 实体
- 输出：`PartDrawingSnapshot` JSON
- 包含：partPosition、thickness、solid_edges、holes、outer_loop_candidates

**目录结构**：
```
subskills/tekla-part-snapshot-exporter/
├── SKILL.md
├── exporter/
│   ├── PartDrawingSnapshotExporter.cs
│   └── PartDrawingSnapshotExporter.Tests.cs
├── schemas/
│   └── part_drawing_snapshot.schema.json
└── references/
    ├── snapshot-contract.md
    └── troubleshooting.md
```

**调用方式**：
```bash
# C# 导出器
cd I:\xingcaisuanfa
dotnet test --filter "PartDrawingSnapshotExporter"

# Python 消费
python -c "from zijinhua_tekla.adapters import load_part_snapshot; \
           snapshot = load_part_snapshot('T3-PX-317.json')"
```

**状态**：✅ 已实现，已有 C# 26 tests + Python 11 tests

---

### Subskill 2: `tekla-plate-geometry-normalizer`

**职责**：将三维 solid edges 归一化为二维平板几何，建立局部坐标系和闭合环。

**契约**：
- 输入：`PartDrawingSnapshot`
- 输出：`NormalizedPlateGeometry`
- 包含：local_frame、outer_loop、inner_loops、thickness、bounding_box

**目录结构**：
```
subskills/tekla-plate-geometry-normalizer/
├── SKILL.md
├── scripts/
│   ├── geometry_analyzer.py
│   └── test_geometry_analyzer.py
├── schemas/
│   └── normalized_plate_geometry.schema.json
└── references/
    ├── coordinate-systems.md
    ├── loop-extraction.md
    └── typical-errors.md
```

**约束规则**：
- 外轮廓必须闭合，容差 < 1mm
- 内环不得与外轮廓相交
- 厚度方向必须垂直于平板平面
- 同编号零件的几何指纹必须一致

**调用方式**：
```python
from zijinhua_tekla.subskills.geometry_normalizer import GeometryAnalyzer

analyzer = GeometryAnalyzer(tolerance_mm=0.5)
geometry = analyzer.normalize(snapshot)

assert geometry.status in ["OK", "REVIEW_REQUIRED", "REJECTED"]
assert geometry.outer_loop.is_closed
assert geometry.thickness > 0
```

**状态**：🚧 部分实现，需要抽成独立子技能

---

### Subskill 3: `tekla-feature-recognizer`

**职责**：从归一化几何识别孔、槽、切角、长圆孔等加工特征。

**契约**：
- 输入：`NormalizedPlateGeometry`
- 输出：`RecognizedFeature[]`
- 特征类型：HOLE、SLOT、CHAMFER、ARC_CUTOUT、CONTOUR_PLATE

**目录结构**：
```
subskills/tekla-feature-recognizer/
├── SKILL.md
├── scripts/
│   ├── feature_recognizer.py
│   ├── hole_recognizer.py
│   ├── slot_recognizer.py
│   └── test_feature_recognizer.py
├── schemas/
│   └── recognized_feature.schema.json
└── references/
    ├── hole-standards.md         # M3/M4/M5/M6/M8 底孔标准
    ├── slot-types.md             # 长圆孔、腰型孔、矩形槽
    ├── chamfer-detection.md      # 切角识别规则
    └── typical-ambiguities.md    # 案例：弧形切角 vs 圆孔
```

**约束规则**（参考 AutoCAD `engineering-patterns.md`）：
- 孔必须有：孔径 + 中心坐标 + 数量
- 槽必须有：槽长 + 槽宽 + 中心坐标 + 方向
- 切角必须有：边长 + 位置 + 端距
- 孔组必须有：首孔位置 + 间距 或 每孔独立坐标

**典型错误**（触发 `FEATURE_AMBIGUOUS`）：
- 只标注 `4×φ22 孔`，缺少孔中心坐标
- 长圆孔缺少长轴方向
- 切角缺少位置（四角都可能切角）
- 孔组只标间距不标首孔位置

**调用方式**：
```python
from zijinhua_tekla.subskills.feature_recognizer import FeatureRecognizer

recognizer = FeatureRecognizer()
features = recognizer.recognize(geometry)

for feature in features:
    print(f"{feature.type}: {feature.position} {feature.dimensions}")
    assert feature.positioning_complete
```

**状态**：🚧 部分实现，需要补约束检查和典型错误库

---

### Subskill 4: `tekla-dimension-intent-generator`

**职责**：生成标注意图，回答"要标什么"，不回答"放哪里"。

**契约**：
- 输入：`NormalizedPlateGeometry` + `RecognizedFeature[]`
- 输出：`DimensionIntent[]`
- Intent 类型：OVERALL_DIMENSION、HOLE_POSITION、HOLE_DIAMETER、CHAMFER_LOCATION、THICKNESS_CALLOUT、PART_MARK

**目录结构**：
```
subskills/tekla-dimension-intent-generator/
├── SKILL.md
├── scripts/
│   ├── dimension_generator.py
│   ├── intent_validator.py
│   └── test_dimension_generator.py
├── schemas/
│   └── dimension_intent.schema.json
└── references/
    ├── dimensioning-rules.md     # 必要尺寸 P0 规则
    ├── priority-levels.md        # 总尺寸 > 定位尺寸 > 孔槽规格
    ├── gb-standards.md           # 国标机械制图规范
    └── typical-incomplete.md     # 案例：螺栓孔定位不完整
```

**必要尺寸 P0 规则**（缺失则 `DIMENSION_INCOMPLETE` → `REJECTED`）：
- 外形尺寸：总长、总宽、板厚
- 孔定位：孔径 + 孔中心到基准边的两个距离
- 槽定位：槽长、槽宽 + 槽中心到基准边的距离
- 切角定位：切角边长 + 端距
- 基准边：至少明确两条相互垂直的基准边

**调用方式**：
```python
from zijinhua_tekla.subskills.dimension_generator import DimensionGenerator

generator = DimensionGenerator()
intents = generator.generate(geometry, features)

# 检查必要尺寸完整性
issues = generator.validate_completeness(intents)
assert all(i.severity != "CRITICAL" for i in issues), "缺少必要尺寸"
```

**状态**：🚧 需要新建，当前逻辑散落在出图脚本中

---

### Subskill 5: `tekla-annotation-layout-optimizer`

**职责**：布局避让，回答"放在哪里"和"是否放得下"。

**契约**：
- 输入：`DimensionIntent[]` + `ProjectionScene`
- 输出：`AnnotationLayout`
- 包含：placed_items、unplaced_items、collision_count、layout_status

**目录结构**：
```
subskills/tekla-annotation-layout-optimizer/
├── SKILL.md
├── scripts/
│   ├── layout_optimizer.py
│   ├── collision_detector.py
│   ├── hole_table_trigger.py
│   └── test_layout_optimizer.py
├── schemas/
│   └── annotation_layout.schema.json
└── references/
    ├── layout-rules.md           # 尺寸链分层、PartMark 优先级
    ├── collision-detection.md    # 文字框、引线、尺寸线碰撞检测
    ├── hole-table-trigger.md     # 孔数量 ≥ 6 时强制使用孔表
    └── typical-overflow.md       # 案例：标注密集导致 17 annotations unplaced
```

**布局约束**（触发 `LAYOUT_OVERFLOW` → `REVIEW_REQUIRED`）：
- `unplaced_intents > 0`：有标注意图无法放置
- `collision_count > 0`：存在文字或尺寸框碰撞
- 主视图被压缩到 < 图纸可用区域 50%

**孔表触发规则**（当前 `T3-PX-317` 的 17 annotations unplaced 问题）：
- 孔数量 ≥ 6
- 孔分布在 3 个以上不同坐标
- 单个视图内孔标注预计占用空间 > 主视区 30%

**调用方式**：
```python
from zijinhua_tekla.subskills.layout_optimizer import LayoutOptimizer

optimizer = LayoutOptimizer(sheet_size="A3", margins_mm={"left": 25, "others": 5})
layout = optimizer.optimize(intents, projection_scene)

assert layout.collision_count == 0, "存在标注碰撞"
assert layout.status in ["OK", "REVIEW_REQUIRED", "NEEDS_DETAIL_VIEW"]

if layout.unplaced_items:
    print(f"WARNING: {len(layout.unplaced_items)} annotations unplaced")
    print("建议：使用孔表或增加局部详图")
```

**状态**：🚧 需要新建，当前 17 annotations unplaced 未触发约束检查

---

### Subskill 6: `tekla-drawing-renderer`

**职责**：将布局好的标注渲染为 DXF/PDF/Tekla Drawing。

**契约**：
- 输入：`AnnotationLayout`
- 输出：DXF 文件 + PDF 文件 + `DrawingManifest` JSON
- Renderer 类型：DXF (ezdxf)、PDF (reportlab)、Tekla GA Drawing

**目录结构**：
```
subskills/tekla-drawing-renderer/
├── SKILL.md
├── scripts/
│   ├── dxf_renderer.py
│   ├── pdf_renderer.py
│   ├── tekla_renderer.py
│   └── test_renderers.py
├── schemas/
│   └── drawing_manifest.schema.json
└── references/
    ├── dxf-standards.md          # R2007+ TABLES/BLOCKS 结构
    ├── cad-native-dimensions.md  # 禁止用线+文字拼凑尺寸
    ├── gb-layers.md              # 国标图层线型规范
    └── tekla-ga-limits.md        # Tekla Drawing API 的已知限制
```

**图层线型规范**（国标 GB）：
- 粗实线 (0.5mm)：外轮廓、主要可见边
- 细实线 (0.25mm)：尺寸线、尺寸界线、引出线
- 中心线 (0.25mm 点划线)：孔中心、对称轴
- 虚线 (0.25mm)：不可见边、辅助线

**调用方式**：
```python
from zijinhua_tekla.subskills.drawing_renderer import DxfRenderer, PdfRenderer

dxf_renderer = DxfRenderer()
dxf_path = dxf_renderer.render(layout, output_path="T3-PX-317.dxf")

pdf_renderer = PdfRenderer()
pdf_path = pdf_renderer.render(layout, output_path="T3-PX-317.pdf")

# 验证输出
manifest = dxf_renderer.get_manifest()
assert manifest["entity_count"] > 0
assert manifest["audit"]["errors"] == 0
```

**状态**：✅ DXF renderer 已实现（ezdxf），PDF 待补，Tekla GA 待升级

---

## 子技能调用流程

### 完整出图流程

```python
from zijinhua_tekla.subskills import (
    load_part_snapshot,               # Subskill 1
    GeometryAnalyzer,                 # Subskill 2
    FeatureRecognizer,                # Subskill 3
    DimensionGenerator,               # Subskill 4
    LayoutOptimizer,                  # Subskill 5
    DxfRenderer, PdfRenderer          # Subskill 6
)

# 1. 加载快照
snapshot = load_part_snapshot("T3-PX-317.json")

# 2. 归一化几何
analyzer = GeometryAnalyzer()
geometry = analyzer.normalize(snapshot)
if geometry.status == "REJECTED":
    raise ValueError(f"几何无效: {geometry.issues}")

# 3. 识别特征
recognizer = FeatureRecognizer()
features = recognizer.recognize(geometry)

# 4. 生成标注意图
generator = DimensionGenerator()
intents = generator.generate(geometry, features)
issues = generator.validate_completeness(intents)
if any(i.severity == "CRITICAL" for i in issues):
    raise ValueError(f"缺少必要尺寸: {issues}")

# 5. 布局优化
optimizer = LayoutOptimizer(sheet_size="A3")
layout = optimizer.optimize(intents, geometry.projection_scene)
if layout.collision_count > 0:
    print(f"WARNING: {layout.collision_count} 标注碰撞")
if layout.unplaced_items:
    print(f"WARNING: {len(layout.unplaced_items)} 标注未放置")

# 6. 渲染输出
dxf_renderer = DxfRenderer()
dxf_path = dxf_renderer.render(layout, "T3-PX-317.dxf")
pdf_renderer = PdfRenderer()
pdf_path = pdf_renderer.render(layout, "T3-PX-317.pdf")

print(f"✅ 出图完成: {dxf_path}, {pdf_path}")
print(f"状态: {layout.status}")
```

### 单独调试子技能

```python
# 只测试特征识别
from zijinhua_tekla.subskills import load_part_snapshot, GeometryAnalyzer, FeatureRecognizer

snapshot = load_part_snapshot("T3-PX-317.json")
geometry = GeometryAnalyzer().normalize(snapshot)
features = FeatureRecognizer().recognize(geometry)

for f in features:
    print(f"{f.type}: {f.dimensions} @ {f.position}")
```

---

## 与 SolidWorks 子技能的对应关系

| SolidWorks Subskill | Tekla 对应子技能 | 共同模式 |
|---------------------|------------------|----------|
| `autocad-automation` | `tekla-drawing-renderer` | COM/ActiveX 绘图、图层、标注、导出 |
| `solidworks-vibecad` | `tekla-dimension-intent-generator` | 参数化规划、制造规则检查 |
| `solidworks-threaded-holes` | `tekla-feature-recognizer` | 孔槽规格、定位约束、典型错误 |
| `solidworks-fillet-chamfer-cnc` | `tekla-plate-geometry-normalizer` | 几何归一化、容差控制、质量门 |

**核心相似点**：
1. **约束驱动**：像 AutoCAD `engineering-patterns.md`，显式定义"什么是不可接受的输出"
2. **典型错误库**：每个子技能有 `typical-errors.md`，沉淀案例和归因
3. **可独立测试**：每个子技能有独立测试，不依赖完整流程
4. **契约清晰**：输入/输出 DTO 有 schema 和验证规则
5. **可替换渲染器**：DXF/PDF/Tekla GA 互换，不影响上层调用

---

## 实施路径

### Phase 1: 建立子技能目录结构（1 天）

```bash
mkdir -p I:\zijinhuatekla\subskills/{tekla-part-snapshot-exporter,tekla-plate-geometry-normalizer,tekla-feature-recognizer,tekla-dimension-intent-generator,tekla-annotation-layout-optimizer,tekla-drawing-renderer}

# 每个子技能创建 SKILL.md + schemas/ + references/
```

### Phase 2: 抽取现有模块到子技能（2-3 天）

- `GeometryAnalyzer` → `tekla-plate-geometry-normalizer`
- `FeatureRecognizer` → `tekla-feature-recognizer`
- `DxfRenderer` → `tekla-drawing-renderer`

### Phase 3: 补齐缺失子技能（3-5 天）

- 新建 `tekla-dimension-intent-generator`
- 新建 `tekla-annotation-layout-optimizer`
- 补齐约束检查和典型错误库

### Phase 4: 修复 T3-PX-317 的 17 annotations unplaced（1 天）

- 在 `tekla-annotation-layout-optimizer` 实现孔表触发逻辑
- 触发条件：孔数量 ≥ 6
- 输出 `NEEDS_HOLE_TABLE` 状态

### Phase 5: 建立回归测试（2 天）

- 将 `tekla-part-drawing-annotation-constraints.md` 的案例 1-6 转化为单元测试
- 每个子技能至少 10 个测试用例

---

## 预期收益

1. **可控性**：每个子技能独立可测试，不会像工序图 POC 一样"功能散落、难以定位问题"
2. **复用性**：`DimensionGenerator` 可以同时被零件图和工序图复用
3. **可维护性**：约束规则和典型错误集中管理，不散落在代码注释中
4. **可审查性**：每个子技能输出 manifest 和证据，支持人工复核
5. **可替换性**：DXF/PDF/Tekla GA renderer 互换，不影响上层调用

---

## 参考文档

- SolidWorks AutoCAD 子技能：`I:\cadstudio\solidworks-automation-skill-main\subskills\autocad-automation\SKILL.md`
- AutoCAD 工程实践：`I:\cadstudio\solidworks-automation-skill-main\subskills\autocad-automation\references\engineering-patterns.md`
- Tekla 零件图离线架构：`I:\zijinhuatekla\docs\design\2026-07-13-part-drawing-offline-architecture.md`
- Tekla 标注约束：`I:\zijinhuatekla\docs\references\tekla-part-drawing-annotation-constraints.md`
