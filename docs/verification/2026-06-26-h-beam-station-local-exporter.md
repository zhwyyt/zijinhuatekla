# H 钢 station-local 截面导出与侧面分类验证

日期：2026-06-26

## 目标

针对弧形 H 钢梁，导出器补充 station-local 截面证据，避免下游用整件全局投影包络判断腹板左右侧。

## 导出器变更

仓库：`I:\xingcaisuanfa`

- `TeklaSectionClassifier.Runner\BodyBracketExportDtos.cs`
  - 新增 `metadata.hBeamSectionEvidence`。
  - 新增 `stationFrames[]`，字段包括 `station/webCenterU/webHalfThickness/topOuterV/bottomOuterV/webTopV/webBottomV/topFlangePartId/bottomFlangePartId/webPartId/partSlices/diagnostics`。
- `TeklaSectionClassifier.Runner\BodyBracketBundleExporter.cs`
  - 新增 `BuildHBeamSectionEvidence`。
  - 复用已有 solid face section intersection 与 section loop 构建逻辑。
  - 主材 frame 只用长连续 H 主板候选，附件保留为 `partSlices`，但不参与 top/bottom/web frame。

## Python 侧变更

仓库：`I:\zijinhuatekla`

- `src\zijinhua_tekla\classifiers\h_beam_part_sides.py`
  - 优先读取 `assembly.metadata.hBeamSectionEvidence.stationFrames`。
  - 按零件 `axisStationStart/End` 中点选择最近 station frame。
  - 无 station frame 时继续 fallback 到 `PartRoles + projection + thickness`。

## 验证命令

### 1. 导出器构建

```powershell
dotnet build I:\xingcaisuanfa\TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj
```

结果：build succeeded，0 errors，8 nullable warnings（既有 nullable 风险，不影响本次导出字段）。

### 2. Tekla 当前选择集重新导出

```powershell
I:\xingcaisuanfa\TeklaSectionClassifier.Runner\bin\Debug\net48\TeklaSectionClassifier.Runner.exe --body-bracket-export --out I:\zijinhuatekla\cache\20260626_hbeam_station_reexport2
```

结果：

```text
进度: 已处理 1 根构件，当前 T3-7GL-126
导出完成: 1 根构件
Body/Bracket Bundle: I:\zijinhuatekla\cache\20260626_115317\tekla-body-bracket-export.bundle.json
```

### 3. 新导出字段检查

数据：`I:\zijinhuatekla\cache\20260626_115317`

结果：

```text
metadata keys: assemblyPosition, mainPartName, memberAxisEvidence, boxSectionEvidence, hBeamSectionEvidence
hBeamSectionEvidence.source: hBeamStationLocalSolidSection.v1
stationFrames: 58
webPartIds: 71357629
first20 topOuterV unique: 4
```

说明：station frame 已稳定使用主腹板 `71357629` 和上下翼缘 `71357604/71357617`，附件未再污染 `topOuterV`。

### 4. Python 回归

```powershell
python -m unittest tests.test_h_beam_part_sides tests.test_reports_offline tests.test_pipeline_offline
```

结果：

```text
Ran 8 tests in 0.636s
OK
```

备注：存在既有 `openpyxl datetime.utcnow()` DeprecationWarning，不影响断言。

## 当前选择集真实结果摘要

所有结果均来自重新导出的 `I:\zijinhuatekla\cache\20260626_115317`，证据码包含 `H_BEAM_STATION_LOCAL_FRAME`。

| partPosition | partId | side | confidence |
| --- | --- | --- | ---: |
| T3-P-3226 | 71485426 | WEB_RIGHT | 0.800 |
| T3-P-3226 | 71485811 | WEB_RIGHT | 0.800 |
| T3-L-301 | 71603918 | WEB_LEFT | 0.600 |
| T3-L-301 | 71604726 | WEB_LEFT | 0.600 |
| T3-P-4309 | 71485508/71485532/71485892/71485916 | TOP_FLANGE_OUTER | 0.714 |
| T3-P-4230 | 71485442/71485827 | TOP_FLANGE_OUTER | 1.000 |
| CP-1 | 71485516/71485524/71485900/71485908 | TOP_FLANGE_OUTER | 1.000 |
| T3-L-279 | 71603848/71604657 | WEB_LEFT | 0.550-0.600 |
| T3-P-1715 | 多个实例 | WEB_LEFT/WEB_RIGHT 均有 | 0.667-1.000 |

## 结论

本轮已按 Tekla 当前选择集重新导出并验证。H 钢侧面分类已优先使用导出器提供的 station-local frame，不再依赖弧形梁整件全局投影包络作为腹板左右分界。
