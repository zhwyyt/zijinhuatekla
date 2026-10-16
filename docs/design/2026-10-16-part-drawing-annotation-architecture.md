# 零件图自动化标注架构设计

**文档状态**：草稿  
**创建日期**：2026-10-16  
**适用分支**：`codex/offline-part-drawing-engine`  
**关联文档**：`2026-07-13-part-drawing-offline-architecture.md`、`2026-07-14-part-drawing-v2-geometry-evidence-and-annotations.md`

---

## 1. 问题陈述

在 Tekla 深化模型基础上对零件进行自动化标注，需满足四条硬约束：

1. **不遗漏、不重复** — 每个几何特征有且仅有一组对应标注。
2. **剖面按需** — 主视图无法清晰表达的特征必须生成剖面或详图；能表达清楚的不多做。
3. **标注无重叠** — 标注在图面上排布合理，不产生遮挡或混乱。
4. **零件无自由度** — 标注集合必须能唯一确定零件几何，不产生歧义。

这是一个**约束求解 + 可验证性**问题，而不仅是生成问题。

---

## 2. 现有架构分析

### 2.1 当前 Pipeline

```
Snapshot
  → GeometryAnalyzer
  → FeatureRecognizer
  → DimensionGenerator
  → DimensionPlanner
  → DimensionOptimizer
  → DrawingDocument
  → DXF / PDF Renderer
```

### 2.2 已有优点

- 事实与表达分离（几何证据层与标注层独立）
- 单一图纸真相（DXF/PDF 来自同一 Document 对象）
- 证据不足不猜测（质量门阻断而非降级输出）
- 问题码可追溯

### 2.3 当前能力边界

**已实现**：
- 平板零件几何归一化
- 圆孔识别及孔组处理
- 原生 CAD 标注（`DIMENSION`、`MULTILEADER`）
- 基本碰撞检查（`DimensionOptimizer`）

**质量门阻断**：
- 折弯板、曲面板、型材 → `PART_FORM_UNSUPPORTED_FOR_DRAWING`
- 缺坡口证据 → 不猜测

### 2.4 核心差距

`DimensionGenerator` 是规则驱动的生成器，无法回答"标注是否完备"以及"是否需要剖面"。

---

## 3. 目标架构

### 3.1 设计原则

- 约束声明式：描述"需要什么"，而不是"如何标注"
- 完备性可验证：系统能量化"还差哪些约束未满足"
- 视图按需生成：由可表达性判定驱动，不预设剖面数量
- 保持质量门哲学：不确定的进 REVIEW，不猜测

### 3.2 新 Pipeline

```
几何 + 加工语义（Snapshot）
  → DOFAnalyzer           # 自由度分析
  → ConstraintGenerator   # 约束集生成
  → ConstraintSolver      # 约束满足规划（尺寸方案）
  → CompletenessVerifier  # 完备性验证
  → ExpressibilityChecker # 可表达性判定
  → ViewPlanner           # 视图决策（剖面 / 详图）
  → LayoutSolver          # 布局求解
  → DrawingDocument
  → DXF / PDF Renderer
```

---

## 4. 模块设计

### 4.1 自由度分析器（DOFAnalyzer）

**职责**：量化零件的几何自由度，生成需要被标注满足的约束清单。

```python
@dataclass(frozen=True)
class DOFConstraint:
    constraint_id: str
    constraint_type: ConstraintType
    # ConstraintType: POSITION_X | POSITION_Y | ROTATION |
    #                 DIMENSION_LENGTH | DIMENSION_DIAMETER | ...
    required_evidence: tuple[str, ...]  # 需要哪些尺寸或基准
    satisfied_by: tuple[str, ...] | None  # 由哪些标注满足（规划后填入）
    confidence: float

@dataclass(frozen=True)
class DOFAnalysisResult:
    total_dof: int           # 理论自由度（平板通常 X/Y/θ = 3）
    dimension_dof: int       # 几何尺寸自由度（长/宽/孔径/孔位置等）
    constraints: tuple[DOFConstraint, ...]
    unconstrained: tuple[DOFConstraint, ...]  # 分析时已知无法满足的约束
```

**平板零件约束模型**：

| 特征 | 需要满足的约束 |
|------|----------------|
| 矩形外轮廓 | 长、宽、板厚 |
| 单孔 | 直径 d、位置 (x, y) |
| 孔组 | 直径 d、基准位置、行/列间距、行/列数 |
| 切角 | 切角位置、两边长度 |
| 槽 | 起点、长度、宽度、方向 |
| 坡口 | 角度、深度（需剖面） |

### 4.2 约束生成器（ConstraintGenerator）

**职责**：从几何分析结果和识别特征生成完整约束集合。

```python
def generate_constraints(
    geometry: NormalizedPlateGeometry,
    features: tuple[RecognizedFeature, ...]
) -> tuple[DOFConstraint, ...]:
    """
    按特征类型生成必要约束：
    - 外轮廓约束
    - 孔 / 槽约束
    - 特征间关系约束（对称、重复阵列、同心）
    """
```

约束是声明式的，与后续"如何标注"解耦。

### 4.3 约束满足规划器（ConstraintSolver）

**职责**：为每个约束选择最优标注方式，生成尺寸方案。

```python
def solve_constraints(
    constraints: tuple[DOFConstraint, ...],
    geometry: NormalizedPlateGeometry,
    features: tuple[RecognizedFeature, ...]
) -> DimensionSolution:
    """
    选择策略：
    - 优先使用共同基准（减少累积误差）
    - 合并可合并的重复尺寸（孔组间距代替独立位置）
    - 检测冗余闭合链
    - 输出最小完备尺寸集
    """
```

### 4.4 完备性验证器（CompletenessVerifier）

**职责**：验证尺寸方案是否覆盖全部约束；未满足的阻断输出。

```python
def verify_completeness(
    solution: DimensionSolution,
    constraints: tuple[DOFConstraint, ...]
) -> CompletenessReport:
    """
    返回：
    - satisfied: 已满足约束列表
    - missing: 未满足约束列表 → 触发 DIMENSION_INCOMPLETE
    - redundant: 过度约束（冗余尺寸，可优化但不阻断）
    """

def is_fully_constrained(
    geometry: NormalizedPlateGeometry,
    solution: DimensionSolution
) -> bool:
    """
    必要条件：
    1. 外形尺寸完整（长、宽、厚）
    2. 每个孔的位置和尺寸被唯一确定
    3. 每个切角/槽的几何被唯一确定
    4. 没有形成闭合冗余尺寸链
    """
```

### 4.5 可表达性判定器（ExpressibilityChecker）

**职责**：判断每个标注意图在当前视图下是否能清晰表达。

```python
@dataclass(frozen=True)
class ExpressibilityIssue:
    feature_id: str
    issue_type: ExpressibilityIssueType
    # HIDDEN | OVERLAPPED | FORESHORTENED | AMBIGUOUS | DENSITY_TOO_HIGH
    recommended_action: str
    # "ADD_SECTION_VIEW" | "ADD_DETAIL_VIEW" | "ROTATE_VIEW"
    evidence: dict[str, object]

def check_expressibility(
    dimensions: tuple[DimensionIntent, ...],
    view: ViewDefinition,
    geometry: NormalizedPlateGeometry
) -> tuple[ExpressibilityIssue, ...]:
    """
    问题类型：
    - 特征被遮挡（需要剖面）
    - 尺寸链过长（需要局部详图）
    - 投影失真（需要换视角）
    - 标注密集（需要分视图）
    """
```

### 4.6 视图决策器（ViewPlanner）

**职责**：根据可表达性问题决策是否生成额外视图。

```python
@dataclass(frozen=True)
class ViewPlan:
    main_view: ViewDefinition
    sections: tuple[SectionView, ...]     # A-A、B-B 等剖面
    details: tuple[DetailView, ...]       # 局部放大详图
    auxiliary_views: tuple[ViewDefinition, ...]

def plan_views(
    geometry: NormalizedPlateGeometry,
    features: tuple[RecognizedFeature, ...],
    expressibility_issues: tuple[ExpressibilityIssue, ...]
) -> ViewPlan:
    ...

def needs_section_view(
    feature: RecognizedFeature,
    view: ViewDefinition,
    plate_thickness: float
) -> bool:
    if feature.feature_type == FeatureType.ROUND_HOLE:
        if feature.depth < plate_thickness:   # 沉孔
            return True
        if is_hidden_in_view(feature, view):  # 被遮挡
            return True
    return False
```

**剖面触发条件**：

| 条件 | 处理 |
|------|------|
| 通孔在主视图被遮挡 | A-A 剖面 |
| 沉孔 / 阶梯孔（深度信息丢失） | 剖面 |
| 内腔复杂（多层板、夹层） | 剖面 |
| 坡口角度 | 剖面 |
| 平板 + 贯通孔 + 主视图可见 | **不做剖面** |
| 切角、外轮廓 | **不做剖面** |

**详图触发条件**：
- 局部区域标注数量超过阈值
- 标注文字在当前比例下小于最小可读尺寸
- 特征尺寸小于板面积的 5% 但需要精细标注

### 4.7 布局求解器（LayoutSolver）

**职责**：在视图空间内无重叠地排布所有标注。

```python
def solve_layout(
    annotations: tuple[AnnotationIntent, ...],
    view_bounds: Rect,
    obstacles: tuple[Obstacle, ...],
    priority: dict[str, int]
) -> LayoutSolution:
    """
    目标函数：
      minimize: collision_penalty + readability_penalty + priority_penalty

    约束：
    - 尺寸线不与轮廓重叠
    - 文字不与文字重叠
    - 尺寸链按层级排布（总长在外、分段在内）
    - 引出线长度合理
    - 标注在视图可见区域内
    """
```

**算法选择**：

| 策略 | 特点 | 适用场景 |
|------|------|----------|
| 贪心（当前） | 快速，可能次优 | 稀疏标注 |
| 模拟退火 / 遗传算法 | 质量好，较慢 | 密集标注 |
| 混合策略 | 先贪心，遇冲突局部优化 | 推荐默认 |

---

## 5. 与现有代码对接

`dimension_planner.py` 中的 `plan_dimensions` 升级为编排入口：

```python
def plan_dimensions(
    geometry: NormalizedPlateGeometry,
    features: tuple[RecognizedFeature, ...]
) -> DimensionPlan:

    # 1. 生成约束集合
    constraints = generate_constraints(geometry, features)

    # 2. 规划尺寸方案（约束满足）
    dimension_solution = solve_constraints(constraints, geometry, features)

    # 3. 验证完备性 — 未满足约束阻断输出
    completeness = verify_completeness(dimension_solution, constraints)
    if completeness.missing:
        return DimensionPlan(
            status=DrawingStatus.DIMENSION_INCOMPLETE,
            issues=completeness.missing,
        )

    # 4. 检查可表达性
    expressibility = check_expressibility(
        dimension_solution.intents, main_view, geometry
    )

    # 5. 决策视图（剖面 / 详图）
    view_plan = plan_views(geometry, features, expressibility.issues)

    # 6. 布局求解
    layout = solve_layout(
        dimension_solution.intents + view_plan.additional_annotations,
        view_bounds=main_view.bounds,
        obstacles=geometry.outline_obstacles,
        priority=DEFAULT_ANNOTATION_PRIORITY,
    )

    return DimensionPlan(
        chains=dimension_solution.chains,
        callouts=dimension_solution.callouts,
        sections=view_plan.sections,
        details=view_plan.details,
        layout=layout,
        completeness_status=completeness.status,
        issues=completeness.issues + expressibility.issues,
    )
```

---

## 6. 实现路线图

### Phase 1 — 完备性验证（不改现有生成逻辑）

1. 新增 `DOFAnalyzer` 和 `CompletenessVerifier`
2. 在现有 `DimensionPlanner` 输出后插入验证步骤
3. 未满足约束 → `DIMENSION_INCOMPLETE`，记录缺失项
4. 验收：已有 OK 案例通过验证，问题案例输出可读的缺失清单

**价值**：将"可能不完整"变成可量化的"还差 X 个约束"。

### Phase 2 — 可表达性判定与剖面规划

1. 新增 `ExpressibilityChecker`
2. 新增 `ViewPlanner`，输出 `ViewPlan`
3. `DrawingDocument` 支持多视图结构（主视图 + 剖面 + 详图）
4. 测试案例：
   - 带沉孔的板 → 必须有剖面
   - 带内腔的板 → 必须有剖面
   - 全平板贯通孔 → 无剖面

### Phase 3 — 约束驱动的尺寸规划

1. 将 `DimensionGenerator` 重构为 `ConstraintSolver`
2. 从约束反推最小完备尺寸集（替代现有规则生成）
3. 自动检测冗余尺寸（过度约束）

### Phase 4 — 布局优化器增强

1. 引入碰撞惩罚函数（替代现有简单检查）
2. 优化尺寸线分层（总长外层、分段内层）
3. 密集标注自动触发详图分割

---

## 7. 待验证事项

- [ ] 平板零件理论 DOF 的形式化定义（板厚是否算入？方向自由度如何处理？）
- [ ] 孔组的约束合并规则（等距阵列 vs. 不规则孔位）
- [ ] 剖面命名规范（A-A 递增 vs. 按位置命名）
- [ ] 布局求解算法的性能基线（标注数量 vs. 耗时上限）
- [ ] 详图比例选择策略

---

## 8. 优先级总结

| 优先级 | 模块 | 解决的核心问题 |
|--------|------|----------------|
| P0 | CompletenessVerifier | 不遗漏（可量化验证） |
| P1 | ExpressibilityChecker + ViewPlanner | 剖面按需 |
| P2 | ConstraintSolver（重构 DimensionGenerator） | 不重复（最小完备集） |
| P3 | LayoutSolver（增强 DimensionOptimizer） | 排布好（精细化） |
