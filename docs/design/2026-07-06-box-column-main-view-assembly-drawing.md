# BOX Column Main View Assembly Drawing

> Superseded on 2026-07-07 by `docs/design/2026-07-07-box-process-drawing-claude-guidance.md`. This file records the earlier main-view pass; the current target is the Claude v3 cumulative process drawing.

## Background

上一版 `box-assembly-drawing-steps.dxf` 只是步骤卡片，不能表达真实构件组立图。参考项目根目录 `4.西岑文化艺术中心地上三节柱组立图2026.07.03.dwg` 后，本阶段把 CAD/DXF 兜底图纸调整为“主视组立图”口径。

第一版不追求完全替代 Tekla 正式图纸，也不强制生成剖面图。剖面只在主视无法表达清楚零件定位时作为后续增强。

## Confirmed Scope

- 先支持 BOX 柱。
- 每个组立阶段输出一个主视图图框。
- 主视图按构件 station 方向真实比例绘制，能看到构件总长、当前阶段零件所在 station 和相对端部位置。
- 已存在零件作为淡线参照，新增加零件作为强线显示。
- 输出尺寸链、零件引出标注、阶段注释和简化材料表。
- 不按每个小零件单独分页；按 station、内外关系、外部簇和共享定位基准合并。

## Drawing Semantics

DXF 图层对齐参考组立图的功能语义：

- `DrawingSheet`: 图框、标题栏、材料表框线。
- `Part`: 已存在构件和零件主视投影。
- `NewPart`: 当前阶段新增零件主视投影。
- `Z-DIMENSIONS`: 构件总长、端距、station 定位、阶段范围尺寸。
- `PartMark`: 零件编号、规格、数量、引出线。
- `Text`: 阶段标题、构件号、说明文字。
- `Table`: 当前阶段新增零件表。

## Main View Layout

每个阶段图框包含：

1. 左侧主视图：BOX 柱身沿 station 方向竖向展开。
2. 主体外轮廓：用该阶段 `visible_part_ids` 的 station 范围确定柱身长度，BOX 宽度第一版按固定可读宽度表达。
3. 零件投影：每个零件按 `station_range` 或 `axisStationStart/End` 映射到主视坐标。
4. 端部尺寸：标注构件总 station 范围。
5. 定位尺寸：标注当前新增零件组的起止 station 和端距。
6. 零件标注：用引出线指向新增零件，文字包含 `part_position / profile / name`，重复件合并显示数量。
7. 阶段注释：说明本步新增内容、显示范围和需要人工复核的限制。
8. 简化材料表：列出当前阶段新增零件的编号、规格、名称、数量。

## Data Strategy

第一版继续消费 `boxAssemblyDrawingSteps.v1`，不新增构件号或零件号特例。

可用字段：

- step 级 `new_part_ids`、`visible_part_ids`、`reference_part_ids`。
- step 级 `part_mark_targets`、`dimension_targets`、`station_range`、`title`。
- part 级数据目前不随 step JSON 完整输出时，DXF 渲染器先以 step 的 mark target 和 station_range 绘制新增零件；后续可把 part station/detail snapshot 写入 JSON，提升单件主视投影准确度。

第一版允许同一 step 内小零件共用同一个 station 投影框，前提是标注和材料表能说明数量、规格和定位关系。

## Acceptance Criteria

- DXF 不再输出“步骤卡片”标题或卡片式小方块列表。
- 每个阶段图框内有按 station 比例绘制的 BOX 主视轮廓。
- 每个阶段至少有构件总长尺寸、当前阶段 station 范围尺寸和端距说明。
- 新增零件有引出线和 `part_position / profile` 标注。
- 当前阶段有材料表，重复零件按编号和规格合并数量。
- 图层包含 `DrawingSheet`、`Part`、`NewPart`、`Z-DIMENSIONS`、`PartMark`、`Text`、`Table`。
- `T3-3GZ-6` 可重新生成 DXF，并可渲染为 PNG 供人工看图复核。

## Verification Plan

1. 单元测试：最小 step payload 生成 DXF，断言存在工程图图层、主视轮廓、尺寸文字、零件标注和材料表。
2. 单元测试：断言不再出现 `BOX progressive drawing steps` 等步骤卡片标题。
3. 报告测试：offline report 生成的 DXF 使用新的主视图语义。
4. Smoke：用当前选中构件 `T3-3GZ-6` 重新运行 analyze，生成新的 `box-assembly-drawing-steps.dxf`。
5. 渲染：把 DXF 渲染为 PNG，人工检查主视、标注和注释是否接近参考组立图方向。

## Non Goals

- 第一版不做自动剖面图。
- 第一版不处理 Tekla Drawing API 的 active drawing 隐藏/标注控制。
- 第一版不承诺所有小零件都具备真实截面形状投影。
- 第一版不为每个小零件生成单独整页。
