# Quality Review Summary Verification

## Scope

验证质量复核任务可以按 `issue_type + recommended_action` 聚合为摘要，作为后续全模型搜索、编号漂移报告、制造/建模口径复核的稳定入口。

## Evidence

- 摘要契约：`src/zijinhua_tekla/quality/review.py`
- 报告输出：`src/zijinhua_tekla/reports/offline.py`
- CLI 路径打印：`src/zijinhua_tekla/cli.py`
- 覆盖测试：
  - `tests/test_quality_review.py`
  - `tests/test_reports_offline.py`

## Data Contract

`quality-review-summary.json/csv` 字段：

- `issue_type`
- `recommended_action`
- `task_count`
- `part_names`

`part_names` 使用 `;` 分隔，只作为人工复核索引，不替代明细任务。

## Verification Commands

```powershell
python -m unittest tests.test_quality_review tests.test_reports_offline
```

结果：5 tests OK。

```powershell
python -m unittest discover -s tests
```

结果：38 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\quality-review-summary-smoke-20260618
```

结果新增：

- `outputs\quality-review-summary-smoke-20260618\T3-5GKZ-10-quality-review-summary.json`
- `outputs\quality-review-summary-smoke-20260618\T3-5GKZ-10-quality-review-summary.csv`

T3 摘要：

- `DATA_MISSING=3`：`T3-P-3449;T3-P-4910;T3-P-4914`
- `MATCH_CONFLICT=4`：`T3-P-4916;T3-P-4917;T3-P-4919;T3-P-6243`

## Acceptance

- 质量复核任务可稳定聚合为摘要。
- 离线报告同时输出 `*-quality-review-summary.json` 和 `*-quality-review-summary.csv`。
- CLI 打印摘要路径。
- 摘要只组织复核入口，不自动写入 Case Bank，也不改变分类规则。

## Remaining Risk

- 摘要尚未执行全模型候选搜索。
- `T3-P-4914` 仍可能需要升级为制造整板 vs Tekla 分段映射案例。
