# 构件复杂度与几何零件特征

## 目标

- 输出每个构件实例的主材类型：H钢、BOX、十字、一字板、角钢、槽钢、圆管等。
- 输出主材形态：变截面、同截面、折弯、多个折弯。
- 输出牛腿数量、楼层高度分布和相对主材方向。
- 零件特征继续以几何事实为准：剖口、倒角、切割、洞口、螺栓孔。

## 方法

1. `reports/member_complexity.py` 汇总构件级主材类型与形态。
2. 主材类型优先使用 Tekla 截面分类和主件 profile；`HXZ` 构件族按项目语义归入一字板，不允许扩展到单根零件号特判。
3. 主材形态用 `Samples.SectionFeatures` 的外包尺寸变化和折叠/折弯证据判断。
4. 牛腿继续由外伸附属件聚类派生；楼层高度用牛腿簇 Z 值聚合，方向用主轴和牛腿主件 `axisX` 夹角判定。
5. 零件特征沿用几何归一化结果；BOOLEAN_CUT 只在 `cutsFatherSolid=true` 时计剖口。

## Acceptance Criteria

- 289 根最新选择集装配能输出 289 行构件级复杂度，0 错误。
- `HXZ` 构件的主材类型为“一字板”。
- 现有零件特征 Excel 增加“切割”“螺栓孔”列，且不改变既有 H/BOX 主材分类逻辑。
- 单元测试覆盖 HXZ 族、变截面、牛腿楼层和牛腿方向。

## Verification Plan

- 运行 `PYTHONPATH=src python -m unittest discover -s tests`。
- 用最新选择集 bundle 重跑零件特征 Excel 与构件复杂度 Excel。
- 核对输出 summary 与抽样 HXZ 行。
