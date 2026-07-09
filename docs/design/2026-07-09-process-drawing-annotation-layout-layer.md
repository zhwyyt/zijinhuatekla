# 工序图标注与避让层设计

## 背景

当前 Tekla GA 工序图 POC 已能从 Tekla `Part.GetSolid()` 重建胎架真实投影，但标注、尺寸、阶段说明和输出对象直接写在绘图函数里。`PROCESS-FIXTURE-U-10-3GZ-6-S1` 旧版出现黑色三角、粉色问号、蓝色竖排 `Tekla Structures`，根因就是在 GA sheet 坐标上直接调用 Tekla 原生 `StraightDimensionSetHandler.CreateDimensionSet()`，尺寸对象没有可靠关联 drawing view/model object。

这个问题说明：标注规则和避让规则不能由 Tekla/DXF renderer 临时决定，必须抽成独立层。Renderer 只能是画笔，不能承载“该标什么、优先级是什么、标不下怎么办”的业务判断。

## 目标

- 将工序图出图拆为 `几何投影 -> 标注意图 -> 布局避让 -> Tekla/DXF 输出` 四段。
- 第一阶段支持 BOX 柱 U-stage 主视图：底板 + 两侧板、胎架基准、总长、截面宽、壁厚、主零件标号和阶段说明。
- 同一套标注规则可被 Tekla GA renderer 和 DXF renderer 复用。
- 避让层必须能显式报告 `OK`、`OVERFLOW`、`NEEDS_DETAIL_VIEW` 或 `REVIEW_REQUIRED`，禁止无限堆叠标注。
- Tekla GA 路线默认不使用原生尺寸对象；除非确认对象绑定到可靠 drawing view/model object，否则尺寸用普通 `Line/Text` 渲染。

## 非目标

- 本阶段不实现完整正式构件图自动出图。
- 本阶段不处理所有剖面图和局部详图，只预留 `NEEDS_DETAIL_VIEW` 输出。
- 本阶段不追求全自动最优排版；先实现可解释、可测试、可人工复核的确定性布局。

## 分层架构

```text
ProcessStep
  -> ProjectionScene
  -> AnnotationIntent[]
  -> AnnotationLayout
  -> TeklaRenderer / DxfRenderer
```

### 1. ProjectionScene 几何投影层

只表达真实投影几何，不放置文字。

建议字段：

- `view_id`: 主视、剖面、局部详图等。
- `fixture_frame`: 长轴、宽向、高向、胎架底面。
- `model_to_sheet`: 模型坐标到图纸坐标的比例与偏移。
- `geometry_edges`: 普通投影线，保留 source part id 和 model endpoint。
- `part_anchors`: 每个零件可标注锚点，例如中心、端部、边线中点、孔中心。
- `model_extents`: 总长、总宽、截面高、壁厚等模型真实尺寸。
- `obstacles`: 主视轮廓、已有尺寸、标题栏、BOM 区等不可覆盖区域。

### 2. AnnotationIntent 标注意图层

只回答“要标什么”，不回答“放哪里”。

建议类型：

- `OVERALL_DIMENSION`: 总长、总宽、总高。
- `LOCAL_DIMENSION`: 当前新增零件的端距、间距、孔距、板厚。
- `THICKNESS_CALLOUT`: 壁厚或板厚，如 `t=30`。
- `PART_MARK`: 零件号、profile、名称、数量。
- `FIXTURE_NOTE`: 胎架底面、放置方向、翻身说明。
- `STAGE_NOTE`: 工序阶段说明，如“阶段 1：底板 + 两侧板，盖板未装”。
- `ORIENTATION_MARK`: 内外侧、上下面、构件端 A/B。
- `WARNING`: 数据不足、虚拟拆解、需要人工复核。
- `DETAIL_REQUEST`: 主视表达不清时请求剖面/局部详图。

每个 intent 至少包含：

- `id`
- `kind`
- `priority`
- `text`
- `target_anchor`
- `model_value`
- `source_part_ids`
- `evidence_codes`
- `allow_merge`
- `fallback_policy`

### 3. AnnotationLayout 布局避让层

只回答“放在哪里”和“是否放得下”。

核心规则：

- 图面先分区：标题/说明区、主视区、上方总长尺寸区、右侧截面尺寸区、左右 PartMark 区、BOM/注释区。
- 高优先级先放：总尺寸、当前阶段新增件定位、胎架方向、关键 PartMark。
- PartMark 候选点按目标锚点生成：右侧、左侧、上方、下方；计算引出线长度、穿越主视次数、与已有框重叠面积，取成本最低位置。
- 尺寸链按方向分层：总尺寸最外层，当前步骤详细尺寸内层；同向尺寸不得重叠，间距不足时自动增加层距。
- 重复件可合并标注，例如 `10-3Z-253 PL28*50 x8`，避免每个小零件单独标号。
- 当同一区域放不下时，不继续缩小文字或叠放，而是输出 `NEEDS_DETAIL_VIEW` 或 `REVIEW_REQUIRED`。

布局输出建议：

- `placed_items`: 已放置的文字、引出线、尺寸线、箭头、符号。
- `unplaced_items`: 未能放置的 intent 及原因。
- `collision_count`: 碰撞数，目标为 0。
- `layout_status`: `OK / OVERFLOW / NEEDS_DETAIL_VIEW / REVIEW_REQUIRED`。
- `debug_boxes`: 文字框、候选框、障碍框，供 PNG/debug JSON 检查。

### 4. Renderer 输出层

Renderer 只消费 `AnnotationLayout`，不再参与业务选择。

Tekla renderer 规则：

- GA 普通图纸优先用 `Line/Text` 绘制尺寸和标注。
- 只有在对象绑定到可靠 drawing view/model object 且验证无乱码时，才允许使用 Tekla 原生尺寸对象。
- 输出统计必须包含 `Lines/Texts/StraightDimensions/StraightDimensionSets/Parts/Marks/Views`。
- 若 `StraightDimensions > 0`，必须写出原因和来源。

DXF renderer 规则：

- 使用同一份 `AnnotationLayout` 输出 DXF `LINE/TEXT/MTEXT/ARC`。
- Debug 图层保留 layout boxes，正式输出可关闭。
- DXF audit 必须无错误。

## 第一阶段规则集

针对 `10-3GZ-6` U-stage 和后续 BOX 柱主视图，先实现以下最小规则：

1. 阶段说明放主视左上，不进入主视轮廓区域。
2. 总长尺寸放主视上方，文字为模型真实长度，例如 `3505`。
3. 总宽/截面尺寸放主视右侧，文字为模型真实宽度，例如 `600`。
4. 壁厚标注使用引出线或短尺寸，文字例如 `t=30`。
5. 主零件标注合并为 `10-3Z-128 / BOX600*600*30*30 / GKZ60-2`。
6. 虚拟拆解必须标注证据：`BOX profile virtual U-stage` 或中文等价说明，避免误以为 Tekla 中已有三块独立板。
7. 所有文字框必须不与主视轮廓、尺寸线、其它文字框重叠。
8. 若当前 step 的 PartMark 超过阈值，优先显示本步新增项，旧件进入 BOM 或汇总说明。

## 数据流示例

```json
{
  "intent": {
    "kind": "OVERALL_DIMENSION",
    "text": "3505",
    "priority": 100,
    "target_anchor": "main_view.length",
    "model_value": 3505,
    "source_part_ids": ["28705233"],
    "evidence_codes": ["TEKLA_SOLID_EXTENT"]
  },
  "layout": {
    "kind": "MANUAL_DIMENSION",
    "line": [[35, 183], [535, 183]],
    "text_box": [270, 188, 300, 196],
    "status": "OK"
  }
}
```

## 验收标准

- U-stage clean 图纸不再出现 Tekla 原生尺寸乱码；读回 `StraightDimensions=0` 且 `StraightDimensionSets=0`。
- U-stage 图纸显示总长、截面宽、壁厚、主零件标号、胎架/阶段说明。
- 标注布局 JSON 中 `collision_count=0` 或明确输出 `REVIEW_REQUIRED`。
- 同一份 intent/layout 可分别喂给 Tekla renderer 和 DXF renderer。
- 复杂步骤不会无限堆标注；超过阈值时输出 `NEEDS_DETAIL_VIEW`。

## 验证计划

1. 单元测试：构造 U-stage `ProjectionScene`，断言生成总长、总宽、壁厚、PartMark、阶段说明 intents。
2. 单元测试：布局器对 U-stage 场景输出 `collision_count=0`，且文字框不与主视 bbox 重叠。
3. 单元测试：密集 PartMark 场景触发合并或 `NEEDS_DETAIL_VIEW`。
4. Tekla smoke：生成 `PROCESS-FIXTURE-U-10-3GZ-6-S1-CLEAN`，读回 `StraightDimensions=0/StraightDimensionSets=0`。
5. DXF smoke：同一 layout 输出 DXF，`ezdxf audit` 无错误。
6. 人工检查：截图确认文字不压线、不遮挡主视、工人能看出阶段动作和关键尺寸。

## 风险与取舍

- Tekla 原生尺寸对象如果继续用于 GA sheet，容易产生不可控显示；本阶段宁可用普通线/文字，牺牲部分 Tekla 原生尺寸智能，换稳定可控。
- 避让算法第一版采用确定性候选位置 + 成本排序，不做复杂优化求解，便于调试和回归。
- 标注规则必须从工艺语义出发，不能为了图面好看丢失关键尺寸；标不下时请求局部详图，而不是删除关键标注。