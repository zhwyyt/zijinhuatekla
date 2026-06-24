# Missing Candidate Search Verification

## Scope

验证缺失零件复核已经有只读候选搜索内核：输入 Excel 行和 Tekla bundle，全模型扫描 assemblies 下的 parts，按规格、长度、板宽、板厚计算候选排序。

本轮只建立搜索内核和验证样例，不自动改变 `prediction_status`，也不写入 Case Bank。

## Evidence

- 候选搜索模块：`src/zijinhua_tekla/quality/candidates.py`
- 覆盖测试：`tests/test_quality_candidate_search.py`
- T3 smoke 输出：`outputs\candidate-search-smoke-20260618\T3-5GKZ-10-missing-candidates.json`

## Candidate Contract

候选字段：

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

`match_level` 当前分为：

- `GEOMETRY_EXACT`：规格与长度接近加工尺寸，可作为强候选。
- `GEOMETRY_NEAR`：规格/几何接近，但仍需人工核对。

## Verification Commands

```powershell
python -m unittest tests.test_quality_candidate_search
```

结果：1 test OK。

```powershell
python -m unittest discover -s tests
```

结果：39 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

T3 只读 smoke：

```powershell
@'
import json
from pathlib import Path
from zijinhua_tekla.adapters.offline import load_truth_rows
from zijinhua_tekla.quality.candidates import search_missing_part_candidates

root = Path(r'I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1')
truth_root = Path(r'I:\xingcaisuanfa\cache\20260615_161938')
member_id = 'T3-5GKZ-10'
review_path = Path(r'I:\zijinhuatekla\outputs\quality-review-summary-smoke-20260618\T3-5GKZ-10-quality-review-tasks.json')
out_dir = Path(r'I:\zijinhuatekla\outputs\candidate-search-smoke-20260618')
out_dir.mkdir(parents=True, exist_ok=True)

bundle = json.loads((root / 'tekla-body-bracket-export.bundle.json').read_text(encoding='utf-8'))
rows_by_name = {row['零件名称']: row for row in load_truth_rows(truth_root, member_id)}
tasks = json.loads(review_path.read_text(encoding='utf-8'))['tasks']
results = []
for task in tasks:
    if task['issue_type'] != 'DATA_MISSING':
        continue
    row = rows_by_name[task['part_name']]
    candidates = search_missing_part_candidates(row, bundle, limit=5)
    results.append({
        'task_id': task['task_id'],
        'part_name': task['part_name'],
        'candidate_count': len(candidates),
        'candidates': [candidate.to_dict() for candidate in candidates],
    })

(out_dir / f'{member_id}-missing-candidates.json').write_text(
    json.dumps(results, ensure_ascii=False, indent=2),
    encoding='utf-8',
)
'@ | python -
```

T3 结果：

- `T3-P-3449`：候选数 `0`
- `T3-P-4910`：候选数 `1`，近似候选 `assembly=72805757`、`part_id=72805808`、`part_position=T3-P-4894`、`profile=PL16*200`、`match_level=GEOMETRY_NEAR`
- `T3-P-4914`：候选数 `0`

## Acceptance

- 候选搜索复用现有规格/板件尺寸规则，不新增按项目号或零件号写死的规则。
- 搜索范围可覆盖 bundle 全部 assemblies。
- 搜索结果保留定位字段和差值证据。
- 搜索结果只作为复核证据，不改变分类结果。

## Remaining Risk

- 尚未接入离线报告输出。
- 尚未处理同名冲突/编号漂移候选。
- `T3-P-4914` 仍可能属于制造整板 vs Tekla 分段映射，不应被普通候选搜索硬凑。
