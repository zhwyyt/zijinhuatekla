# BOX Part Spatial Relation Verification

## Change

本阶段不细分零件角色，只输出 BOX 构件的内外关系层：

- `MAIN_WALL`：已确认的 BOX 主壁板实体，来自 `BOX_MAIN_WALL_CONFIRMED_SET`。
- `INSIDE_BODY`：正常闭合截面样本中落在内腔区域的短局部件。
- `OUTSIDE_ATTACHMENT`：已由空间附属件簇识别为外部 Bracket 的零件。
- `BOUNDARY_OR_THROUGH`：截面上大范围跨越 BOX 轮廓/内腔边界的零件。
- `INSUFFICIENT_EVIDENCE`：缺少可靠截面/侧向/外部簇证据的零件。

`GeometryHints.OuterSideCandidate` 在 `20260623_144836` 中过宽，不能单独作为外侧强判据；当前只作为 `OUTER_SIDE_GEOMETRY_HINT_AUXILIARY` 辅助证据。

## Files

- 新增：`src/zijinhua_tekla/classifiers/box_part_spatial_relations.py`
- 接入：`src/zijinhua_tekla/pipeline/offline.py`
- 报告：`src/zijinhua_tekla/reports/offline.py`
- 测试：`tests/test_box_part_spatial_relations.py`、`tests/test_pipeline_offline.py`、`tests/test_reports_offline.py`

## Verification

已运行：

```powershell
python -m unittest discover -s tests
```

结果：69 tests OK。存在 openpyxl `datetime.utcnow()` DeprecationWarning，为既有 warning，不影响当前测试结果。

真实 T3 smoke：

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_144836 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\box-part-spatial-relations-smoke-20260623-v2
```

新增输出：

- `outputs\box-part-spatial-relations-smoke-20260623-v2\T3-5GKZ-10-box-part-spatial-relations.json`
- `outputs\box-part-spatial-relations-smoke-20260623-v2\T3-5GKZ-10-box-part-spatial-relations.csv`

关系分布：

- `INSUFFICIENT_EVIDENCE=226`
- `MAIN_WALL=16` Tekla 实体；普通零件编号去重仍对应修正后的 13 个主材编号。
- `OUTSIDE_ATTACHMENT=9`，来自已识别外部 Bracket 附属件簇。
- `INSIDE_BODY=8`，来自正常闭合截面样本内腔 trace。

关键样例：

- `T3-P-4917`、`T3-P-4918`、`T3-P-4919`、`T3-P-6284`、`T3-P-5571` 均为 `MAIN_WALL`。
- 旧版保守结果中，`T3-P-4916` 不再误入主板，但曾因未消费 projected centroid 而归为 `INSUFFICIENT_EVIDENCE`；见下方 2026-06-23 更新。

## Remaining Risk

当前正常闭合截面样本只覆盖局部 station，因此只有被样本切到的内部件能稳定进入 `INSIDE_BODY`。大量未采样零件保持 `INSUFFICIENT_EVIDENCE` 是刻意保守行为。下一步应增加更多 station samples 或导出真实外轮廓/内腔侧向关系，逐步把 FEATURE 缺口转为稳定内外关系。
## 2026-06-23 Update: Main Wall Enclosure Projection

用户指出：有了 `MAIN_WALL` 后，BOX 真实围合区域应由主壁板投影轮廓确定；不应只看零件是否被少数 station sample 切到，也不应只看焊接关系。

修正：

- 使用 `mainMaterialEvidence.sectionProjectionEvidence.projectedContour/projectedBounds` 从 `MAIN_WALL` 零件反推真实截面围合区域。
- 对所有零件优先读取自身 `sectionProjectionEvidence.projectedCentroid`。
- projected centroid 在主壁板围合区域内：`INSIDE_BODY`，证据码 `PROJECTED_CENTROID_INSIDE_MAIN_WALL_ENCLOSURE`。
- projected centroid 在主壁板围合区域外：`OUTSIDE_ATTACHMENT`，证据码 `PROJECTED_CENTROID_OUTSIDE_MAIN_WALL_ENCLOSURE`。
- 该判断基于主壁板真实投影围合，不使用构件包围盒。

新增回归测试：

- 未被 `Samples.SectionParts` 采样切到的零件，只要 projected centroid 在主壁板围合区域内，也判为 `INSIDE_BODY`。
- projected centroid 在围合区域外，判为 `OUTSIDE_ATTACHMENT`。

验证：

```powershell
python -m unittest discover -s tests
```

结果：70 tests OK。存在 openpyxl `datetime.utcnow()` DeprecationWarning，为既有 warning。

真实 T3 smoke：

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_144836 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\box-part-spatial-relations-smoke-20260623-v3
```

关系分布更新为：

- `INSIDE_BODY=228`
- `MAIN_WALL=16`
- `OUTSIDE_ATTACHMENT=15`
- `INSUFFICIENT_EVIDENCE=0`

关键变化：

- `T3-P-4916` 从 `INSUFFICIENT_EVIDENCE` 修正为 `INSIDE_BODY`，证据为 `PROJECTED_CENTROID_INSIDE_MAIN_WALL_ENCLOSURE;CONNECTED_TO_MAIN_WALL`。
- 主材集合仍保持去重后 13 个，`T3-P-4918` 在主材集合内。