# Strict Numbering And Split Plate Verification

## Scope

验证普通零件编号必须与 Tekla `partPosition` 精准一致；几何相似、规格相似、长度相近不能自动替代编号匹配。拆板/派生加工件保留为独立制造口径映射，不归入编号漂移或几何猜测。

## Rules

- 普通零件：只允许 exact `partPosition` 自动匹配。
- 同名但规格/长度冲突：进入 `MATCH_CONFLICT`。
- 不同名但几何相似：进入 `DATA_MISSING`，候选只在复核报告里展示。
- 拆板派生：必须由母件名、母件 profile、后缀语义和尺寸证据证明，匹配方式为 `derivedFromProfilePart`。

## Evidence

- 核心规则：`src/zijinhua_tekla/rules.py`
- 复核候选：`src/zijinhua_tekla/quality/candidates.py`
- 复核任务文案：`src/zijinhua_tekla/quality/review.py`
- 项目硬规则：`AGENTS.md`
- 覆盖测试：
  - `tests/test_rules.py`
  - `tests/test_quality_candidate_search.py`
  - `tests/test_reports_offline.py`
  - `tests/test_quality_review.py`

## Verification Commands

```powershell
python -m unittest tests.test_rules
```

结果：6 tests OK。

```powershell
python -m unittest discover -s tests
```

结果：42 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\strict-numbering-smoke-20260618
```

T3 严格编号结果：

- `MATCH=35`
- `MATCH_CONFLICT=4`
- `DATA_MISSING=23`
- `partPosition=32`
- `derivedFromProfilePart=3`
- `partPositionConflict=4`
- `missing=23`

保留的拆板派生：

- `T3-H-558s`
- `T3-H-558x`
- `T3-H-558f`

## Acceptance

- 不同编号但几何相似的普通零件不会自动匹配。
- 拆板派生仍可由母件 `T3-H-558` 证明。
- 几何候选报告只作为复核证据，不表示自动改号。
- 项目规则已经写入 `AGENTS.md`。

## Remaining Risk

- 严格编号后 `DATA_MISSING` 从 3 增加到 23，这是预期结果；后续需要区分真实缺件、导出范围问题、制造整板 vs Tekla 分段映射。
- 还未实现箱型柱主壁板制造整板与 Tekla 分段映射。
