# Offline Pipeline Verification

## Scope

验证 `pipeline.offline` 已承接离线分析编排职责，能串联 adapters、features、classifiers、quality，并输出 `OfflinePipelineResult`；CLI 当前只保留参数解析和报告触发。

## Evidence

- 入口模块：`src/zijinhua_tekla/pipeline/offline.py`
- 入口函数：`run_offline_analysis`
- 覆盖测试：`tests/test_pipeline_offline.py`
- CLI 使用：`src/zijinhua_tekla/cli.py` 调用 `run_offline_analysis` 后交给 `reports.offline.write_offline_analysis_report`。

## Verification Commands

```powershell
python -m unittest tests.test_pipeline_offline
```

结果：1 test OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m unittest discover -s tests
```

结果：30 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\pipeline-smoke-20260617
```

结果：

- 输出 `outputs\pipeline-smoke-20260617\T3-5GKZ-10-alignment.csv`
- 输出 `outputs\pipeline-smoke-20260617\T3-5GKZ-10-alignment.json`
- 输出 `outputs\pipeline-smoke-20260617\T3-5GKZ-10-analysis.md`
- JSON 行数：62
- 状态计数：`MATCH=55`、`MATCH_CONFLICT=4`、`DATA_MISSING=3`
- 匹配方式计数：`partPosition=32`、`specLength=17`、`partPositionConflict=4`、`derivedFromProfilePart=3`、`missing=3`、`specLengthPartial=2`、`geometryLoose=1`

## Acceptance

- `run_offline_analysis` 返回统一 `OfflinePipelineResult`。
- CLI 不再直接调用 adapters、rules、features 或 classifiers。
- T3-5GKZ-10 smoke 与既有 55/4/3 基线一致。

## Remaining Risk

- `spatial_classifications` 字段仍未在 pipeline 内填充；下一步应接入 `spatial_features.classify_appendage_clusters_from_bundle`。
- `score_prediction` 仍是 pipeline 内部私有函数，后续可拆成 evaluation/scoring 模块，以便单独演进评分策略。
