# BOX Solid Station Loop Spatial Relations Verification

## Change

本轮按用户要求把 BOX 内外关系证据从固定三刀升级为零件级 station 采样：

- `I:\xingcaisuanfa` 导出器新增 `metadata.boxSectionEvidence.stationLoops[].partLoops[]`。
- station 采样为默认 25%/50%/75% 加每个零件自身 `axisStationStart / midpoint / axisStationEnd` 三点。
- station 上限改为所有零件 `axisStationEnd` 最大值，避免主零件局部长轴长度截断整根柱子的后续分段。
- 每个 station loop 来自 Tekla solid 原生 `Face -> Loop -> Vertex` 与主轴截面平面求交，证据源为 `teklaSolidFaceLoopSection.v1`。
- Python 侧优先用已确认 `BOX_MAIN_WALL_CONFIRMED_SET` 的主壁板 `partLoops` 重建该 station 的主壁板外轮廓，不再用全体 PL 候选污染外轮廓。
- Python 侧对每个待判零件按 `start/mid/end` 三个 station 选择最近 station loop；三点一致则判内/外，三点混合则判 `BOUNDARY_OR_THROUGH`。

## Files

- 导出器：`I:\xingcaisuanfa\TeklaSectionClassifier.Runner\BodyBracketExportDtos.cs`
- 导出器：`I:\xingcaisuanfa\TeklaSectionClassifier.Runner\BodyBracketBundleExporter.cs`
- Python：`src/zijinhua_tekla/classifiers/box_part_spatial_relations.py`
- 测试：`tests/test_box_part_spatial_relations.py`

## Verification

导出器构建：

```powershell
dotnet build I:\xingcaisuanfa\TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj
```

结果：build succeeded，0 errors，4 nullable warnings。

Python 单元测试：

```powershell
python -m unittest discover -s tests
```

结果：73 tests OK。存在 openpyxl `datetime.utcnow()` DeprecationWarning，为既有 warning。

Tekla 已打开并选中 `T3-5GKZ-10` 后重新导出：

```powershell
I:\xingcaisuanfa\TeklaSectionClassifier.Runner\bin\Debug\net48\TeklaSectionClassifier.Runner.exe --body-bracket-export --out I:\xingcaisuanfa\cache\solid_section_start_mid_end_20260624_2
```

实际输出路径：`I:\zijinhuatekla\cache\20260624_092738`。

新导出检查：

- `metadata.boxSectionEvidence.source=teklaSolidFaceLoopSection.v1`
- `stationLoopCount=152`
- `maxStation=10585.000892`
- T3-GG-2 所在 5.2m、5.8m、9.7m、10.2m 附近均有 station loop 覆盖。

真实 T3 smoke：

```powershell
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260624_092738 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\box-solid-start-mid-end-smoke-20260624
```

关系分布：

- `MAIN_WALL=16` Tekla 实体，对应去重 `partPosition` 仍为 13 个主板编号。
- `INSIDE_BODY=185`
- `OUTSIDE_ATTACHMENT=57`
- `BOUNDARY_OR_THROUGH=1`

主板去重编号保持：

`T3-P-4917,T3-P-4918,T3-P-4919,T3-P-5571,T3-P-5576,T3-P-5577,T3-P-5579,T3-P-6268,T3-P-6269,T3-P-6270,T3-P-6271,T3-P-6272,T3-P-6284`

关键回归：

- `T3-GG-2` 8 个 Tekla 实体全部由旧结果 `INSIDE_BODY` 修正为 `OUTSIDE_ATTACHMENT`。
- 证据码为 `PROJECTED_CENTROID_OUTSIDE_MAIN_WALL_ENCLOSURE;EXPORTED_BOX_OUTER_LOOP_POLYGON`。
- 未使用 name 特例、挂钩特例或焊接关系硬规则。

## Remaining Risk

当前 loop 构造仍使用主壁板 station part loops 的凸包作为该 station 外轮廓；对于凹形/开洞更复杂的异形 BOX，后续应继续升级为真正多 loop 拓扑（outer loop + inner/cavity loops），并在报告中输出每个零件三点 station 的逐点 inside/outside 明细。
