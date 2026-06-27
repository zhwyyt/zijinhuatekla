# Composite Main Material Segments

## Scope

本设计用于识别由多个截面体系沿构件主轴组合而成的复杂构件主材，例如下部为十字柱并带外侧翼缘板、上部为 BOX 的构件。

目标不是为某一个构件号写特例，而是建立通用口径：同一根构件可以沿轴向被切成多个截面体系区段，每个区段独立识别主板/主材，再汇总为构件级主材轨迹。

## Business Semantics

主材不再等同于单一 `BOX_MAIN_WALL_CONFIRMED_SET`。主材定义为：在某个轴向区段内参与主体截面体系、承担构件主体形态和加工配送口径的连续板件。

下部十字柱外侧翼缘板属于主板/主材，不是附件或普通加强板。它们在十字柱稳定区段中的主角色为 `CROSS_FLANGE_MAIN_PLATE`。

过渡段允许保留多种体系解释，但每个区段内每块板只能有一个主角色。其他参与关系写入辅助解释，避免同一行同时声明多个主身份。

## Segment Model

沿构件主轴读取多个 station 的截面证据，不预设固定三段。每个 station 先识别截面状态，再把相邻、稳定、同类的 station 合并成 N 个 `regime segment`。

常见区段类型：

- `CROSS_CORE_WITH_FLANGES`: 十字柱主体稳定区段，包含十字核心板和外侧翼缘主板。
- `CROSS_TO_BOX_TRANSITION`: 十字柱向 BOX 收口或转换的过渡区段。
- `PARTIAL_BOX_FORMING`: BOX 外轮廓开始形成但尚未稳定闭合的区段。
- `BOX_CLOSED_SECTION`: 稳定闭合 BOX 区段。
- `END_OR_NODE_ZONE`: 端部、节点、局部附件触发的非稳定主体区段。
- `MIXED_OR_INSUFFICIENT_EVIDENCE`: 证据不足或多体系混合但无法稳定归类的区段。

切段触发条件：

- 主体截面拓扑变化，例如十字、H、BOX、闭合环、开口环之间变化。
- 主板参与关系变化，例如某块长板开始或结束参与主体截面。
- 外轮廓或内腔变化，例如 BOX cavity 从不存在、局部形成到稳定闭合。
- 翼缘/腹板体系变化，例如十字核心和外侧翼缘是否稳定出现。
- 过渡区多体系重叠，不能硬归入单一 BOX 或单一十字柱。

## Primary Role Rules

每个 `regime segment` 内，每块主材板只输出一个 `primary_role`。如果一块板同时具有多种体系解释，以当前区段主体截面体系和结构连续主线确定主角色，其他解释写入 `secondary_evidence`。

建议角色：

- `CROSS_CORE_MAIN_PLATE`: 十字柱核心主体板。
- `CROSS_FLANGE_MAIN_PLATE`: 十字柱外侧翼缘主板。
- `BOX_MAIN_WALL_PLATE`: 稳定闭合 BOX 外壁主板。
- `BOX_FORMING_MAIN_PLATE`: 过渡或局部形成 BOX 外轮廓的主体板。
- `TRANSITION_MAIN_PLATE`: 过渡区内连续参与主体转换的主板。
- `END_NODE_MAIN_PLATE_CANDIDATE`: 端部或节点区域的主体候选，默认需要复核。

主角色优先级：

1. 稳定区段优先使用当前区段的主体截面体系。
2. 过渡区段按结构连续主线确定主角色。
3. 无法稳定确定主角色时，不强行升级为主板，进入复核候选。

辅助解释示例：

```json
{
  "partPosition": "EXAMPLE-P-001",
  "segment_type": "CROSS_TO_BOX_TRANSITION",
  "primary_role": "BOX_FORMING_MAIN_PLATE",
  "secondary_evidence": [
    "continues_from_lower_cross_column",
    "overlaps_with_cross_flange_system"
  ]
}
```

## Evidence Inputs

优先使用 Tekla 导出的截面证据：

- `metadata.memberAxisEvidence`
- `metadata.boxSectionEvidence.stationLoops[].sectionLoops`
- `metadata.boxSectionEvidence.stationLoops[].sectionSegments`
- `metadata.hBeamSectionEvidence.stationFrames[].partSlices`
- part 级 `mainMaterialEvidence.axisStationStart/End`
- part 级 `mainMaterialEvidence.sectionProjectionEvidence`

厚度、长度、profile 和零件名称只能作为辅助解释或排序证据，不作为单独强判据。

## Output Contract

新增通用输出建议名：`composite-main-material-segments.json/csv`。旧的 `box-main-material-segment-groups` 可保留为 BOX 专项兼容输出，但复杂构件最终口径应以 composite 输出为准。

JSON 顶层建议结构：

```json
{
  "assembly_id": "string",
  "member_id": "string",
  "source": "compositeMainMaterialSegments.v1",
  "segments": [
    {
      "segment_id": "S1",
      "station_start": 0.0,
      "station_end": 1000.0,
      "segment_type": "CROSS_CORE_WITH_FLANGES",
      "confidence": 0.0,
      "main_plates": [
        {
          "part_id": "string",
          "part_position": "string",
          "primary_role": "CROSS_FLANGE_MAIN_PLATE",
          "secondary_evidence": [],
          "evidence_codes": []
        }
      ]
    }
  ],
  "part_traces": [
    {
      "part_id": "string",
      "part_position": "string",
      "segments": ["S1", "S2"],
      "primary_roles": ["CROSS_FLANGE_MAIN_PLATE", "TRANSITION_MAIN_PLATE"]
    }
  ]
}
```

## Acceptance Criteria

- 对由多个截面体系组成的构件，不再只输出一个 BOX 主材集合代表全部主材。
- 输出可包含 N 个轴向区段，不预设固定段数。
- 下部十字柱外侧翼缘板在稳定十字柱区段中被识别为主材，角色为 `CROSS_FLANGE_MAIN_PLATE`。
- 稳定 BOX 区段继续识别闭合 BOX 外壁主板，角色为 `BOX_MAIN_WALL_PLATE`。
- 过渡区段内每块板只给一个 `primary_role`，另一体系关系进入 `secondary_evidence`。
- 证据不足时输出 `MIXED_OR_INSUFFICIENT_EVIDENCE` 或候选复核，不写构件号、零件号、项目名特例。
- 旧普通零件精准编号匹配和制造/建模口径差异规则不变。

## Verification Plan

1. 为 station 状态识别新增最小单元测试：稳定 BOX、稳定十字柱带翼缘、过渡段、证据不足。
2. 为区段合并新增测试：截面状态连续时合并，状态变化时切分为多个区段。
3. 为主角色分配新增测试：十字柱外侧翼缘板输出 `CROSS_FLANGE_MAIN_PLATE`，过渡段单主角色加辅助解释。
4. 用当前 Tekla 选择集 `T2-3GKZ-12` 做 smoke：报告应输出多个 composite segments，而不是只用 `BOX_MAIN_WALL_CONFIRMED_SET` 表达完整主材。
5. 回归既有 BOX 样例，确保稳定 BOX 构件仍可输出 `BOX_MAIN_WALL_PLATE`，且旧 BOX 专项测试不被破坏。
6. 回归 H/GL station slice 样例，确保 composite 逻辑不把 H/GL 主板规则退回到名称或 PartRoles 硬判。

## Non Goals

- 本设计不在导出器中直接声明主材角色；导出器只提供可复核的截面、station、loop、slice 证据。
- 本设计不解决完整加工工序、装焊顺序或配送顺序。
- 本设计不把几何相似候选升级为自动编号匹配。
