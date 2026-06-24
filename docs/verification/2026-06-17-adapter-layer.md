# Adapter Layer Verification

## Scope

验证 `adapters` 包已承接离线 Tekla bundle、member JSON、Excel truth rows 的读取职责，CLI 不再直接负责这些源数据入口。

## Evidence

- 新增模块：`src/zijinhua_tekla/adapters/offline.py`
- 覆盖测试：`tests/test_adapters_offline.py`
- CLI 使用：`src/zijinhua_tekla/cli.py` 通过 `load_member`、`load_member_assembly_id`、`load_bundle`、`load_roles`、`load_truth_rows` 获取输入数据。

## Verification Commands

```powershell
python -m unittest discover -s tests
```

结果：26 tests OK。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\adapter-smoke-20260617
```

结果：CLI 成功输出 CSV、JSON、Markdown。

## Acceptance

- `adapters` 层提供离线数据读取入口。
- 读取职责从 CLI 迁出。
- T3-5GKZ-10 基线可继续通过 CLI 跑通。

## Remaining Risk

- `load_truth_rows` 当前仍绑定 `T3楼五节柱零构件清单(1).xls` 文件名，后续要把 truth source discovery 做成显式配置或多清单索引。
