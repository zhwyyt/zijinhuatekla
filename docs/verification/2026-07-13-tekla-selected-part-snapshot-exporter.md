# Tekla 当前选择集零件图快照导出器验证记录

## 范围

- 导出器工作目录：`I:\tmp\xingcaisuanfa-part-snapshot-exporter`
- 分支：`codex/part-drawing-snapshot-exporter`
- 基线：`1de06da Export direct H profile station frames`
- 最新实现提交：`e875a58 fix: align exported part snapshot plane`
- 消费端：`I:\tmp\zijinhuatekla-part-drawing-engine`
- 日期：2026-07-13

本记录验证 Tekla 2017 当前直接选中的平板 `Part` 能输出 `partDrawingSnapshot.v1`，并由既有 Python 离线引擎生成 DXF/PDF。`REVIEW_REQUIRED` 表示图纸仍需人工检查，不代表生产放行。

## 实现摘要

- 新增命令行参数 `--export-part-drawing-snapshots`。
- 只处理当前选择集中的直接 `Part`，不扩展 Assembly。
- 每个实体以 `partPosition-partId.json` 单独输出。
- 严格读取 `partPosition`、厚度、材质、profile、局部坐标系和最终 Solid 主面环。
- 导出 BoltGroup 圆孔/长圆孔事实和 Boolean cut 证据。
- 无法由孔槽或原生圆弧证据解释的曲线返回 `UNSUPPORTED_CURVE_GEOMETRY`。
- `part-drawing-snapshots` 只存实体快照；`part-drawing-export-summary.json` 写在输出根目录。

## 自动测试

### C#

```powershell
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj --no-restore
dotnet build TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj --no-restore
```

结果：

- `26` tests passed，`0` failed。
- Runner build：`0 warnings / 0 errors`（增量构建）。
- 基线首次完整构建存在 `14` 个既有 nullable warning，`0` error；新代码未新增构建错误。

测试覆盖：

- JSON 字段名、三维数组、稳定文件名。
- 坐标系、环清理、外环/内环、自交、多外环。
- 编号、厚度、类型、曲线和几何质量门。
- 直接选择、去重、跳过非 Part、单件失败隔离和退出码。
- 圆孔、长圆孔、目标零件过滤、孔位去重、Boolean cut 和曲线证据预算。
- Runner 参数默认值和新模式分流。
- 最终主面与局部坐标平面对齐。
- 汇总文件与实体快照目录隔离。

### C# 到 Python 契约

C# 测试实际生成：

```text
C:\Users\Administrator\AppData\Local\Temp\zijinhua-part-drawing-contract\P-1001-1001.json
```

Python `load_part_snapshot()` 直接读取并断言：

```text
schema=partDrawingSnapshot.v1
partPosition=P-1001
thickness=10
outerLoop=4
```

Focused Python：

```powershell
python -m unittest tests.test_part_drawing_contracts tests.test_part_drawing_geometry tests.test_part_drawing_pipeline
```

结果：`11 tests OK`。

完整 Python：

```powershell
python -m unittest discover -s tests
```

结果：`165 tests OK`；存在既有 openpyxl `datetime.utcnow()` deprecation warning，不影响断言。

## 真实 Tekla Smoke

### 选择集与导出结果

当前 Tekla 2017 选择集包含一个直接平板：

```text
runtimeType=ContourPlate
partId=45416496
partPosition=T3-PX-317
profile=PL16
material=Q355B
name=连接板
```

修复后命令：

```powershell
I:\tmp\xingcaisuanfa-part-snapshot-exporter\TeklaSectionClassifier.Runner\bin\Debug\net48\TeklaSectionClassifier.Runner.exe --export-part-drawing-snapshots --output I:\tmp\tekla-selected-part-snapshot-smoke-20260713-v2
```

结果：`EXPORTED=1 / SKIPPED=0 / REJECTED=0`。

产物：

- `I:\tmp\tekla-selected-part-snapshot-smoke-20260713-v2\part-drawing-export-summary.json`
- `I:\tmp\tekla-selected-part-snapshot-smoke-20260713-v2\part-drawing-snapshots\T3-PX-317-45416496.json`

快照包含 4 段直线外轮廓、6 个圆孔、1 个 Boolean cut、板厚 16 和精确 `partPosition`。

### 首轮失败与根因

首轮 Python smoke 为 `REJECTED=2`：

1. 最终 Solid 主面位于板表面，原始零件坐标原点位于另一平行平面，沿法向相差半个板厚，触发 `contour points are not planar in the supplied local frame`。
2. `export-summary.json` 与实体快照同目录，被 Python 的 `*.json` 扫描当成快照。

修复：

- 坐标原点只沿法向移动到最终主面，X/Y/normal 不变。
- 汇总移到输出根目录，快照子目录只包含 `partDrawingSnapshot.v1`。
- 两个根因均先加入失败测试，再实现修复。

### 离线出图

命令：

```powershell
python -m zijinhua_tekla.cli draw-parts --snapshot-root I:\tmp\tekla-selected-part-snapshot-smoke-20260713-v2\part-drawing-snapshots --out I:\tmp\tekla-selected-part-drawing-smoke-20260713-v3 --cjk-font C:\Windows\Fonts\simhei.ttf
```

结果：`OK=0 / REVIEW_REQUIRED=1 / REJECTED=0`。

产物：

- `I:\tmp\tekla-selected-part-drawing-smoke-20260713-v3\parts\T3-PX-317\T3-PX-317.dxf`
- `I:\tmp\tekla-selected-part-drawing-smoke-20260713-v3\parts\T3-PX-317\T3-PX-317.pdf`
- `I:\tmp\tekla-selected-part-drawing-smoke-20260713-v3\parts\T3-PX-317\T3-PX-317.drawing.json`
- `I:\tmp\tekla-selected-part-drawing-smoke-20260713-v3\T3-PX-317-preview.png`

输出验证：

- DXF audit：`0 errors / 0 fixes`。
- PDF：`1` 页，`420 x 297 mm`。
- 预览非空、未裁切；可见矩形轮廓、6 个孔、零件号、名称、材质和板厚。
- 状态为 `REVIEW_REQUIRED`：`17 annotations unplaced / 0 collisions`，主要是孔径和孔定位标注未放置。

## 当前限制与人工验收

- 当前真实样件是直线外轮廓。Tekla 2017 `Solid.Edge` 只提供曲线类型和端点，不提供圆心；未能从 Contour/Chamfer 原生参数确定圆心的曲线会被拒绝。ARC 快照验收尚未完成。
- 当前图纸虽已生成并通过文件审计，但 17 个孔相关标注未放置，不能作为生产放行图。
- 尚需用户对照 Tekla 模型人工确认轮廓、6 个孔的位置/孔径、总尺寸和标题栏内容。
- 用户确认图面前，不合并离线引擎 PR #1，也不宣称零件图阶段完成。
