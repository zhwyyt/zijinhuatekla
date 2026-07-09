# BOX 工序图真实投影修正设计

## 背景

用户复核指出：多张工序图是正确方向，但每张必须像组立图一样表达真实几何投影、零件标号、尺寸标注和必要注释；不能继续用 station/lane 示意矩形代替构件图。

本次修正的根因是：原始 `member_T3-3GZ-6.json` 中 95 个零件都有 `SolidEdges`，但 `box-assembly-drawing-steps.json` 只保留了零件号、规格、station、face、bolt/weld，丢掉了真实几何，导致 DXF 渲染器只能画简化矩形。

## 设计口径

- 步骤计划仍由 `boxAssemblyDrawingSteps.v1` 决定，不新增按单个小零件分页的规则。
- `box-assembly-drawing-steps.json.parts[]` 增加 `projectionEdges`，由 Tekla solid edge 的全局 `X/Z` 投影生成二维主视边线。
- 若未来导出器提供 `projectionArcs`，DXF 渲染器直接输出 `ARC` 并标注 `R半径`。
- DXF 默认渲染全部步骤，按 3 列 sheet 网格排布，避免恢复成长卷；`render_step_no` 仍保留为单步调试入口。
- 主视图优先渲染 `projectionEdges/projectionArcs`；缺少真实几何时才退回旧 station 矩形兜底。
- 折弯仍按真实旋转投影，不画折断符号；同时按用户最新要求在 Section 附近标注 `BEND n°`。

## Acceptance Criteria

- `T3-3GZ-6-box-assembly-drawing-steps.json` 中 95 个零件均带 `projectionEdges`。
- DXF 包含 29 张阶段页，每张有 sheet、标题、主视、PartMark、尺寸链、BOM 区。
- DXF 每张主视包含 `TRUE PROJECTION`，且 Part 层存在真实斜边/曲边离散线，不再只由 lane 矩形组成。
- 有 `projectionArcs` 的测试载荷会输出 `ARC` 和 `Rxxx` 半径标注。
- 折弯测试载荷输出 `BEND 8°`，且不输出折断符号。

## Verification Plan

- 单元测试：
  - `python -m unittest tests.test_reports_offline`
  - `python -m unittest tests.test_box_progressive_dxf`
  - `python -m unittest discover -s tests`
- 真实 smoke：
  - `python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260706_165011 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-3GZ-6 --out outputs\box-progressive-drawing-selected-20260706`
- DXF 读回检查：
  - 统计页数、实体数、`TRUE PROJECTION` 数量、Part 层非水平/垂直线数量和 bbox。

## Remaining Limits

- 当前仍是离线 DXF 兜底，不是 Tekla Drawing Editor 原生对象；自动标注避让能力有限。
- 主视只使用全局 `X/Z` 投影，尚未根据构件最佳视向自动选择 `X/Z` 或 `Y/Z`。
- 当前真实 cache 没有显式弧线半径，圆孔/曲边多表现为 solid edge 离散线；半径标注能力已在 `projectionArcs` 契约和测试中预留。
