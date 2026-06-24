# Classifiers Facade Verification

## Scope

验证 `classifiers` 包已成为主材分类、零件角色分类和附属件簇分类的统一入口，后续 pipeline 不需要直接依赖分散的旧模块。

## Evidence

- 新增模块：`src/zijinhua_tekla/classifiers/__init__.py`
- 覆盖测试：`tests/test_classifiers_facade.py`
- CLI 使用：`src/zijinhua_tekla/cli.py` 已通过 `classifiers.classify_part` 调用零件角色分类。

## Verification Commands

```powershell
python -m unittest tests.test_classifiers_facade
```

结果：2 tests OK。

```powershell
python -m unittest discover -s tests
```

结果：29 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\classifiers-smoke-20260617
```

结果：

- 输出 `outputs\classifiers-smoke-20260617\T3-5GKZ-10-alignment.csv`
- 输出 `outputs\classifiers-smoke-20260617\T3-5GKZ-10-alignment.json`
- 输出 `outputs\classifiers-smoke-20260617\T3-5GKZ-10-analysis.md`
- JSON 行数：62
- 状态计数：`MATCH=55`、`MATCH_CONFLICT=4`、`DATA_MISSING=3`
- 匹配方式计数：`partPosition=32`、`specLength=17`、`partPositionConflict=4`、`derivedFromProfilePart=3`、`missing=3`、`specLengthPartial=2`、`geometryLoose=1`

## Acceptance

- `ClassificationFacade` 暴露 `classify_member`、`classify_part`、`classify_appendage`。
- 模块级函数提供默认门面调用。
- 迁移不改变 T3-5GKZ-10 当前对齐基线。

## Remaining Risk

- 现有旧模块仍保留在顶层，当前只是门面包裹；后续可以按稳定性逐步迁移到 `classifiers/` 子模块。
- `score_prediction` 仍在 CLI 中，后续应迁入 pipeline 或 classifier result evaluator。
