# Confirmed Main Material Segments Verification

## Scope

记录用户在 2026-06-23 人工确认的 T3-5GKZ-10 柱主材分段集合，并验证该确认已进入 Case Bank 与制造范围报告。

本轮不改变普通零件编号匹配规则，不自动改号，不把模型候选段当作自动匹配成功。

## Human Confirmation

用户确认修正：`T3-P-4914` 是误写成主材，不属于主材分段集合。以下 13 个零件才是这根柱子的主材分段模型：

- `T3-P-4914`
- `T3-P-4918`
- `T3-P-4917`
- `T3-P-4919`
- `T3-P-6272`
- `T3-P-5577`
- `T3-P-6269`
- `T3-P-6268`
- `T3-P-5571`
- `T3-P-6284`
- `T3-P-6271`
- `T3-P-5579`
- `T3-P-5576`
- `T3-P-6270`

## Implemented Boundary

- Case Bank 新增 `T3-5GKZ-10:box-column-main-material-segments`。
- `quality.manufacturing_scope.apply_confirmed_segment_groups` 从 Case Bank 读取人工确认集合。
- `pipeline.offline` 在制造范围识别前应用 Case Bank 确认集合。
- 制造范围候选报告输出：
  - `confirmed_segment_positions`
  - `confirmation_level=HUMAN_CONFIRMED_SEGMENT_GROUP`

## Verification Commands

```powershell
python -m unittest tests.test_casebank_persistence
```

结果：5 tests OK。

```powershell
python -m unittest tests.test_manufacturing_scope
```

结果：5 tests OK。

```powershell
python -m unittest discover -s tests
```

结果：48 tests OK。存在 `openpyxl` 的 `datetime.utcnow()` DeprecationWarning，不影响当前测试结果。

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\confirmed-segments-smoke-20260623
```

## Smoke Result

- `outputs\confirmed-segments-smoke-20260623\T3-5GKZ-10-manufacturing-scope-candidates.json` 中，制造范围候选带 `confirmation_level=HUMAN_CONFIRMED_SEGMENT_GROUP`。
- `confirmed_segment_positions` 包含修正后的 13 个柱主材分段编号。
- 当前 Excel 对齐行中只有 `T3-P-4917/4918/4919` 出现，因此 alignment 只对这 3 行带确认标记；其余 10 个作为同组模型分段证据保存在制造范围报告字段中。

## Remaining Risk

当前是人工确认集合，不是自动分组算法最终形态。下一步需要补导出器或特征层字段：

- 构件轴向 station。
- 壁板面编号或主材面归属。
- 分段接缝位置。
- segment adjacency / continuity evidence。

这些字段补齐后，再把人工确认集合升级为可解释自动分组。





## 2026-06-23 Correction

用户复核后修正：T3-P-4916 在新 cache 中为 环形劲板 PL30*100 短局部件，不属于 BOX 主板；T3-P-4918 为 COLUMN PL30*900 长连续主板，纳入确认集合。

