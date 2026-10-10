# T3-6YC-16 主材形态判定来源

2026-10-10 用户询问为什么主材形态为“折弯”。本轮只追溯当前判定，不修改分类口径、主轴或 exe。

## 已验证数据

数据源 `cache/selected-mainline-20261010-105609`，报告 `outputs/main-material-axis-20261010/delivery/徐汇T3_当前选择集.xlsx`。精确命中装配 `71010441`，主件 `71010436 / T3-L-334`，规格 `L100*8`，bundle 的 runtimeType 和 member PartType 均为 `PolyBeam`。

- 5 个截面宽高均约 100×100mm，仅浮点尾差；未触发截面变化条件。
- member 标签仅 `profile-angle`，没有折弯标签。
- `AxisSegments` 只有 1 段，长度 2433.057496mm；`GuidePolyline` 只有起终点 2 点。
- 当前函数重算与报告一致：主材类型=角钢、主材形态=折弯、主材轴线形状=直线、折弯数量=0。
- 报告证据：`profile.L;main_part.polybeam;axis.segments:1;axis.bend_count:0`。

## 判定链路

`reports/member_complexity.py::_main_material_form` 使用 Tekla 主件类型与截面变化/标签：主件类型为 PolyBeam 时，将内部 bend_count 赋为 1；若还有截面变化则赋为 2。本例无截面变化、无额外折弯标签，故返回“折弯”，证据 `main_part.polybeam`。

这条路径没有读取轴线段数、方向转角或实际折点。另一个函数 `_axis_shape_and_bend_count` 独立检查 `AxisSegments` 的相邻方向，本例仅 1 段，故返回“直线”、0 折弯。

结论：“折弯”来自按 PolyBeam 建模类型的推定，并非分组跨度主轴算法检测出了折点。PolyBeam 表示建模对象类型，单凭这个类型不足以证明实体发生了折弯；现有导出轴线也未提供折点。当前证据不替代 Tekla 模型人工几何确认，本轮不擅自判定最终业务标签或修改规则。

## 验证与后续边界

已执行真实缓存精确身份提取、主件类型核对、截面样本/轴线检查、复杂度函数重算和原 Excel 读取。未操作真实 Tekla、未修改算法、未重新打包。详细证据保存于忽略目录 `outputs/member-form-20261010/T3-6YC-16-source.json` 与 `T3-6YC-16-report.json`。

解释同名业务字段时，先区分对象类型、截面变化、轴线几何和制造工艺；不同字段可能来自不同层，不能把对象类型推断当作测量结果。本例展示了“主材形态”和“轴线折弯数量”的独立来源，若后续用户要求统一真实几何口径，应同时回归直线 PolyBeam 与真实折线主件，避免仅按编号修正。
