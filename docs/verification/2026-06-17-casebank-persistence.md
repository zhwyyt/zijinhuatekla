# Case Bank Persistence Verification

## Scope

验证 Case Bank 已从内存反馈容器升级为可落盘、可加载、可作为回归输入的数据边界。

## Evidence

- 实现模块：`src/zijinhua_tekla/casebank.py`
- 覆盖测试：`tests/test_casebank_persistence.py`
- 种子案例：`cases/seed.json`

## Data Contract

JSON 格式：

```json
{
  "cases": [
    {
      "case_id": "T3-5GKZ-10:T3-H-558f",
      "issue_type": "SCORING",
      "expected_label": "DERIVED_FROM_PROFILE",
      "human_note": "人工确认说明",
      "evidence_fields": ["profile", "position_suffix", "derived_parent", "match_method"]
    }
  ]
}
```

CSV 字段：

- `case_id`
- `issue_type`
- `expected_label`
- `human_note`
- `evidence_fields`

`evidence_fields` 在 CSV 中用分号分隔。

## Verification Commands

```powershell
python -m unittest tests.test_casebank_persistence
```

结果：4 tests OK。

```powershell
python -m unittest discover -s tests
```

结果：34 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

## Acceptance

- `CaseBank.save_json` / `CaseBank.load_json` 可往返。
- `CaseBank.save_csv` / `CaseBank.load_csv` 可往返。
- `CaseBank.add` 会拒绝没有 `evidence_fields` 的反馈，避免人工确认缺少回归证据。
- `cases/seed.json` 可加载，并包含已确认的 `T3-H-558s/x/f` 来自 `BH400*200*7*10` 拆板派生口径。

## Important Boundary

T3 空间诊断中的 2 个 `Bracket` 目前仍是算法候选，没有写入 seed 作为已确认案例。它们需要人工复核后再进入 Case Bank。

## Remaining Risk

- 当前 Case Bank 只管理反馈数据，还没有接入 pipeline 的自动回归校验流程。
- 后续需要为 Bracket 候选补 `cluster_id`、证据码、置信度和人工标签后再固化。
