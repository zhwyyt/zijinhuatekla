# 零件图尺寸规划层设计

## 文档状态

- 日期：2026-07-14
- 状态：待用户确认后实施
- 范围：平板零件尺寸需求归并、尺寸链规划和图面层级规划
- 首个真实验收件：`T3-PX-317`，但生产规则不得依赖该零件号或固定坐标

## 背景

当前零件图流水线已经能从 Tekla 快照识别外轮廓和圆孔，并输出可编辑的 CAD 原生 `DIMENSION`。但是尺寸生成器会为每个独立圆孔生成直径、X 坐标和 Y 坐标，布局层再按优先级逐项尝试放置。

这种流程把工程表达决策错误地下放给了避让算法。对于 `T3-PX-317` 的 `3 x 2` 同径孔阵，系统生成 12 个逐孔定位尺寸，只放置 5 个，其余 7 个进入 `LAYOUT_OVERFLOW`。这些未放置项主要是重复行列坐标，不应该通过扩大标注带或降低碰撞标准强行放入图面。

工程图尺寸具有明确层级：离零件近的层表达孔、切口、倒角等加工特征定位；外层表达零件最大尺寸；孔径、圆角和倒角等采用局部引出表达。系统必须先盘点零件信息并形成尺寸方案，再在方案限定的层级内进行避让。

## 目标

1. 在尺寸需求生成与图面布局之间新增独立 `DimensionPlanner`。
2. 按外轮廓、孔及孔组、倒角、圆角、切口等语义规划必须表达的信息。
3. 合并重复孔位坐标，将规则二维孔阵表达为行列尺寸链，而不是逐孔 X/Y。
4. 显式规划尺寸所在方向、侧边和层级，保证总尺寸位于特征尺寸链外侧。
5. 布局层只在已规划层内调整文字和局部位置，不再决定尺寸是否重复、如何成链。
6. DXF 继续输出 CAD 原生 `DIMENSION`，PDF 从同一规划和布局结果渲染。
7. 所有无法规划或无法放置的信息必须进入可追溯质量状态，不得静默丢弃。

## 非目标

- 本阶段不实现所有异形孔阵、极坐标孔阵或任意曲线基准尺寸。
- 本阶段不重做图框、标题栏、材料表或零件号排版。
- 本阶段不引入通用约束求解器。
- 本阶段不修改 Tekla 快照导出契约。
- 本阶段不通过增加标注带容量解决 `T3-PX-317` 的 7 个未放置尺寸。

## 架构

```text
PartDrawingSnapshot
  -> GeometryAnalyzer / FeatureRecognizer
  -> DimensionGenerator
       输出需要表达的原始 DimensionIntent
  -> DimensionPlanner
       语义归并
       基准选择
       尺寸链构建
       侧边与层级分配
  -> DimensionPlan
  -> DimensionOptimizer
       仅在规划层内放置和避让
  -> PartDrawingDocument
  -> Native DXF DIMENSION / PDF
```

### DimensionGenerator

保留“需要表达什么”的职责：

- 零件总长、总宽、厚度。
- 孔中心、孔径和来源特征。
- 倒角、圆角、切口和其他加工特征的必要参数。
- 模型真实值、证据码和来源 feature id。

生成器不再把每个孔的 X/Y 直接视为最终图纸尺寸，也不决定标注层级。

### DimensionPlanner

新增 `dimension_planner.py`，消费几何、识别特征和原始尺寸需求，输出格式无关的 `DimensionPlan`。

核心数据结构：

```text
DimensionPlan
- chains: DimensionChain[]
- callouts: PlannedCallout[]
- covered_intent_ids
- unresolved_intents
- issues

DimensionChain
- chain_id
- axis: X / Y
- side: TOP / BOTTOM / LEFT / RIGHT
- layer: 从零件向外递增
- baseline_kind: EDGE / DATUM
- points: 有序模型坐标
- segments: DimensionSegment[]
- source_feature_ids
- evidence_codes

DimensionSegment
- start_anchor
- end_anchor
- measured_value_mm
- display_mode: VALUE / EQUAL_SPACING / COUNT_SPACING
```

`layer` 表示工程表达层级，不是布局失败后的临时偏移。特征定位链位于内层；同侧总尺寸必须位于所有特征链外层。

### DimensionOptimizer

布局层改为消费 `DimensionPlan`：

- 根据 side 和 layer 计算稳定基线。
- 为计划层预留图面边距，再计算主视比例和位置。
- 只允许在同一规划层的小范围候选位置内移动文字。
- 不得跨层交换总尺寸和特征尺寸。
- 不得自行删除、合并或新增尺寸段。
- 规划正确但图面放不下时返回 `LAYOUT_OVERFLOW`。

### Renderer

- 每个线性 `DimensionSegment` 输出原生 DXF `DIMENSION`。
- 同一尺寸链共享 DIMSTYLE、方向和基线层级。
- 孔组只保留一个代表性孔径引出，例如 `6-Ø27`，并追溯到全部孔 feature id。
- PDF 使用同一 `DimensionPlan` 和 `PlacedDimension`，不得独立推断尺寸。

## 信息盘点与规划规则

### 外轮廓

- 总长和总宽始终属于必要尺寸。
- 在同一轴和同一侧存在特征定位链时，总尺寸放在最外层。
- 显示精度由 `partCadDimensionStyle.v1` 决定，内部保留精确模型值。

### 单孔

- 输出一次孔径或孔型引出。
- 输出相对于稳定板边基准的 X/Y 定位。
- X/Y 分别进入对应轴的特征定位层。

### 规则二维孔阵

第一阶段识别条件：

- 圆孔直径在版本化容差内一致。
- 孔中心可归并为两个或多个唯一 X 坐标和两个或多个唯一 Y 坐标。
- 唯一 X/Y 坐标的笛卡尔组合均有对应孔，不允许缺孔时误判完整矩形阵列。
- 坐标归并只使用几何和明确孔特征证据，不解析零件号或项目名。

规划结果：

- 同一唯一 X 坐标只表达一次。
- 同一唯一 Y 坐标只表达一次。
- X 方向生成“板边 -> 各列中心 -> 板边”连续尺寸链。
- Y 方向生成“板边 -> 各行中心 -> 板边”连续尺寸链。
- 等间距连续段允许表达为 `n@spacing`；首尾边距仍独立表达。
- 同径孔阵只生成一个数量和孔径引出，例如 `6-Ø27`。
- 总长、总宽位于对应特征链外层。

若孔中心不能构成完整矩形阵列，则不得强行套用该规则；保留为独立孔或后续支持的其他孔组类型，并输出可解释的规划结果。

### 倒角、圆角和切口

- 半径、角度、深度等局部加工量优先使用局部引出。
- 相对于板边的位置进入特征定位层。
- 证据不足时保留 `DIMENSION_INCOMPLETE` 或 `REVIEW_REQUIRED`，不得由布局层猜测。

## T3-PX-317 预期计划

几何事实：

- 板件范围：`300 x 243.174 mm`。
- 六个 `Ø27` 圆孔，形成三列两行完整孔阵。
- 唯一 X 坐标：`60, 150, 240`。
- 唯一 Y 坐标：`93.174, 183.174`。

计划表达：

```text
X 特征定位内层：60 | 90 | 90 | 60
X 总尺寸外层：300

Y 特征定位内层：93.174 | 90 | 60
Y 总尺寸外层：243.174

局部孔组引出：6-Ø27
厚度说明：t=16
```

最终显示文字按现有样式取整，但每个原生尺寸实体保留准确模型测量值和比例补偿。允许将连续的两个 `90` 合并显示为 `2@90`，前提是 DXF/PDF 表达一致且测量证据仍可追溯。

## 质量状态

将问题区分为两类：

- `DIMENSION_PLAN_INCOMPLETE`：必要工程信息无法形成可靠尺寸方案，例如非规则孔阵缺少明确基准。
- `LAYOUT_OVERFLOW`：方案已经明确，但规划层在页面中无法无碰撞放置。

`DimensionPlan` 必须记录每个原始 intent 是被某个尺寸链覆盖、被合并到 callout，还是 unresolved。任何 intent 都不得无记录消失。

## 实施边界

建议新增：

- `src/zijinhua_tekla/part_drawing/dimension_planner.py`
- `tests/test_part_drawing_dimension_planner.py`

建议最小修改：

- `dimension_generator.py`：保留原始需求，不承担孔阵最终表达。
- `dimension_optimizer.py`：消费 plan，按 side/layer 放置。
- `drawing_output.py`：支持连续尺寸链和合并孔径 callout 的原生实体输出。
- `pipeline.py`：串联 planner 并传播规划质量状态。
- 现有尺寸、布局、输出和 pipeline 测试：更新契约断言。

不在本阶段重构其他分类器、BOX 工序图或 Tekla 导出器。

## Acceptance Criteria

1. `T3-PX-317` 的六个孔被识别为三列两行完整孔阵，规则不包含具体零件号或固定坐标。
2. 该孔阵不再生成 12 个逐孔 X/Y 最终尺寸，而是生成唯一行列连续尺寸链。
3. X 特征链表达 `60/90/90/60`，外层总尺寸表达 `300`。
4. Y 特征链表达精确的 `93.174/90/60`，外层总尺寸表达精确的 `243.174`；显示精度继续遵循样式。
5. 六个同径孔只生成一个可追溯到全部孔的 `6-Ø27` 引出。
6. 总尺寸在特征定位链外层，布局层不得交换层级。
7. 生成的线性尺寸均为原生 DXF `DIMENSION`，不退回 `LINE + TEXT`。
8. `T3-PX-317` 不再因这 7 个重复孔定位 intent 返回 `LAYOUT_OVERFLOW`。
9. 任何未覆盖的必要需求都进入 `DIMENSION_PLAN_INCOMPLETE`，没有 intent 被静默丢弃。
10. DXF 通过 `ezdxf.audit()`，PDF 与 DXF 的尺寸文字和层级一致。
11. 单孔和既有矩形板回归行为保持正确。

## Verification Plan

### 单元测试

- 三列两行等径完整孔阵归并为两个连续尺寸链和一个孔径 callout。
- 不等边距但等间距的孔阵保留正确首尾边距。
- 缺少一个孔的阵列不得误判为完整矩形孔阵。
- 不同直径孔不得合并到同一孔径 callout。
- 单孔仍生成两个定位需求和一个孔径引出。
- 总尺寸层级严格大于同侧特征尺寸链层级。
- 原始 intent 覆盖账目完整。

### 输出测试

- 读回 DXF，断言尺寸链段均为 `DIMENSION`，`DIMSTYLE=PART-CAD-V1`。
- 断言原生尺寸测量值与精确模型尺寸一致。
- 断言 DXF 中不存在用于替代线性尺寸的 `LINE[layer="DIMENSION"]`。
- 比较 PDF 和 DXF 的尺寸文字集合。
- 执行 `ezdxf.audit()`，要求无错误和修复。

### 真实 smoke

```powershell
python -m zijinhua_tekla.cli draw-parts `
  --snapshot-root I:\tmp\tekla-selected-part-snapshot-smoke-20260713-v2\part-drawing-snapshots `
  --out I:\tmp\tekla-selected-part-drawing-planned-20260714 `
  --cjk-font C:\Windows\Fonts\simhei.ttf
```

人工检查：

- 总尺寸位于孔定位链外侧。
- 孔阵只出现一次数量/孔径引出。
- 连续尺寸链无重复坐标、无文字重叠、无标题栏穿越。
- CAD 中尺寸对象可选择和编辑。
- 若仍为 `REVIEW_REQUIRED`，问题必须来自真实未解决信息，而不是原有 7 个重复定位尺寸。

