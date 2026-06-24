# Spatial Candidate Part Ids Verification

## Scope

验证空间候选明细已包含 cluster 内部 Tekla part ids，使 Bracket 候选可以在模型中定位并人工复核。

## Evidence

- 空间特征：`src/zijinhua_tekla/spatial_features.py`
- 分类对象：`src/zijinhua_tekla/bracket_classifier.py`
- 报告输出：`src/zijinhua_tekla/reports/offline.py`
- 覆盖测试：
  - `tests/test_spatial_features.py`
  - `tests/test_reports_offline.py`

## Verification Commands

```powershell
python -m unittest tests.test_spatial_features
```

结果：3 tests OK。

```powershell
python -m unittest tests.test_reports_offline
```

结果：1 test OK。

```powershell
python -m unittest discover -s tests
```

结果：34 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\spatial-partids-smoke-20260617
```

结果输出：

- `outputs\spatial-partids-smoke-20260617\T3-5GKZ-10-spatial-classifications.csv`
- `outputs\spatial-partids-smoke-20260617\T3-5GKZ-10-spatial-classifications.json`
- `outputs\spatial-partids-smoke-20260617\T3-5GKZ-10-analysis.md`

T3 Bracket 候选定位明细：

| cluster_id | part_ids | role | confidence | evidence_codes | missing_codes |
| --- | --- | --- | --- | --- | --- |
| `72805757:5` | `71163864` | `Bracket` | `0.94` | `OVERHANG_DOMINANT;AXIS_SPAN_LIMITED;EXTERNAL_CENTROID;NOT_END_CONNECTION` | `ROOT_LOCAL_ATTACHMENT` |
| `72805757:6` | `71170394;71170452;71170471;71460728;71460737;71460746;71460755;71460764` | `Bracket` | `0.94` | `OVERHANG_DOMINANT;AXIS_SPAN_LIMITED;EXTERNAL_CENTROID;NOT_END_CONNECTION` | `ROOT_LOCAL_ATTACHMENT` |

## Acceptance

- `AppendageClusterFeatures` 保留 `part_ids`。
- `AppendageRoleClassification` 保留 `part_ids`。
- spatial CSV/JSON 输出 `part_ids`。
- Markdown Bracket 候选摘要输出零件集合。

## Remaining Risk

- `ROOT_LOCAL_ATTACHMENT` 仍缺失，说明当前 root/contact 证据可能不够细。人工复核后决定是调整评分，还是补 C# 导出器 root/contact/overhang 精细字段。
