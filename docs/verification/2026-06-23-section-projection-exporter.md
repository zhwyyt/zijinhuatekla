# Section Projection Exporter Verification

## Change

在 `I:\xingcaisuanfa` 导出器中补充 `mainMaterialEvidence.sectionProjectionEvidence`，用于替代异形 BOX 内外判断对包围盒/径向分桶的依赖。

涉及文件：

- `I:\xingcaisuanfa\TeklaSectionClassifier.Runner\BodyBracketExportDtos.cs`
- `I:\xingcaisuanfa\TeklaSectionClassifier.Runner\BodyBracketBundleExporter.cs`

新增证据字段：

- `sectionPlaneOrigin`
- `sectionAxisU`
- `sectionAxisV`
- `projectedCentroid`
- `projectedBoundsMin`
- `projectedBoundsMax`
- `projectedContour`
- `normalProjection`
- `normalProjectionMagnitude`
- `pointSource`

## Semantics

导出器以构件主轴为法向建立截面 U/V 坐标，把零件轮廓点投影到同一截面坐标。若零件没有可用 `ContourPlate` 轮廓点，则退回 solid bounding box 角点投影，并通过 `pointSource` 明确标记。

该字段是证据，不是最终分类标签。BOX 内外、壁板闭环和附属件归属仍应由下游算法结合投影轮廓、焊接/接触关系、station 连续性和拓扑关系综合判断。

## Verification

已运行：

```powershell
dotnet build I:\xingcaisuanfa\TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj
```

结果：构建成功，0 errors，4 warnings。4 个 warning 为既有 nullable/可能 null 返回警告：

- `BodyBracketExportDtos.cs(163,37)` `PartCoordinateSystem` nullable warning。
- `BodyBracketBundleExporter.cs(97,16)` 可能返回 null。
- `BodyBracketBundleExporter.cs(105,20)` 可能返回 null。
- `BodyBracketBundleExporter.cs(885,16)` 可能返回 null。

## Next

需要在 Tekla 中用新 Runner 重新导出目标构件 cache，然后在 `I:\zijinhuatekla` 消费 `sectionProjectionEvidence`：

```powershell
I:\xingcaisuanfa\TeklaSectionClassifier.Runner\bin\Debug\net48\TeklaSectionClassifier.Runner.exe --body-bracket-export --out I:\xingcaisuanfa\cache\main_material_section_projection_20260623_1
```
