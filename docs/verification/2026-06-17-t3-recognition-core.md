# 2026-06-17 T3 Recognition Core Verification

## 命令

```powershell
python -m unittest discover -s tests
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs
```

## 结果

- 单元测试：4 个测试通过。
- T3-5GKZ-10 Excel 行数：62。
- `MATCH`：55。
- `MATCH_CONFLICT`：4。
- `DATA_MISSING`：3。
- `derivedFromProfilePart`：3。
- `partPosition`：32。
- `specLength`：17。

## 已验证口径

- `T3-H-558s/x/f` 被识别为来自 `T3-H-558` 的 `BH400*200*7*10` 拆板派生，不再算缺 Tekla 实体。
- `T3-P-4869` 和 `T3-P-4885` 通过 ContourPlate 成对名义尺寸匹配，不再被 OBB 外包盒误判为冲突。
- `T3-P-3245`、`T3-P-4546`、`T3-P-4775`、`T3-P-4942`、`T3-P-4943` 仍能用 OBB/轮廓候选正确匹配。
- `PL12*116/890` 这类窄长板不会被错误匹配成 `PL12*845` 内隔板。

## 剩余问题

- `T3-P-3449`：Excel 为 `PL30*100` 长 978，真实 `下料割孔/异形/圆`，当前 selected assembly 缺对应实体。
- `T3-P-4910`：Excel 为 `PL16*200` 长 158，当前 selected assembly 缺对应实体。
- `T3-P-4914`：Excel 为超长主壁板 `PL16*968` 长 10534，当前 selected assembly 只有近似分段候选，属于制造清单口径与 Tekla 分段口径差异。
- `T3-P-4916`、`T3-P-4917`、`T3-P-4919`、`T3-P-6243`：同名 Tekla 实体与 Excel 规格/长度冲突，保留为 `MATCH_CONFLICT`。

## 输出

- `outputs\T3-5GKZ-10-alignment.csv`
- `outputs\T3-5GKZ-10-alignment.json`
- `outputs\T3-5GKZ-10-analysis.md`
