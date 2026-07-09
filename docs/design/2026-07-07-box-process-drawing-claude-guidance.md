# BOX 柱工序图 Claude v3 指导落地设计

## 背景

2026-07-06 的主视图第一版仍偏“阶段示意”，没有充分满足真实组立图的读图需求。用户提供 `给Codex的工序图技术指导_v3.md` 后，本设计将 DXF 兜底图纸收敛为累计工序图：

- 每一步都是“已装配状态 + 本步新增零件高亮”，不是重新画一张孤立示意图。
- 主视图先表达清楚高度方向位置、零件编号、焊缝/螺栓/局部详图和累计 BOM。
- 不为每个小零件单独分页，按能表达定位关系的工序阶段输出。
- 剖面图暂不作为强制项；主视表达不清时再补局部剖面。

## Drawing Semantics

DXF 图层沿用指导书验证过的图层体系：

- `DrawingSheet`: 图框、标题栏、表格框线。
- `Part`: 构件主视轮廓和零件投影；已装配部分常规色，本步新增零件红色。
- `PartMark`: 零件号文字框、规格文字和引出线。
- `Z-DIMENSIONS`: 外侧全部通高尺寸、内侧连续详细尺寸链。
- `文本`: 标题、焊缝说明、阶段说明。
- `Bolt`: 螺栓孔。
- `BoltMark`: 螺栓规格文字。
- `Section`: 折点/节点剖切标记。
- `Defpoints`: 预留辅助定位。

不再使用昨天临时的 `NewPart`、`Table`、`Text` 层来表达核心语义。

## State Model

DXF 渲染器维护 `_AssemblyState.installed_part_ids`，每个 step 只追加零件：

1. `visible_part_ids + new_part_ids` 进入累计安装状态。
2. 主视图重画当前累计状态。
3. 本步新增零件用红色，既有零件用常规色。
4. PartMark/BOM/局部详图优先显示本步新增项，避免后期步骤被截断列表淹没。
5. 焊缝说明按累计状态绘制，并保证每条焊缝引线都有文字说明。

## Main View

主视图仍是 BOX 柱简化立面：

- 两条竖线或按 segment 投影后的轮廓表示柱身。
- 零件按 `axisStationStart/axisStationEnd` 映射到高度方向。
- `bodyFaceId` 用于分配主视图横向 lane，帮助区分左右壁板、盖板、内部板和外部件。
- 外部/螺栓件优先进入 `LOCAL DETAIL` 框，主视图只保留定位和引出关系。

## Dimension Chains

尺寸链使用两层：

- 外侧总尺寸：`全部通高 N`，表示整根柱的垂直投影视觉总高。
- 内侧详细尺寸链：从累计零件 station 起终点生成连续分段，不因 step 分页而中断。

本步新增零件覆盖到的详细尺寸段用红色高亮。

## Weld, Bolt, BOM

- 焊缝：用斜引线 + `全熔透` 或 `角焊缝 Nmm`，不允许只有线没有文字。
- 螺栓：局部详图内输出 `Bolt` 圆孔和 `BoltMark` 数量/直径。
- BOM：每步表格显示累计零件，按 `part_position/profile/name/material` 合并数量，本步新增行高亮。

## Bend Handling

按 v3 指导修正折弯柱：

- 小角度折弯不画折断符号、不写偏转角说明。
- 相邻 axis segment 出现角度差时，推断折点 station，并生成普通 `Section` 剖切标记。
- segment 按真实角度投影到同一主视图，零件投影随 segment 角度旋转。
- 折点处画普通双线拼接缝。

当前 T3-3GZ-6 的两个 axis segment 角度均为 0 度，本次真实输出不触发折弯；折弯行为由单元测试锁定。

## Acceptance Criteria

- `T3-3GZ-6-box-assembly-drawing-steps.dxf` 标题为 `BOX 工序图`。
- 每步保留累计零件状态，后续步骤能看到已装配零件和新增零件。
- 后续步骤保留已有焊缝说明，不只显示本步新增焊缝。
- 后期新增零件即使累计 PartMark 超过显示上限，也必须优先显示本步新增 PartMark。
- 局部详图优先显示本步新增外部/螺栓件。
- BOM 为累计零件表，不是空表格。
- 折弯测试中只出现真实旋转投影、拼接双线和 `Section` 标记，不出现 `BREAK SYMBOL` 或 `偏转角`。

## Verification Plan

1. 单元测试覆盖累计状态、PartMark、尺寸链、焊缝、BOM。
2. 单元测试覆盖外部簇局部详图、Bolt/BoltMark 和焊缝文字。
3. 单元测试覆盖小角度折弯真实投影和 B-B 剖切标记。
4. 报告测试覆盖 offline report payload 到 DXF 的完整接入。
5. 用当前选中构件 `T3-3GZ-6` 重新运行 analyze，生成 DXF/PNG。
6. 用 ezdxf 读回 DXF TEXT，确认中文内容未被编码破坏。
7. 跑 `python -m unittest discover -s tests` 做全量回归。
