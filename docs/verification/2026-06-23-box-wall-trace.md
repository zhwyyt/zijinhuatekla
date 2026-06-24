# BOX Wall Trace Verification

## Change

在 BOX 主材分段算法中加入多 station 截面外轮廓 trace 过滤：

- 仍只使用非异常且闭合的截面样本：`ClosedLoops >= 1`、`CavityCount >= 1`。
- 对 `SectionParts` 中的 `flange_candidate` / `web_candidate`，增加外轮廓切线长度过滤。
- `flange_candidate` 使用 `TotalCutLength / OuterWidth >= 0.65`。
- `web_candidate` 使用 `TotalCutLength / OuterHeight >= 0.65`。
- 没有 `TotalCutLength` 或外轮廓尺寸字段时保守回退旧行为。
- 通过过滤的组增加 evidence code：`BOX_OUTER_WALL_TRACE_CONFIRMED`。

## Why

此前正常截面样本会把内部短加劲板也标为 `flange_candidate` / `web_candidate`，导致 `SECTION_FLANGE_CANDIDATE` 和 `SECTION_WEB_CANDIDATE` 混入内部短件。外轮廓 trace 要求切线长度接近 BOX 外轮廓宽/高，可把短内部件排除。

## Verification

已运行：

```powershell
python -m unittest discover -s tests
```

结果：66 tests OK。存在 openpyxl `datetime.utcnow()` DeprecationWarning，为既有 warning。

真实 T3 smoke：

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_144836 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\box-wall-trace-smoke-20260623
```

结果：

- 输出 `T3-5GKZ-10-box-main-material-segment-groups.json/csv`。
- 总行数：16。
- `SECTION_FLANGE_CANDIDATE=2`，为 `T3-P-6284`、`T3-P-6270`。
- `SECTION_WEB_CANDIDATE=2`，为 `T3-P-6272`、`T3-P-6271`。
- `SECTION_UNSAMPLED_CANDIDATE=12`。
- 修正后确认的 13 个主材分段编号：13/13 召回。
- `T3-P-4916` 不在主材输出中；`T3-P-4918` 在主材输出中。

## Remaining Risk

当前新 cache 只有 S03/S04 两个正常闭合截面样本，直接外轮廓 trace 只能确认被这些 station 切到的 4 个长壁板。后续要稳定追踪整根柱的四面壁板，需要导出器增加更多正常 station samples，尤其覆盖后续分段区间。
