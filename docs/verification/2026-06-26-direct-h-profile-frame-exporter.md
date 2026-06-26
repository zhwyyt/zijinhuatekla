# Direct H profile station frame exporter 验证

日期：2026-06-26

## 背景

`T2-3GL-17` 构件中直接存在 H 型材：`T2-3B-721 / GL3020-1 / BH300*200*6*10`。构件级判为异形是合理的，但零件侧面关系仍应按局部 H 型材 frame 判定。

此前导出器的 `hBeamSectionEvidence` 只从长连续拆板主材重建 H frame。直接 H 型材没有 3 块拆板主材，因此导出 `hFrames=0`，Python 侧只能返回 `MISSING_H_BEAM_MAIN_MATERIAL_FRAME`。

## 修改

导出器 `BodyBracketBundleExporter.cs` 新增 direct H profile fallback：

- 当拆板式 H 主材候选不足 3 块时，尝试解析直接 H profile。
- 支持 `BH/H` 格式，例如 `BH300*200*6*10`。
- 支持 `HI` 格式，例如 `HI780-10-20*200-12*200`。
- 解析出 height、width、webThickness、flangeThickness 后，生成 `directHProfileSectionFrame.v1`。
- station frame 输出 `webCenterU/webHalfThickness/topOuterV/bottomOuterV/webTopV/webBottomV`。
- diagnostics 包含 `DIRECT_H_PROFILE_FRAME`、`PROFILE=...`、`PROFILE_SOURCE=...`。

Python 侧 `h_beam_part_sides.py` 同步支持：

- `source=directHProfileSectionFrame.v1` 时，短附件也使用最近 station frame。
- evidence codes 增加 `DIRECT_H_PROFILE_FRAME`。
- 不再因为 direct profile 只有 3 个 station frames 而让中间附件误报缺 frame。

## 重新导出

命令：

```powershell
I:\xingcaisuanfa\TeklaSectionClassifier.Runner\bin\Debug\net48\TeklaSectionClassifier.Runner.exe --body-bracket-export --out I:\zijinhuatekla\cache\20260626_150124
```

结果：

- 实际输出：`I:\zijinhuatekla\cache\20260626_150124`
- 导出 4 根构件。

## 验算摘要

| member | source | hFrames | diagnostics |
| --- | --- | ---: | --- |
| T2-3GL-62 | hBeamStationLocalSolidSection.v1 | 21 | [] |
| T2-3GL-17 | directHProfileSectionFrame.v1 | 3 | DIRECT_H_PROFILE_FRAME; PROFILE=BH300*200*6*10; PROFILE_SOURCE=BH/H |
| T2-3GKL-13 | hBeamStationLocalSolidSection.v1 | 84 | [] |
| T2-3GL-49 | hBeamStationLocalSolidSection.v1 | 48 | [] |

`T2-3GL-17` 侧面关系样例：

| partPosition | side | confidence | evidence |
| --- | --- | ---: | --- |
| T2-3B-899 | TOP_FLANGE_OUTER | 0.833 | DIRECT_H_PROFILE_FRAME |
| T2-3B-926 | TOP_FLANGE_OUTER | 1.000 | DIRECT_H_PROFILE_FRAME |
| T2-3B-399 | WEB_LEFT / WEB_RIGHT | 0.667 | DIRECT_H_PROFILE_FRAME |
| T2-3B-1129 | WEB_LEFT | 1.000 | DIRECT_H_PROFILE_FRAME |

## 验证命令

```powershell
dotnet build I:\xingcaisuanfa\TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj
python -m unittest tests.test_h_beam_part_sides tests.test_main_material_segments tests.test_box_main_material_segments tests.test_pipeline_offline tests.test_reports_offline
```

结果：

```text
TeklaSectionClassifier.Runner build: 0 warnings, 0 errors
Ran 28 tests in 0.906s
OK
```

备注：Python 回归仍有既有 `openpyxl datetime.utcnow()` DeprecationWarning，不影响断言。

## 后续注意

直接 H 型材 frame 当前用于零件侧面关系判定。`classify_main_material_segment_groups` 对 `T2-3GL-17` 仍输出 0 个拆板式主板集合，这是预期行为：直接 H 型材不是拆板主板集合。若后续报告需要把直接 H 型材也列为主材，应新增独立角色，例如 `DIRECT_H_PROFILE_MAIN_MATERIAL`，不要混进拆板主板规则。