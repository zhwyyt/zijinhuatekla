# Spatial Pipeline Verification

## Scope

验证 `spatial` 空间关系层已经从旁路诊断接入 `run_offline_analysis`，并进入 `OfflinePipelineResult.spatial_classifications` 与 Markdown 报告摘要。

## Evidence

- 流水线入口：`src/zijinhua_tekla/pipeline/offline.py`
- 空间适配：`src/zijinhua_tekla/spatial_features.py`
- 报告输出：`src/zijinhua_tekla/reports/offline.py`
- 覆盖测试：
  - `tests/test_pipeline_offline.py`
  - `tests/test_reports_offline.py`

## Verification Commands

```powershell
python -m unittest tests.test_pipeline_offline
```

结果：1 test OK。测试 fixture 要求 `run_offline_analysis` 产出 1 个 `Bracket` 空间分类。

```powershell
python -m unittest tests.test_reports_offline
```

结果：1 test OK。测试要求 Markdown 包含 `## 空间关系诊断` 和 `Bracket` 计数。

```powershell
python -m unittest discover -s tests
```

结果：30 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\spatial-pipeline-smoke-20260617
```

结果：

- 输出 `outputs\spatial-pipeline-smoke-20260617\T3-5GKZ-10-alignment.csv`
- 输出 `outputs\spatial-pipeline-smoke-20260617\T3-5GKZ-10-alignment.json`
- 输出 `outputs\spatial-pipeline-smoke-20260617\T3-5GKZ-10-analysis.md`
- JSON 行数：62
- 状态计数：`MATCH=55`、`MATCH_CONFLICT=4`、`DATA_MISSING=3`
- 空间分类：附属件簇 `15`，`Bracket=2`、`Unknown=13`
- Markdown 新增空间摘要：`Unknown=13`、`Bracket=2`

## Acceptance

- `OfflinePipelineResult.spatial_classifications` 由 pipeline 填充。
- 报告层输出空间关系诊断摘要。
- 接入空间层不改变 T3-5GKZ-10 既有 55/4/3 对齐基线。

## Remaining Risk

- 2 个 `Bracket` 仍需人工复核后进入 Case Bank，当前只是算法候选。
- 报告暂时只显示角色计数，后续需要输出簇 ID、证据码和置信度，便于人工确认。
