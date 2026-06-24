# Station Continuity Evidence Verification

## Scope

验证制造范围候选报告新增轴向 station 与连续性证据，用于推进“人工确认主材分段集合”到可解释自动分组。

本轮不改变严格编号规则，不自动改号，不把制造范围候选段当作 Excel 零件的自动匹配成功。

## Implemented Boundary

- `ManufacturingScopeCandidate` 新增候选级证据字段：
  - `station_ranges`
  - `continuity_gaps`
  - `continuity_level`
- `flatten_manufacturing_scope_report` 将上述字段输出到 CSV，方便 Excel 人工筛查。
- station 证据基于现有 Tekla 导出字段推导：`centroid`、`plateLongDirection`、名义板长。
- 如果分段 station 区间相互重叠，输出 `continuity_level=AXIS_OVERLAP_NEEDS_FACE_GROUPING`，表示需要补壁板面/主材面归属，不能只凭轴向连续性自动确认同一整板分段。

## Verification Commands

```powershell
python -m unittest tests.test_manufacturing_scope
```

结果：7 tests OK。

```powershell
python -m unittest discover -s tests
```

结果：50 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\station-continuity-smoke-20260623
```

## T3 Smoke Result

输出文件：

- `outputs\station-continuity-smoke-20260623\T3-5GKZ-10-manufacturing-scope-candidates.json`
- `outputs\station-continuity-smoke-20260623\T3-5GKZ-10-manufacturing-scope-candidates.csv`

真实 T3 数据中 4 个制造范围候选均带 station 证据：

- `T3-P-4914`
- `T3-P-4916`
- `T3-P-4917`
- `T3-P-4919`

同时 4 个候选均输出：

- `confirmation_level=HUMAN_CONFIRMED_SEGMENT_GROUP`
- `continuity_level=AXIS_OVERLAP_NEEDS_FACE_GROUPING`

这说明当前候选段在构件轴向上存在重叠，符合“多块壁板面/主材面沿同一柱轴并行分段”的风险。下一步必须补壁板面编号、主材面归属或截面 face evidence，才能把人工确认集合升级为自动分组。

## Remaining Risk

- station 只能证明沿构件轴向的区间关系，不能单独证明同一壁板面。
- 当前还没有输出壁板面编号、截面 face id、接缝位置与相邻关系。
- 因此本轮字段仍属于 Data Quality Gate 复核证据，不进入自动配送、自动组立、自动出图结论。


