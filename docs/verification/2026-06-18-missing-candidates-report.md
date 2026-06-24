# Missing Candidates Report Verification

## Scope

验证缺失零件全模型候选搜索已经接入离线报告。常规 `analyze` 输出现在会同时生成 `missing-candidates.json/csv`，供人工核对缺失件是否存在于其他 assembly、是否存在编号漂移或 Excel/模型口径差异。

本轮仍保持只读：不改变 `prediction_status`，不自动匹配，不写入 Case Bank。

## Evidence

- pipeline 结果携带完整 bundle：`src/zijinhua_tekla/pipeline/offline.py`
- adapter 返回完整 bundle：`src/zijinhua_tekla/adapters/offline.py`
- 候选报告构建：`src/zijinhua_tekla/quality/candidates.py`
- 报告输出：`src/zijinhua_tekla/reports/offline.py`
- CLI 路径打印：`src/zijinhua_tekla/cli.py`
- 覆盖测试：
  - `tests/test_quality_candidate_search.py`
  - `tests/test_reports_offline.py`
  - `tests/test_pipeline_offline.py`
  - `tests/test_adapters_offline.py`

## Output Contract

新增输出：

- `*-missing-candidates.json`
- `*-missing-candidates.csv`

CSV 字段包括：

- `task_id`
- `member_id`
- `part_name`
- `spec`
- `length`
- `candidate_count`
- `assembly_id`
- `part_id`
- `part_position`
- `name`
- `profile`
- `match_level`
- `score`
- `length_delta`
- `width_delta`
- `thickness_delta`

没有候选的缺失任务也会保留一行，`candidate_count=0`，方便人工筛查。

## Verification Commands

```powershell
python -m unittest tests.test_quality_candidate_search tests.test_reports_offline tests.test_pipeline_offline tests.test_architecture_skeleton
```

结果：7 tests OK。

```powershell
python -m unittest discover -s tests
```

结果：40 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\missing-candidates-report-smoke-20260618
```

结果新增：

- `outputs\missing-candidates-report-smoke-20260618\T3-5GKZ-10-missing-candidates.json`
- `outputs\missing-candidates-report-smoke-20260618\T3-5GKZ-10-missing-candidates.csv`

T3 结果：

- `T3-P-3449`：`PL30*100`，长 `978`，候选数 `0`
- `T3-P-4910`：`PL16*200`，长 `158`，候选数 `1`，近似候选 `T3-P-4894` / `part_id=72805808` / `GEOMETRY_NEAR`
- `T3-P-4914`：`PL16*968`，长 `10534`，候选数 `0`

## Acceptance

- 常规 analyze 输出缺失候选 JSON/CSV。
- 候选搜索覆盖完整 bundle，而不只目标 assembly。
- 没有候选的任务也保留复核行。
- CLI 打印新输出路径。
- 搜索结果只作为质量复核证据，不污染分类规则。

## Remaining Risk

- 同名冲突/编号漂移还没有专门候选报告。
- `T3-P-4914` 很可能属于制造整板 vs Tekla 分段映射，不能用普通缺件候选硬凑。
