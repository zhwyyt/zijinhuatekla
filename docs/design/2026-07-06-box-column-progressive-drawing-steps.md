# BOX Column Progressive Drawing Steps

## Scope

本设计用于第一版 BOX 柱子“渐进式构件图”能力：先按构件组立/定位逻辑生成步骤计划，再由 Tekla 2017 Drawing API 或 CAD/DXF 生成可查看图纸。

第一阶段目标不是直接替代人工正式出图，而是做出一版能验证业务口径的结果：选中一个 BOX 柱子后，系统可以输出每一步应该显示哪些零件、隐藏哪些零件、新增哪些零件、需要标哪些尺寸、需要标哪些零件信息，并尽量用 Tekla 图纸视图执行。

## Confirmed Direction

采用“两层规划、第一阶段只实现可验证第一版”的方案：

1. 离线步骤计划层：在 `I:\zijinhuatekla` 中基于现有 pipeline 输出 `box-assembly-drawing-steps.json/csv/markdown`。
2. Tekla 出图 POC 层：基于 Tekla Structures 2017 本机安装路径 `D:\Program Files\Tekla Structures\2017\nt\bin`，验证能否按步骤在构件图中控制零件显示、零件标记和关键尺寸。
3. CAD/DXF 兜底层：如果 Tekla 2017 图纸 API 无法稳定按零件集合控制视图，保留用 CAD/DXF 直接绘制渐进式图纸的兜底路径。

Tekla 2017 本机反射已确认 `Tekla.Structures.Drawing.dll` 中存在以下公开类型和能力：

- `AssemblyDrawing.Insert()` 可创建构件图。
- `DrawingHandler` 可打开、保存、更新图纸。
- `View.CreateFrontView`、`CreateTopView`、`Create3dView`、`CreateSectionView`、`CreateDetailView` 可创建视图、剖视和详图。
- `View.GetModelObjects()`、`ViewBase.GetAllObjects()` 可枚举图纸视图中的模型对象。
- `Part.Hideable.HideFromDrawingView()`、`HideFromDrawing()`、`ShowInDrawingView()` 可控制图纸零件隐藏/显示。
- `Mark(ModelObject).Insert()` 可插入零件标记。
- `StraightDimensionSetHandler.CreateDimensionSet()` 可创建直线尺寸组。

因此第一选择仍是 Tekla 内实现。CAD/DXF 只作为 API 控制失败或图纸质量不可接受时的替代路线。

## Business Semantics

渐进式构件图不是“每个小零件单独出一页”。它的核心是让加工和组立人员看懂：

- 本步骤新增了哪些零件。
- 新增零件装在什么 station、哪一侧、哪个簇或哪个内腔位置。
- 新增零件相对主板、端部、隔板、外部簇根部的关键定位尺寸。
- 当前步骤与前一步相比发生了什么变化。

出图粒度按“信息组”确定，而不是按单零件确定。一个步骤可以包含多个小零件，只要它们满足以下条件：

- 同一 station 区间或相邻 station 区间。
- 同一面、同一内腔功能组或同一外部零件簇。
- 共享同一定位基准。
- 图面标注不会拥挤到难以阅读。

复杂位置优先使用局部详图、剖面图和明细表，不为每个小零件新建整页。

## Step Model

第一版 BOX 柱子步骤分为以下类型：

- `BASE_MAIN_WALL`: 选择最适合作为底部/基准的主壁板。它作为后续 station 和截面定位的尺寸基准。
- `ADD_SIDE_WALLS`: 增加腹板/侧壁板，形成 L 形或 U 形开口截面。
- `ADD_INTERNAL_GROUP`: 增加内部隔板、加劲板、电渣焊相关件等。按 station 区间和内腔位置分组。
- `ADD_COVER_WALL`: 增加最后盖板，形成闭合 BOX。
- `ADD_EXTERNAL_CLUSTER`: 增加外部零件簇，例如牛腿、连接板组、节点簇。按簇为单位加入。
- `REVIEW_REQUIRED`: 证据不足、关系冲突或图面无法自动表达清楚时输出复核步骤。

默认顺序：

1. 基准主板。
2. 与基准主板相邻且定位关系最清楚的第一块侧壁板。
3. 第二块侧壁板，形成开口 U 形。
4. 内部零件组，按 station 从小到大、按共享基准合并。
5. 盖板，闭合 BOX。
6. 外部零件簇，按 station、根部连接证据和簇大小排序。

## Data Inputs

第一版直接消费现有离线 pipeline 结果，不新增围绕构件号或零件号的特例规则：

- `box_main_material_segment_groups`: BOX 主壁板确认集合。
- `box_part_spatial_relations`: `MAIN_WALL`、`INSIDE_BODY`、`OUTSIDE_ATTACHMENT`、`BOUNDARY_OR_THROUGH` 等内外关系。
- `spatial_classifications`: 外部附属件簇，例如 `Bracket`。
- `composite_main_material_segments`: 组合截面主材分段，后续可帮助区分稳定 BOX 段和过渡段。
- part 级 `mainMaterialEvidence.axisStationStart/End`、`bodyFaceId`、`sectionProjectionEvidence`。
- assembly 级 `relationships` 中的 Weld、Contact、Bolt。
- Excel/Tekla 对齐后的零件规格、长度、工序和数量信息。

## Output Contract

第一版新增输出建议名：

- `{member_id}-box-assembly-drawing-steps.json`
- `{member_id}-box-assembly-drawing-steps.csv`
- `{member_id}-box-assembly-drawing-steps.md`

JSON 顶层结构：

```json
{
  "assembly_id": "string",
  "member_id": "string",
  "source": "boxAssemblyDrawingSteps.v1",
  "steps": [
    {
      "step_no": 1,
      "step_type": "BASE_MAIN_WALL",
      "title": "基准主板",
      "station_range": "0.0-6000.0",
      "new_part_ids": ["string"],
      "visible_part_ids": ["string"],
      "reference_part_ids": ["string"],
      "hidden_part_ids": ["string"],
      "part_mark_targets": [
        {
          "part_id": "string",
          "part_position": "string",
          "profile": "string",
          "name": "string"
        }
      ],
      "dimension_targets": [
        {
          "kind": "station_range",
          "part_ids": ["string"],
          "from": "member_start",
          "to": "member_end",
          "label": "主板全长定位"
        }
      ],
      "view_hints": [
        {
          "view_mode": "box_open_top",
          "purpose": "show_new_parts_and_reference",
          "preferred_detail": "main"
        }
      ],
      "evidence_codes": ["string"],
      "confidence": 0.0,
      "issue_category": ""
    }
  ]
}
```

CSV 扁平化为一行一个 step，保留 `new_part_positions`、`visible_part_positions`、`dimension_kinds`、`view_modes`、`evidence_codes`。

Markdown 用于人工快速查看步骤摘要，不承载完整出图数据。

## Dimension Strategy

每一步只标最关键尺寸，避免图面爆炸：

- 基准主板：构件总长、主板 station 范围、主板规格和编号。
- 侧壁板/腹板：相对基准主板的截面定位、端部 station 对齐关系、主焊缝或接触边。
- 内部零件组：相对构件端部的 station 尺寸、相对内腔壁板的定位尺寸、组内重复件数量。
- 盖板：与已有 U 形截面的闭合关系、盖板 station 范围和关键接口尺寸。
- 外部零件簇：簇根部 station、所在面、外挑方向、关键孔或连接板定位尺寸。

如果一个 step 的标注目标超过图面可读阈值，系统应拆为局部详图或输出 `REVIEW_REQUIRED`，而不是继续堆标注。

## Tekla Drawing POC

Tekla POC 第一版只验证关键可行性，不追求正式排版：

1. 在 Tekla 当前模型中读取用户选中的 assembly。
2. 使用 `AssemblyDrawing` 创建或打开构件图。
3. 创建一个或多个 view。
4. 通过 drawing part 的 `ModelIdentifier` 与步骤计划中的 `part_id` 对齐。
5. 对不属于当前 step 的 drawing part 调用 `HideFromDrawingView()`。
6. 对 `new_part_ids` 插入 `Mark`，并尝试用不同属性或视图标题表达“本步新增”。
7. 对至少一种 `dimension_targets` 调用 `StraightDimensionSetHandler.CreateDimensionSet()` 或输出待人工标注说明。
8. 保存图纸，并输出 POC 日志。

POC 成败标准不是图面美观，而是能否证明 Tekla 2017 可按步骤控制零件集合。

## CAD/DXF Fallback

如果 Tekla POC 遇到以下情况，转入 CAD/DXF 方案：

- drawing part 无法稳定映射回 Tekla model part id。
- `HideFromDrawingView()` 无法按 view 粒度稳定控制显示。
- Mark 或 dimension API 在 2017 环境中限制过多，无法表达最小步骤图。
- Tekla 自动出图排版需要大量人工交互，无法批量化。

CAD/DXF 兜底方案仍使用同一份 `box-assembly-drawing-steps.json`。区别只是渲染器从 Tekla drawing plugin 换成自绘 CAD 图层：

- 每个 step 一个 CAD 布局或一个图框区域。
- `visible_part_ids` 画为淡色线。
- `new_part_ids` 画为强调色线。
- 标注、表格、剖面符号由 CAD 渲染器生成。

CAD 路线控制更强，但会失去 Tekla 构件图的模型关联和更新机制，因此不是第一选择。

## Acceptance Criteria

- 对一个 BOX 柱子，离线 pipeline 能输出 `box-assembly-drawing-steps.json/csv/md`。
- 步骤不是按单零件机械分页；内部小零件能按 station/内腔/共享基准合并。
- 外部件按 `spatial_classifications` 中的簇加入，不散件乱排。
- 每个 step 都有 `visible_part_ids`、`new_part_ids`、`part_mark_targets`、`dimension_targets`、`view_hints`。
- 主体顺序包含基准主板、侧壁板/U 形、内部组、盖板、外部簇。
- 证据不足时输出 `REVIEW_REQUIRED` 或 `issue_category=FEATURE/DATA`，不写零件号或构件号特例。
- Tekla POC 至少验证一个 step view 可按 `visible_part_ids` 隐藏/显示 drawing parts，并能插入零件 mark 或输出明确失败原因。
- 如果 Tekla POC 失败，保留同一数据契约转 CAD/DXF 的路径，不重写识别逻辑。

## Verification Plan

1. 单元测试：用最小 BOX fixture 验证基准主板、侧壁板、内部组、盖板和外部簇步骤顺序。
2. 单元测试：验证多个内部小零件在相近 station 且共享基准时合并为一个 `ADD_INTERNAL_GROUP`。
3. 单元测试：验证外部零件使用簇而不是单件散排。
4. 报告测试：验证 offline report 输出 JSON/CSV/Markdown 三类步骤文件，并在 Markdown 中列出步骤摘要。
5. Tekla 2017 POC：用户在 Tekla 中选中一个 BOX 构件后，运行 POC，记录是否能创建/打开构件图、隐藏非本步零件、插入 mark。
6. 验证记录写入 `docs/verification/YYYY-MM-DD-box-column-progressive-drawing-steps.md`。

## Non Goals

- 第一版不追求完全免人工调整的正式构件图。
- 第一版不为每个小零件单独生成整页。
- 第一版不在 Tekla 模型中复制、删除或改造真实零件来模拟步骤状态。
- 第一版不把几何相似候选升级为自动编号匹配。
- 第一版不支持所有截面体系，先只做 BOX 柱子。
