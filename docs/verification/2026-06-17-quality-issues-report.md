# Quality Issues Report Verification

## Scope

验证 Data Quality Gate 的问题明细已输出为 CSV/JSON，后续缺失/冲突零件复核工具可以直接消费，而不是只能从 Markdown 文本中读取。

## Evidence

- 质量闸门：`src/zijinhua_tekla/quality/gate.py`
- 报告输出：`src/zijinhua_tekla/reports/offline.py`
- CLI 输出：`src/zijinhua_tekla/cli.py`
- 覆盖测试：`tests/test_reports_offline.py`

## Output Files

`write_offline_analysis_report` 当前输出：

- `*-quality-issues.csv`
- `*-quality-issues.json`

质量问题字段：

- `issue_type`
- `part_name`
- `status`
- `match_method`
- `evidence`

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
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\quality-issues-smoke-20260617
```

结果输出：

- `outputs\quality-issues-smoke-20260617\T3-5GKZ-10-quality-issues.csv`
- `outputs\quality-issues-smoke-20260617\T3-5GKZ-10-quality-issues.json`

T3 质量问题统计：

- 总问题：`7`
- `DATA_MISSING=3`
- `MATCH_CONFLICT=4`

前三个 `DATA_MISSING`：

- `T3-P-3449`
- `T3-P-4910`
- `T3-P-4914`

## Acceptance

- 报告路径对象包含 quality CSV/JSON。
- CLI 打印 quality CSV/JSON 路径。
- Markdown 输出文件列表包含 Quality Issues CSV/JSON。
- T3 质量问题明细与既有 3 缺失、4 冲突基线一致。

## Remaining Risk

- 当前只导出质量问题，还没有自动全模型搜索复核工具。
- `T3-P-4914` 属于制造整板 vs Tekla 分段口径，后续应进入专门的制造/建模口径映射，而不是作为普通缺件处理。
