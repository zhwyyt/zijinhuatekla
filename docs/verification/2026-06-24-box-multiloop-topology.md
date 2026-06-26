# BOX Multi-Loop Topology Verification

## Change

BOX 内外关系层从 station 主壁板点集凸包升级为 Shapely 多 loop 拓扑：

- 新增依赖 `shapely`。
- 每个 station 使用已确认主壁板 `partLoops` 构建壁板截面 polygon。
- 对主壁板截面 polygon 做 `unary_union`，再用正负 buffer 做小缝闭合修复。
- 输出 station topology：`outer_loop`、`inner_loops`、`geometry`、`cavity_geometries`。
- 点判定优先走 Shapely：边界、cavity、inside、outside；不再用凸包抹平凹形。
- 当最近 station 没闭合 inner loop 时，允许在面积接近的情况下用参考 outer loop 复核 inside；不覆盖真实变窄 station 的 mixed/outside 结果。

## Files

- `pyproject.toml`
- `src/zijinhua_tekla/classifiers/box_part_spatial_relations.py`
- `tests/test_box_part_spatial_relations.py`

## Unit Verification

```powershell
python -m unittest discover -s tests
```

结果：75 tests OK。存在 openpyxl `datetime.utcnow()` DeprecationWarning，为既有 warning。

新增回归覆盖：

- 凹形 outer loop 不能被凸包误判为 inside。
- 四块主壁板围成的 inner/cavity loop 显式标记 `POINT_IN_CAVITY_LOOP`，并按 BOX 真实围合区域归为 `INSIDE_BODY`。
- start/mid/end station 判断不一致仍归为 `BOUNDARY_OR_THROUGH`。

## T3 Smoke

```powershell
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260624_092738 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\box-multiloop-topology-smoke-20260624-v6
```

结果摘要：

- `MAIN_WALL=16` Tekla 实体，去重后仍为 13 个主材编号：
  `T3-P-4917,T3-P-4918,T3-P-4919,T3-P-5571,T3-P-5576,T3-P-5577,T3-P-5579,T3-P-6268,T3-P-6269,T3-P-6270,T3-P-6271,T3-P-6284`
- `T3-GG-2` 8 个实体仍全部为 `OUTSIDE_ATTACHMENT`。
- 关系分布：`OUTSIDE_ATTACHMENT=115`、`INSIDE_BODY=87`、`MAIN_WALL=16`、`BOUNDARY_OR_THROUGH=41`。
- `SHAPELY_BOX_SECTION_TOPOLOGY` 证据 202 条。
- `POINT_IN_CAVITY_LOOP` 证据 86 条，且均为 `INSIDE_BODY`。

## Remaining Risk

本轮已经移除凸包作为主判据，但真实 T3 的部分 station 仍无法由当前 `partLoops` 稳定闭合出 inner/cavity loop。新算法比旧凸包口径更严格，因此 `INSIDE_BODY` 数量从旧 smoke 的 185 降到 87，`BOUNDARY_OR_THROUGH` 增加到 41。此变化不应直接视为业务最终正确，需要下一步继续补导出器或 Python 侧 topology 证据：

- station loop 应显式区分外边界边、内腔边、板材料边。
- 对每个 station 输出闭合失败原因和缺口尺度。
- 对零件 start/mid/end 输出逐点 station topology 明细，便于人工复核漂移来源。

当前可确认的稳定点：主板 13 个集合未漂移，`T3-GG-2` 外部判断未回退，且凹形/inner loop 不再由凸包误判。
