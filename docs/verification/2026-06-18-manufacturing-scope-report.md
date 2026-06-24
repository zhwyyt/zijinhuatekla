# Manufacturing Scope Report Verification

## Scope

验证箱型柱长主壁板的“Excel 制造整板 vs Tekla 分段模型”问题有独立复核出口，不再混入普通缺件或编号漂移。

本轮只做候选归因和报告，不做自动编号匹配、不做自动改号、不确认一一映射。

## Implemented Boundary

- 新增 `src/zijinhua_tekla/quality/manufacturing_scope.py`。
- `pipeline/offline.py` 在对齐后给疑似制造范围问题打 `quality_issue_type_hint=MANUFACTURING_MODEL_SCOPE_MISMATCH`。
- `quality/gate.py` 读取 hint 后将质量问题归入 `MANUFACTURING_MODEL_SCOPE_MISMATCH`。
- `reports/offline.py` 新增：
  - `*-manufacturing-scope-candidates.json`
  - `*-manufacturing-scope-candidates.csv`
- 普通 `missing-candidates` 会跳过已归入制造范围问题的行，避免人工复核方向混乱。

## Verification Commands

```powershell
python -m unittest tests.test_manufacturing_scope
```

结果：3 tests OK。

```powershell
python -m unittest discover -s tests
```

结果：45 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\manufacturing-scope-smoke-20260618
```

## T3 Smoke Result

严格编号状态未改变：

- `MATCH=35`
- `MATCH_CONFLICT=4`
- `DATA_MISSING=23`
- `partPosition=32`
- `derivedFromProfilePart=3`
- `partPositionConflict=4`
- `missing=23`

质量归因分流：

- `DATA_MISSING=22`
- `MANUFACTURING_MODEL_SCOPE_MISMATCH=4`
- `MATCH_CONFLICT=1`

制造范围候选：

- `T3-P-4914`
- `T3-P-4916`
- `T3-P-4917`
- `T3-P-4919`

保留拆板派生：

- `T3-H-558s`
- `T3-H-558x`
- `T3-H-558f`

## Outputs

- `outputs\manufacturing-scope-smoke-20260618\T3-5GKZ-10-manufacturing-scope-candidates.json`
- `outputs\manufacturing-scope-smoke-20260618\T3-5GKZ-10-manufacturing-scope-candidates.csv`
- `outputs\manufacturing-scope-smoke-20260618\T3-5GKZ-10-quality-review-summary.csv`
- `outputs\manufacturing-scope-smoke-20260618\T3-5GKZ-10-analysis.md`

## Current Limitation

制造范围候选当前依据同厚、近似同宽、长主材行和多段板证据聚合。它还没有用构件轴线站位、分段接缝连续性、同一壁板面归属来确认一一映射。

因此本结果只能作为 Data Quality Gate 的复核入口，不能作为自动配送、自动编号或自动出图依据。

## Next

- 人工复核 `T3-P-4914/4916/4917/4919` 的候选段集合。
- 复核确认后写入 Case Bank 回归样例。
- 如人工复核需要更强证据，补导出器字段：构件轴向 station、壁板面编号、分段接缝位置、segment adjacency。
