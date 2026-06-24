# Conflict Candidates Report Verification

## Scope

验证 `MATCH_CONFLICT` 质量问题已经有只读复核报告。报告同时保留：

- `conflict_parts`：与 Excel 零件号同名但规格/长度明显冲突的 Tekla 实体。
- `geometry_review_candidates`：排除同名冲突实体后，在全模型中按几何接近程度找到的复核候选。

本轮不自动把候选改成匹配结果，不写入 Case Bank。

## Evidence

- 候选报告构建：`src/zijinhua_tekla/quality/candidates.py`
- 报告输出：`src/zijinhua_tekla/reports/offline.py`
- CLI 路径打印：`src/zijinhua_tekla/cli.py`
- 覆盖测试：
  - `tests/test_quality_candidate_search.py`
  - `tests/test_reports_offline.py`

## Output Contract

新增输出：

- `*-conflict-candidates.json`
- `*-conflict-candidates.csv`

CSV 字段包括：

- `task_id`
- `member_id`
- `part_name`
- `spec`
- `length`
- `conflict_count`
- `geometry_review_candidate_count`
- `candidate_kind`
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

`candidate_kind` 当前取值：

- `conflict_part`：同名冲突实体。
- `geometry_review_candidate`：几何接近的复核候选，不表示自动改号。

## Verification Commands

```powershell
python -m unittest tests.test_quality_candidate_search tests.test_reports_offline
```

结果：4 tests OK。

```powershell
python -m unittest discover -s tests
```

结果：41 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\conflict-candidates-report-smoke-20260618
```

结果新增：

- `outputs\conflict-candidates-report-smoke-20260618\T3-5GKZ-10-conflict-candidates.json`
- `outputs\conflict-candidates-report-smoke-20260618\T3-5GKZ-10-conflict-candidates.csv`

T3 结果：

- `T3-P-4916`：同名冲突实体 `72806770`，无 geometry review candidate。
- `T3-P-4917`：同名冲突实体 `72806751`、`72806761`，无 geometry review candidate。
- `T3-P-4919`：同名冲突实体 `72806723`，无 geometry review candidate。
- `T3-P-6243`：同名冲突实体 `72807307`、`72808211`；geometry review candidates 为 `T3-P-6368/72806134`、`T3-P-6366/72806245`、`T3-P-6366/72806275`、`T3-P-6366/72806462`、`T3-P-6367/72806164`。

## Acceptance

- 常规 analyze 输出冲突候选 JSON/CSV。
- 同名冲突实体保留定位和规格/长度差值。
- 几何复核候选排除同名冲突实体。
- 搜索结果只作为质量复核证据，不污染分类规则。

## Remaining Risk

- 目前仍需要人工判断 geometry review candidate 是否说明制造/建模口径差异或导出范围问题。
- `T3-P-4916/4917/4919` 可能属于制造整板 vs Tekla 分段映射，不应被普通编号漂移报告硬修。
