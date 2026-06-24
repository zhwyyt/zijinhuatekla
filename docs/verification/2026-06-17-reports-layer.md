# Reports Layer Verification

## Scope

验证 `reports` 包已承接离线 CSV、JSON、Markdown 输出职责，CLI 只负责调用报告层，不再内置报告组装逻辑。

## Evidence

- 新增模块：`src/zijinhua_tekla/reports/offline.py`
- 覆盖测试：`tests/test_reports_offline.py`
- CLI 使用：`src/zijinhua_tekla/cli.py` 构造 `OfflinePipelineResult` 后调用 `write_offline_analysis_report`。

## Verification Commands

```powershell
python -m unittest tests.test_reports_offline
```

结果：1 test OK。

```powershell
python -m unittest discover -s tests
```

结果：27 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\reports-smoke-20260617
```

结果：

- 输出 `outputs\reports-smoke-20260617\T3-5GKZ-10-alignment.csv`
- 输出 `outputs\reports-smoke-20260617\T3-5GKZ-10-alignment.json`
- 输出 `outputs\reports-smoke-20260617\T3-5GKZ-10-analysis.md`
- JSON 行数：62
- 状态计数：`MATCH=55`、`MATCH_CONFLICT=4`、`DATA_MISSING=3`
- 匹配方式计数：`partPosition=32`、`specLength=17`、`partPositionConflict=4`、`derivedFromProfilePart=3`、`missing=3`、`specLengthPartial=2`、`geometryLoose=1`

## Acceptance

- 报告输出层有独立模块和返回路径对象。
- Markdown 汇总继续包含构件结论、命中概览、未匹配行、同名冲突行和复核清单。
- T3-5GKZ-10 smoke 与既有 55/4/3 基线一致。

## Remaining Risk

- Markdown 文案当前仍包含 T3 阶段固化口径，后续应把固化口径从报告层迁到 pipeline/case context 输入，避免报告模块携带业务特例。
