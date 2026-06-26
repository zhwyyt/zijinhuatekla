# H/GL station slice 最新 Tekla 选择集验算

日期：2026-06-26

## 新导出

命令：

```powershell
I:\xingcaisuanfa\TeklaSectionClassifier.Runner\bin\Debug\net48\TeklaSectionClassifier.Runner.exe --body-bracket-export --out I:\zijinhuatekla\cache\20260626_144742
```

结果：

- 导出目录：`I:\zijinhuatekla\cache\20260626_144742`
- Bundle：`I:\zijinhuatekla\cache\20260626_144742\tekla-body-bracket-export.bundle.json`
- Member JSON：`I:\zijinhuatekla\cache\20260626_144742\members`
- 共导出 4 根构件。

## 构件概览

| member | parts | hFrames | boxLoops | mainPart |
| --- | ---: | ---: | ---: | --- |
| T2-3GL-62 | 30 | 21 | 22 | BEAM |
| T2-3GL-17 | 12 | 0 | 13 | GL3020-1 |
| T2-3GKL-13 | 59 | 84 | 86 | BEAM |
| T2-3GL-49 | 36 | 48 | 50 | BEAM |

## 新算法验算结果

### T2-3GL-62

识别 5 个 H/GL station slice 主板：

| role | partPosition | stations | span | coverage |
| --- | --- | ---: | ---: | ---: |
| WEB | T2-3B-449 | 21 | 2927.909 | 0.986 |
| FLANGE | T2-3B-642 | 21 | 2927.909 | 0.986 |
| FLANGE | T2-3B-647 | 21 | 2927.909 | 0.986 |
| FLANGE | T2-3B-930 | 21 | 2927.909 | 0.986 |
| WEB | T2-3B-987 | 21 | 2927.909 | 0.986 |

slice 排名显示上述 5 个零件均为全长覆盖；附件如 `T2-3B-436`、`T2-3B-435` 仅覆盖约 0.042，未进入主板集合。

### T2-3GL-17

未输出 H/GL station slice 主板。

原因：本次导出该构件 `hFrames=0`，没有 `hBeamSectionEvidence.stationFrames` 可供新算法消费。当前算法不会在缺 slice/loop 证据时用 `PartRoles` 或关系硬判。

### T2-3GKL-13

识别 3 个 H/GL station slice 主板：

| role | partPosition | stations | span | coverage |
| --- | --- | ---: | ---: | ---: |
| FLANGE | T2-3B-315 | 84 | 9592.733 | 0.999 |
| WEB | T2-3B-563 | 84 | 9592.733 | 0.999 |
| FLANGE | T2-3B-567 | 84 | 9592.733 | 0.999 |

附件如 `T2-3B-562`、`T2-3B-559` 覆盖约 0.111，未进入主板集合。

### T2-3GL-49

识别 3 个 H/GL station slice 主板：

| role | partPosition | stations | span | coverage |
| --- | --- | ---: | ---: | ---: |
| FLANGE | T2-3B-247 | 48 | 10621.238 | 0.986 |
| WEB | T2-3B-348 | 48 | 10621.238 | 0.986 |
| FLANGE | T2-3B-7 | 48 | 10621.238 | 0.986 |

附件如 `T2-3B-369`、`T2-3B-246` 覆盖约 0.110，未进入主板集合。

## 结论

本次新导出的 4 根构件中，3 根具备 H station frame 的构件均由 `H_GL_STATION_SLICE_MAIN_PLATE` 证据识别出主板；局部附件未被吸入。`T2-3GL-17` 因缺少 hFrames 未判定，符合“不用 PartRoles/关系硬判”的安全口径。

`T2-3GL-62` 输出 5 块全长主板，证据上不是局部附件误吸；是否业务上也认定为 5 块主板，建议后续在 Tekla 视图中人工确认一次并加入 Case Bank。