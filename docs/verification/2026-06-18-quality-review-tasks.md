# Quality Review Tasks Verification

## Scope

验证 Data Quality Gate 问题已经可以转换为人工复核任务队列，而不是直接污染 Case Bank。该队列用于后续全模型搜索、编号漂移核对、制造/建模口径复核。

## Evidence

- 复核任务模块：`src/zijinhua_tekla/quality/review.py`
- 报告输出：`src/zijinhua_tekla/reports/offline.py`
- CLI 输出：`src/zijinhua_tekla/cli.py`
- 覆盖测试：
  - `tests/test_quality_review.py`
  - `tests/test_reports_offline.py`

## Data Contract

`quality-review-tasks.json` 格式：

```json
{
  "tasks": [
    {
      "task_id": "T3-5GKZ-10:T3-P-3449:DATA_MISSING",
      "member_id": "T3-5GKZ-10",
      "part_name": "T3-P-3449",
      "issue_type": "DATA_MISSING",
      "case_issue_type": "DATA",
      "recommended_action": "全模型搜索候选零件并核对 Excel/模型编号",
      "evidence": "候选证据",
      "evidence_fields": ["part_name", "status", "match_method", "evidence"]
    }
  ]
}
```

## Verification Commands

```powershell
python -m unittest tests.test_quality_review
```

结果：2 tests OK。

```powershell
python -m unittest tests.test_reports_offline
```

结果：1 test OK。

```powershell
python -m unittest discover -s tests
```

结果：36 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\quality-review-smoke-20260618
```

结果输出：

- `outputs\quality-review-smoke-20260618\T3-5GKZ-10-quality-review-tasks.json`

T3 复核任务统计：

- 总任务：`7`
- `DATA_MISSING=3`，建议：`全模型搜索候选零件并核对 Excel/模型编号`
- `MATCH_CONFLICT=4`，建议：`核对同名零件的规格、长度和编号漂移`

## Acceptance

- 质量问题能转换为 `QualityReviewTask`。
- 复核任务能 JSON 保存/加载。
- 报告层输出 `*-quality-review-tasks.json`。
- CLI 打印复核任务路径。
- 复核任务不自动写入 Case Bank，仍需人工确认。

## Remaining Risk

- 任务只给出建议动作，还没有执行全模型搜索。
- `T3-P-4914` 可能属于制造整板 vs Tekla 分段口径，应在复核后升级为专门的制造/建模映射任务。
