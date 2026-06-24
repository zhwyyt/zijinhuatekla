# Quality Review Tasks CSV Verification

## Scope

验证 Data Quality Gate 复核任务除了 JSON 机器契约外，也能输出 CSV，便于人工用 Excel 筛查缺失件、同名冲突和后续编号漂移候选。

## Evidence

- 复核任务 CSV 契约：`src/zijinhua_tekla/quality/review.py`
- 报告输出：`src/zijinhua_tekla/reports/offline.py`
- CLI 路径打印：`src/zijinhua_tekla/cli.py`
- 覆盖测试：
  - `tests/test_quality_review.py`
  - `tests/test_reports_offline.py`

## Data Contract

`quality-review-tasks.csv` 字段：

- `task_id`
- `member_id`
- `part_name`
- `issue_type`
- `case_issue_type`
- `recommended_action`
- `evidence`
- `evidence_fields`

其中 `evidence_fields` 使用 `;` 分隔，保持 CSV 对人工友好；JSON 仍保留数组结构，作为机器契约。

## Verification Commands

```powershell
python -m unittest tests.test_quality_review tests.test_reports_offline
```

结果：4 tests OK。

```powershell
python -m unittest discover -s tests
```

结果：37 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\quality-review-csv-smoke-20260618
```

结果新增：

- `outputs\quality-review-csv-smoke-20260618\T3-5GKZ-10-quality-review-tasks.csv`

CSV 统计：

- 总任务：`7`
- `DATA_MISSING=3`
- `MATCH_CONFLICT=4`

## Acceptance

- 质量复核任务可保存/加载 CSV。
- 离线报告同时输出 `*-quality-review-tasks.json` 和 `*-quality-review-tasks.csv`。
- CLI 打印 CSV 路径，人工复核不需要猜输出文件名。
- CSV 只是复核视图，不自动写入 Case Bank。

## Remaining Risk

- CSV 仍只是任务清单，不执行全模型搜索。
- `T3-P-4914` 一类制造整板 vs Tekla 分段口径仍需要单独建映射边界。
