# BOX 工序图胎架翻身与步骤合并设计

## 背景

用户复核后明确：BOX 柱工序图的目标不是把每个小零件拆成单独页面，而是让工人按胎架装配逻辑一眼看懂每一步做什么、零件装到哪里、尺寸是多少。真实制造会先确定底面放胎架，再逐步加腹板、内部件、盖板和外部零件；外部件还可能需要翻身或侧焊。

## 设计口径

- 基准主板按工作底面成组输出。若底面主板由多块 Tekla 分段板焊成，同一工作底面的主板链合并为一个 `BASE_MAIN_WALL` 步骤。
- `BASE_MAIN_WALL.evidence_summary` 输出 `fixture_face` 和 `fixture_role=fixture_base`，DXF 阶段说明输出 `FIXTURE ...`。
- 外部零件先按既有空间簇生成 draft，再按翻身面合并成更少的工序阶段。
- 工作面优先来自零件 `mainMaterialEvidence.bodyFaceId`；真实外部件缺少该字段时，从空间关系 `projected_centroid_u/v` 推断 `RADIAL_X_POS/RADIAL_Y_POS/RADIAL_X_NEG/RADIAL_Y_NEG`。
- 翻身算法支持两套四面环：合成测试的 `FACE_A/B/C/D`，以及真实截面投影的 `RADIAL_*`。
- `MUST_TOP` 面作为朝上施工面；相邻 `CAN_SIDE` 面可并入同一步作为 `side_work_faces`，DXF 阶段说明输出 `UP FACE ...`、`SIDE WELD ...`、`FLIP 90`。
- 当前真实样例没有明确 `CAN_SIDE` 证据，因此只输出 4 个翻身朝上阶段，不硬凑侧焊。

## Acceptance Criteria

- 分段底面主板在同一 `BASE_MAIN_WALL` 步骤中出现，不分散成多页。
- 基准步骤标题包含胎架语义，并在 JSON/DXF 中带 `fixture_face`。
- 外部簇可按翻身面合并，减少每簇单独一页的图纸爆炸。
- 缺少 `bodyFaceId` 的真实外部件可用 `projected_centroid_u/v` 推断工作面。
- DXF note 能显示 `FIXTURE`、`UP FACE`、`SIDE WELD`、`FLIP` 工序提示。
- 真实 `T3-3GZ-6` 输出保持真实投影 DXF 可打开，并从 29 步收敛到合理的 14 步。

## Verification Plan

- 单元测试：
  - `python -m unittest tests.test_box_assembly_drawing_steps`
  - `python -m unittest tests.test_box_progressive_dxf`
  - `python -m unittest discover -s tests`
- 真实 smoke：
  - `python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260706_165011 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-3GZ-6 --out outputs\box-progressive-drawing-selected-20260706`
- DXF 读回：
  - 用 `ezdxf.readfile(...).audit()` 验证 `errors=0/fixes=0`。
  - 抽查 DXF TEXT 中包含 `FIXTURE`、`UP FACE`、`FLIP`。

## Remaining Limits

- `CAN_SIDE` 仍依赖显式 access 证据、焊缝类型或板厚启发式；后续应由工艺人员提供 WPS/胎架规则阈值。
- 当前只规划四面翻身，尚未考虑吊装夹具、实际焊接变形控制和构件重心。
- DXF 仍是离线兜底图，不是 Tekla Drawing Editor 原生对象；正式生产图还需要更强的标注避让和剖面/局部详图策略。
