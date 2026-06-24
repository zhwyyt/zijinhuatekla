# Spatial Candidate Report Verification

## Scope

验证报告层已输出可人工复核的空间分类明细，而不只是角色计数。该明细用于后续将人工确认的 Bracket 候选沉淀到 Case Bank。

## Evidence

- 实现模块：`src/zijinhua_tekla/reports/offline.py`
- CLI 输出：`src/zijinhua_tekla/cli.py`
- 覆盖测试：`tests/test_reports_offline.py`

## Output Files

`write_offline_analysis_report` 当前输出五份文件：

- `*-alignment.csv`
- `*-alignment.json`
- `*-spatial-classifications.csv`
- `*-spatial-classifications.json`
- `*-analysis.md`

空间分类明细字段：

- `cluster_id`
- `role`
- `confidence`
- `evidence_codes`
- `missing_codes`

## Verification Commands

```powershell
python -m unittest tests.test_reports_offline
```

结果：1 test OK。

```powershell
python -m unittest discover -s tests
```

结果：34 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\spatial-detail-cli-smoke-20260617
```

结果输出五份文件：

- `outputs\spatial-detail-cli-smoke-20260617\T3-5GKZ-10-alignment.csv`
- `outputs\spatial-detail-cli-smoke-20260617\T3-5GKZ-10-alignment.json`
- `outputs\spatial-detail-cli-smoke-20260617\T3-5GKZ-10-spatial-classifications.csv`
- `outputs\spatial-detail-cli-smoke-20260617\T3-5GKZ-10-spatial-classifications.json`
- `outputs\spatial-detail-cli-smoke-20260617\T3-5GKZ-10-analysis.md`

T3 Bracket 候选明细：

| cluster_id | role | confidence | evidence_codes | missing_codes |
| --- | --- | --- | --- | --- |
| `72805757:5` | `Bracket` | `0.94` | `OVERHANG_DOMINANT;AXIS_SPAN_LIMITED;EXTERNAL_CENTROID;NOT_END_CONNECTION` | `ROOT_LOCAL_ATTACHMENT` |
| `72805757:6` | `Bracket` | `0.94` | `OVERHANG_DOMINANT;AXIS_SPAN_LIMITED;EXTERNAL_CENTROID;NOT_END_CONNECTION` | `ROOT_LOCAL_ATTACHMENT` |

## Acceptance

- 报告路径对象包含 spatial CSV/JSON 路径。
- CLI 打印 spatial CSV/JSON 路径。
- Markdown 包含 `Bracket 候选` 明细。
- T3 的 2 个 Bracket 候选可被人工复核。

## Remaining Risk

- 这两个 Bracket 仍是候选，不是已确认 Case Bank 样例。
- 当前明细没有列出 cluster 内部零件号；如果人工复核需要定位模型零件，下一步应把 cluster part ids 输出到 spatial 明细。
