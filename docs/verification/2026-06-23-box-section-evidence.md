# BOX Section Evidence Verification

## Scope

补 Python 侧 BOX 截面证据层，用现有导出字段先派生内部/外部/壁芯候选证据，不改 C# 导出器。

输入证据：

- `mainMaterialEvidence.bodyFaceId`
- `mainMaterialEvidence.bodyFaceOffset`
- `axisStationStart/End`
- assembly `Weld/Contact` relationships
- part `name/profileString`

## Implemented Boundary

新增 `src\zijinhua_tekla\box_section.py`：

- `classify_box_section_evidence(assembly)`
- 输出每个 part 的：
  - `side`: `WALL_CORE` / `OUTER_ATTACHMENT` / `INNER_STIFFENER_OR_DIAPHRAGM` / `UNKNOWN`
  - `face_id`
  - `body_face_offset`
  - `axis_coverage_ratio`
  - `related_wall_count`
  - `evidence_codes`

现有主材分段输出新增 `evidence_summary.box_section_sides`，用于报告中查看 BOX 内外/壁芯候选证据。

## Test Coverage

新增 `tests\test_box_section_evidence.py`：

- 长轴覆盖板判为 `WALL_CORE`。
- 短小且 offset 明显外侧的关系件判为 `OUTER_ATTACHMENT`。
- 短小、offset 靠内且与多块 wall core 有关系的零件判为 `INNER_STIFFENER_OR_DIAPHRAGM`。

## Verification Commands

```powershell
python -m unittest tests.test_box_section_evidence tests.test_box_main_material_segments tests.test_main_material_segments
```

结果：14 tests OK。

```powershell
python -m unittest tests.test_pipeline_offline tests.test_reports_offline tests.test_box_section_evidence tests.test_main_material_segments tests.test_box_main_material_segments
```

结果：16 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m unittest discover -s tests
```

结果：64 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

## T3 BOX Evidence Snapshot

对 `I:\xingcaisuanfa\cache\20260623_103323` 的 `T3-5GKZ-10` 使用统一主材入口抽样：

- groups：201。
- `box_section_sides` 分布：
  - `INNER_STIFFENER_OR_DIAPHRAGM=168`
  - `WALL_CORE=11`
  - `OUTER_ATTACHMENT=12`
  - `UNKNOWN=8`
  - 混合 side group 2 个。

## Remaining Risk

- 当前是 Python 派生证据，不是 Tekla 导出器原生 `inside/outside` 字段。
- `bodyFaceOffset` 的内外阈值仍是启发式；可用于候选和报告，不应用于最终自动定案。
- 下一步如果要稳定区分 BOX 内外，应在导出器补 `boxSectionEvidence.side/distanceToOuterFace/distanceToInnerFace/isInsideBoxEnvelope/attachedWallFaceIds`。
