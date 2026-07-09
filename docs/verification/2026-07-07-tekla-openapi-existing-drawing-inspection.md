# Tekla Open API 既有构件图探测验证

## Scope

- Tool: `tools/tekla2017_progressive_drawing_poc`
- Tekla install: `D:\Program Files\Tekla Structures\2017\nt\bin`
- Purpose: 验证能否通过 Tekla Open API 读取当前 Tekla 中已生成的构件图，并评估“基于原生构件图隐藏零件分阶段出工序图”的可行性。

## Changes To POC

新增只读入口：

- `--list-drawings`: 通过 `DrawingHandler.GetDrawings()` 枚举当前模型图纸，输出图纸类型、模型对象 ID、Mark、标题、状态。
- `--selected-model`: 通过 `ModelObjectSelector.GetSelectedObjects()` 读取当前模型选择集，输出零件/构件 ID、part position、assembly position。
- `--inspect-drawing-model-id <id>`: 按图纸关联的 model id 找到图纸，打开为 active drawing，统计 sheet 内 `Part/Mark/View` 对象；不执行 hide/show/save。

## Commands And Results

### Build

```powershell
dotnet build I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\BoxProgressiveDrawingPoc.csproj
```

Result:

```text
0 warnings
0 errors
```

### Drawing list

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe `
  --steps I:\zijinhuatekla\outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps.json `
  --list-drawings
```

Result:

```text
Target member: T3-3GZ-6
Target assembly: 63737929
Active drawing: <none>
Total drawings: 2394
```

Filtered result:

- 当前 Tekla 模型中有大量 `10#三节柱` 构件图，例如 `10-3GZ-.6 / G10-Z3-06`。
- 没有匹配 `T3-3GZ-6 / assembly 63737929` 的 `MATCH_TARGET` 图纸。
- 结论：当前 Tekla 打开的模型不是离线 cache 中的 T3 目标模型，或至少当前图纸列表里没有该 T3 构件图。

### Selected model objects

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe --selected-model
```

Result:

```text
Selected model objects: 0
```

当前 Tekla 模型里没有可由 API 读到的选择集；后续要针对用户当前选择构件套图，需要先在 Tekla 模型中选中构件或主零件。

### Existing assembly drawing inspect

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe --inspect-drawing-model-id 28717373
```

Result:

```text
Found drawing: AssemblyDrawing | modelId=28717373 | mark=[10-3GZ-.6] | name=10#三节柱 | title1=G10-Z3-06 | upToDate=DrawingIsUpToDate | locked=False
Opened drawing: AssemblyDrawing | modelId=28717373 | mark=[10-3GZ-.6] | name=10#三节柱 | title1=G10-Z3-06 | upToDate=DrawingIsUpToDate | locked=False
Sheet Part objects: 160
Sheet Mark objects: 40
Sheet View objects: 4
No hide/show/save operations were executed.
```

## Conclusion

Tekla 原生构件图路线可行性明显提高：

- Open API 能连接当前 Tekla DrawingHandler。
- 能枚举当前模型图纸。
- 能打开既有 AssemblyDrawing。
- 能读取 sheet 内的 Part、Mark、View 对象。

因此，“以 Tekla 已生成构件图为基准，通过隐藏/显示零件生成阶段图”比离线 DXF 更有潜力保留真实投影、Tekla 标注、零件标号和图纸风格。

## Remaining Limits

- 当前没有活动图纸，且 Tekla 模型选择集为 0。
- 当前打开模型的图纸是 `10#...`，不是离线 cache 的 `T3-3GZ-6`。
- 尚未在复制图纸上执行 hide/show/save；不能直接改原图，应先生成副本或使用新建工序图再测试。
- 隐藏零件后尺寸链、零件标号和焊缝标注是否自动保留/失效，需要在复制图纸上做一次阶段隐藏试验。

## Native Hide/Show POC - 10-3GZ-.6

用户指定以当前 Tekla 中的 `10-3GZ-6` 为目标继续。当前 API 选择集仍为 0，因此本轮使用图纸列表中已确认的 `10-3GZ-.6 / G10-Z3-06`，其 AssemblyDrawing `modelId=28717373`。

新增命令：

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe `
  --generate-process-drawings-model-id 28717373 `
  --out I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6
```

第一次尝试使用 sheet 80 失败，Tekla 2017 异常无法 `ToString()`；补充异常捕获后确认原因之一是 active drawing 未关闭：

```text
Tekla.Structures.Drawing.CannotInsertDrawingException: Drawing cannot be inserted when another drawing is active.
```

修正后流程：

1. 打开原始 `10-3GZ-.6` 只读获取 drawing part ids。
2. 关闭原图，不保存。
3. 对同一 assembly 新建 sheet 1-5。
4. 每张 sheet 按阶段调用 `HideFromDrawingView()` / `ShowInDrawingView()`。
5. 保存新 sheet。

生成结果：

```text
Source drawing: AssemblyDrawing | modelId=28717373 | sheet=0 | mark=[10-3GZ-.6] | name=10#三节柱 | title1=G10-Z3-06
Source drawing unique drawing part ids: 40
Ordered assembly part ids: 40
Closed source drawing without saving before process sheet insertion.
Existing process/source sheet numbers for assembly: 0
Creating process drawing sheet 1 for step 1.
Step 1 saved sheet=1 matched=24 hidden=96 visibleTarget=8.
Creating process drawing sheet 2 for step 2.
Step 2 saved sheet=2 matched=48 hidden=72 visibleTarget=16.
Creating process drawing sheet 3 for step 3.
Step 3 saved sheet=3 matched=72 hidden=48 visibleTarget=24.
Creating process drawing sheet 4 for step 4.
Step 4 saved sheet=4 matched=96 hidden=24 visibleTarget=32.
Creating process drawing sheet 5 for step 5.
Step 5 saved sheet=5 matched=120 hidden=0 visibleTarget=40.
```

读回 Tekla 图纸列表确认新增：

```text
AssemblyDrawing | modelId=28717373 | sheet=5 | mark=[10-3GZ-.6 - 5] | name=STANDARD
AssemblyDrawing | modelId=28717373 | sheet=4 | mark=[10-3GZ-.6 - 4] | name=STANDARD
AssemblyDrawing | modelId=28717373 | sheet=3 | mark=[10-3GZ-.6 - 3] | name=STANDARD
AssemblyDrawing | modelId=28717373 | sheet=2 | mark=[10-3GZ-.6 - 2] | name=STANDARD
AssemblyDrawing | modelId=28717373 | sheet=1 | mark=[10-3GZ-.6 - 1] | name=STANDARD
AssemblyDrawing | modelId=28717373 | sheet=0 | mark=[10-3GZ-.6] | name=10#三节柱 | title1=G10-Z3-06
```

生成计划文件：

- `outputs\tekla-process-drawings-10-3GZ-6\tekla-process-drawings-28717373.json`

当前 5 步是机械 POC：按 assembly/drawing part 顺序每步增加 8 个唯一 part id，用于验证原生图纸隐藏路线；还不是最终“胎架/主板/腹板/内部件/盖板/外部簇”的工艺算法。

下一步：

- 打开 sheet 1-5 人工检查：隐藏后原有尺寸、标记、视图是否仍清晰。
- 如果保留效果好，把离线 BOX 工序 planner 输出的真实步骤映射到当前 Tekla 模型 part ids，再用同一隐藏机制生成正式工序图。
- 如果标记/尺寸跟随隐藏后残留或丢失，则需要在新 sheet 上重新插入本步新增零件 Mark 和关键尺寸。

## Process Sheet Readback - Dimensions And Marks

新增读回命令：

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe `
  --inspect-process-sheets-model-id 28717373 `
  --out I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6
```

读回结果：

```text
sheet=0 mark=[10-3GZ-.6] parts=160 visibleParts=160 hiddenParts=0 marks=40 dimensions=96 texts=5 weldMarks=0 views=4
sheet=1 mark=[10-3GZ-.6 - 1] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=0 texts=0 weldMarks=0 views=3
sheet=2 mark=[10-3GZ-.6 - 2] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=0 texts=0 weldMarks=0 views=3
sheet=3 mark=[10-3GZ-.6 - 3] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=0 texts=0 weldMarks=0 views=3
sheet=4 mark=[10-3GZ-.6 - 4] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=0 texts=0 weldMarks=0 views=3
sheet=5 mark=[10-3GZ-.6 - 5] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=0 texts=0 weldMarks=0 views=3
```

输出文件：

- `outputs\tekla-process-drawings-10-3GZ-6\tekla-process-sheets-inspection-28717373.json`

结论：

- 原图 sheet 0 的尺寸对象保留为 `96`，文字注释为 `5`，视图为 `4`。
- 新建的 sheet 1-5 均为 `STANDARD` 图纸，只有零件和标记对象；尺寸对象、文字注释均为 `0`，视图数也从原图 `4` 降为 `3`。
- 读回时 sheet 1-5 的 `hiddenParts=0`，说明当前 `new AssemblyDrawing(..., sheetNumber)` + `HideFromDrawingView()` 不是可交付路线；它没有继承既有构件图的尺寸/注释，也没有可靠保留阶段隐藏状态。
- 额外探测 `new AssemblyDrawing(id, sheet, "10#三节柱")` 生成了不可打开的坏 sheet 6，Tekla 报“无法加载所选图纸，图纸文件不兼容”；已通过打开/关闭正常 sheet 0 刷新状态，并删除坏 sheet 6。该构造方式不可继续使用。

下一步改向：

- 不再把这 5 张 `STANDARD` sheet 当正式工序图基础。
- 若继续 Tekla 原生路线，必须优先走 Tekla 自带克隆/主图纸目录机制，证明克隆图能继承 sheet 0 的尺寸、文字、视图和 Mark。
- 如果 Tekla 2017 Open API/宏无法稳定克隆既有构件图，则改为在新 sheet 上按本步可见零件重新创建关键尺寸、PartMark、阶段注释和必要局部视图。

## Clone Drawing Route Probe

目的：验证是否能通过 Tekla 自带图纸列表/克隆图纸机制复制既有 sheet 0，从而保留原构件图尺寸、文字、视图和 Mark。

新增命令：

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe `
  --probe-drawing-filter-options-model-id 28717373 `
  --out I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6
```

输出文件：

- `outputs\tekla-process-drawings-10-3GZ-6\tekla-drawing-filter-options-28717373.json`

关键发现：

- `diaSavedSearchOptionMenu=7` 能在当前 TS2017 China 环境里通过图纸列表筛选选中原图：

```text
filterOption=7 selected=1
  option 7 selected AssemblyDrawing | modelId=28717373 | sheet=0 | mark=[10-3GZ-.6] | name=10#三节柱 | title1=G10-Z3-06
```

- 旧宏 `SelectAssemblyDrawing.cs` 使用的 value `10` 在当前环境里选不中该构件图；value `1/2/9/11/15` 会选中此前失败 POC 的 `STANDARD` sheet 5，不能用于克隆原图。
- 探测到 value `16` 后 Tekla 切回“选择设置”启动界面，DrawingHandler 暂时断开；已重新打开模型恢复，后续探测上限限制为 `15`。

随后执行：

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe `
  --probe-clone-drawing-model-id 28717373 `
  --out I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6
```

结果：

```text
Selected drawings after UI filter: 1
  selected AssemblyDrawing | modelId=28717373 | sheet=0 | mark=[10-3GZ-.6] | name=10#三节柱 | title1=G10-Z3-06
Running Tekla macro FabricationInspectionDrawings\CloneDrawing.cs.
Clone macro ran; waiting for drawing list change.
```

Tekla UI 状态：

- 克隆宏进入 Tekla 的 `克隆图纸` 对话。
- 同时弹出 `视图` 可见性选择对话。
- 还会弹出“模型中早期的版本创建”提示。
- 在这些模态窗口未被处理前，程序侧轮询图纸列表会被阻塞。

恢复操作：

- 手动/脚本关闭克隆相关模态窗口。
- 重新确认 DrawingHandler 可连接，active drawing 为空。
- 重新读图纸列表，当前 `modelId=28717373` 只剩原图 sheet 0，没有误生成克隆图：

```text
Active drawing: <none>
AssemblyDrawing | modelId=28717373 | sheet=0 | mark=[10-3GZ-.6] | name=10#三节柱 | title1=G10-Z3-06
Total drawings: 2394
```

结论：

- Tekla UI 宏路线可以准确选中 sheet 0 原图。
- Tekla 2017 公开 Open API 没有直接 Clone/Copy drawing 方法；现有 CloneDrawing 宏不是无交互克隆，会停在克隆参数和视图可见性对话。
- 因此“自动克隆原构件图，再隐藏零件”还需要继续宏化 `克隆图纸` 对话和 `视图` 对话；在这一步完成前，不能把克隆路线视为可交付自动出图路线。
- 若不继续钻 UI 宏，下一条可控路线是在新建图纸上用 Drawing API 重建本步关键尺寸、PartMark、阶段注释和必要局部视图。

## Re-run: Open 5 Mechanical Sheets

用户要求继续打开这 5 张 sheet，看尺寸和标注保留效果。先关闭上一轮遗留的 `克隆图纸` 对话和卡住的 POC 进程，再确认当前 Tekla 图纸库中目标 `modelId=28717373` 只剩原图 sheet 0。随后重新生成同一批机械验证 sheet 1-5，并逐张打开读回对象统计。

生成命令：

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe `
  --generate-process-drawings-model-id 28717373 `
  --out I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6
```

生成结果：

```text
Source drawing: AssemblyDrawing | modelId=28717373 | sheet=0 | mark=[10-3GZ-.6] | name=10#三节柱 | title1=G10-Z3-06
Source drawing unique drawing part ids: 40
Ordered assembly part ids: 40
Closed source drawing without saving before process sheet insertion.
Existing process/source sheet numbers for assembly: 0
Creating process drawing sheet 1 for step 1.
Step 1 saved sheet=1 matched=24 hidden=96 visibleTarget=8.
Creating process drawing sheet 2 for step 2.
Step 2 saved sheet=2 matched=48 hidden=72 visibleTarget=16.
Creating process drawing sheet 3 for step 3.
Step 3 saved sheet=3 matched=72 hidden=48 visibleTarget=24.
Creating process drawing sheet 4 for step 4.
Step 4 saved sheet=4 matched=96 hidden=24 visibleTarget=32.
Creating process drawing sheet 5 for step 5.
Step 5 saved sheet=5 matched=120 hidden=0 visibleTarget=40.
```

逐张打开/读回命令：

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe `
  --inspect-process-sheets-model-id 28717373 `
  --out I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6
```

读回结果：

```text
sheet=0 mark=[10-3GZ-.6] parts=160 visibleParts=160 hiddenParts=0 marks=40 dimensions=96 texts=5 weldMarks=0 views=4
sheet=1 mark=[10-3GZ-.6 - 1] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=0 texts=0 weldMarks=0 views=3
sheet=2 mark=[10-3GZ-.6 - 2] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=0 texts=0 weldMarks=0 views=3
sheet=3 mark=[10-3GZ-.6 - 3] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=0 texts=0 weldMarks=0 views=3
sheet=4 mark=[10-3GZ-.6 - 4] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=0 texts=0 weldMarks=0 views=3
sheet=5 mark=[10-3GZ-.6 - 5] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=0 texts=0 weldMarks=0 views=3
```

结论：

- 重新生成并逐张打开后，sheet 1-5 仍然没有继承原图的尺寸对象和文字注释。
- 原图 sheet 0 有 `Dimensions=96/Text=5/View=4`，新建 sheet 1-5 均为 `Dimensions=0/Text=0/View=3`。
- `hiddenParts=0` 说明 `HideFromDrawingView()` 的阶段隐藏状态没有以可读回的方式稳定保留。
- 这条 `new AssemblyDrawing(..., sheetNumber)` 路线只能证明能生成 Tekla 图纸副页，不能作为正式工序图底图。下一步应继续验证克隆原图是否能保留标注，或者转向在新 sheet 上重建关键尺寸、PartMark、阶段注释和必要局部视图。

## Annotation Copy And Part Pruning Probe

继续探测后确认两件事：

1. Tekla 自带 `CloneDrawing.cs` 可打开 `克隆图纸` 对话，但在当前目标 `10-3GZ-.6` 同一构件上，`clone_selected_pb`、前台鼠标点击、`WM_COMMAND`、UI Automation 都未触发实际克隆；`drawing_cloning.log` 也没有新增记录。推断该对话更偏向“用源图克隆到当前模型选择的其它目标构件”，不适合直接复制同一构件图为新 sheet。
2. 原图标注可通过 Drawing API 复制到新建副页：从 sheet 0 捕获 `Text=5` 和 `StraightDimensionSet=23`，用 `Text.Insert()` 和 `StraightDimensionSetHandler.CreateDimensionSet()` 插入到 `STANDARD` 副页后，读回尺寸从 `0` 增加到 `96`、文字从 `0` 增加到 `5`。

代表命令：

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe `
  --probe-copy-annotations-model-id 28717373 `
  --source-sheet 0 `
  --target-sheet 1 `
  --out I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6
```

代表结果：

```text
Captured annotations from source: texts=5 straightDimensionSets=23 sourceDimensions=96.
Copied annotations to target sheet=1 texts 5/5 dimensionSets 23/23.
Target stats before(dim=0, texts=0) after(dim=96, texts=5, views=3).
```

随后测试“删除多余 Drawing Part”形成阶段视图：

```text
Pruned target sheet=1 step=1 kept=24 deleted=96 failed=0.
Target stats before(parts=120, unique=40, marks=40, dim=96) after(parts=24, unique=8, marks=8, dim=96).
```

但重新打开读回后，Tekla 会恢复 Drawing Part：

```text
sheet=1 mark=[10-3GZ-.6 - 1] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=96 texts=5 views=3
```

进一步测试：

- 设置 `View.Parts` 为第 1 步 8 个零件：`changedViews=3/failedViews=0`，但 immediate/reopened 统计均仍为 `parts=120/unique=40/marks=40/dim=96`，没有实际筛选效果。
- 剪裁后设置 `IsLocked=true`：即时读回仍为 `parts=24/unique=8/marks=8/dim=96`，但再次打开 sheet 1 失败；该坏 sheet 已删除，避免污染现场。

当前现场状态：

- 原图 sheet 0 保持可打开，`Part=160/Mark=40/Dimensions=96/Text=5/View=4`。
- sheet 1 因锁定剪裁实验后不可打开，已删除。
- sheet 2-5 可打开，并已稳定保留复制来的 `Dimensions=96/Text=5`，但零件集合仍为全量 `Part=120/Mark=40/HiddenParts=0`。

结论：

- “复制原图尺寸/文字到 Tekla 新 sheet”可行，是后续可控路线的重要基础。
- “用 Hideable、删除 Drawing Part、View.Parts、锁定图纸来稳定保留阶段零件集合”均未形成可交付结果。
- 下一步若继续 Tekla 原生路线，应改成“新 sheet 上按工序步骤重新绘制/限制几何对象 + 复制或重建关键尺寸/PartMark/注释”，不要再依赖 Tekla 自动生成的 Part 对象隐藏状态。

## Re-run: Five Fresh Annotation-Copy Sheets

用户要求继续打开 5 张 sheet，看尺寸和标注保留效果。由于上一轮 sheet 1 已因锁定剪裁实验删除，当前目标构件图纸库中只有原图 sheet 0 和副页 sheet 2-5。本轮不删除既有副页，重新生成一组 5 张机械验证副页 sheet 6-10，并明确从原图 sheet 0 复制文字和尺寸。

生成 5 张副页：

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe `
  --generate-process-drawings-model-id 28717373 `
  --out I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6
```

结果：

```text
Creating process drawing sheet 6 for step 1.
Step 1 saved sheet=6 matched=24 hidden=96 visibleTarget=8.
Creating process drawing sheet 7 for step 2.
Step 2 saved sheet=7 matched=48 hidden=72 visibleTarget=16.
Creating process drawing sheet 8 for step 3.
Step 3 saved sheet=8 matched=72 hidden=48 visibleTarget=24.
Creating process drawing sheet 9 for step 4.
Step 4 saved sheet=9 matched=96 hidden=24 visibleTarget=32.
Creating process drawing sheet 10 for step 5.
Step 5 saved sheet=10 matched=120 hidden=0 visibleTarget=40.
```

逐张复制原图标注：

```powershell
$env:SESSIONNAME='Console'
$exe='I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe'
$out='I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6'
foreach ($sheet in 6..10) {
  & $exe --probe-copy-annotations-model-id 28717373 --source-sheet 0 --target-sheet $sheet --out $out
}
```

每张 sheet 均捕获并插入：

```text
Captured annotations from source: texts=5 straightDimensionSets=23 sourceDimensions=96.
Copied annotations to target sheet=<6..10> texts 5/5 dimensionSets 23/23.
Target stats before(dim=0, texts=0) after(dim=96, texts=5, views=3).
```

关闭后重新逐张打开读回：

```text
sheet=6 mark=[10-3GZ-.6 - 6] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=96 texts=5 weldMarks=0 views=3
sheet=7 mark=[10-3GZ-.6 - 7] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=96 texts=5 weldMarks=0 views=3
sheet=8 mark=[10-3GZ-.6 - 8] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=96 texts=5 weldMarks=0 views=3
sheet=9 mark=[10-3GZ-.6 - 9] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=96 texts=5 weldMarks=0 views=3
sheet=10 mark=[10-3GZ-.6 - 10] parts=120 visibleParts=120 hiddenParts=0 marks=40 dimensions=96 texts=5 weldMarks=0 views=3
```

输出证据：

- `outputs\tekla-process-drawings-10-3GZ-6\tekla-copy-annotations-probe-28717373-s0-to-s6.json`
- `outputs\tekla-process-drawings-10-3GZ-6\tekla-copy-annotations-probe-28717373-s0-to-s7.json`
- `outputs\tekla-process-drawings-10-3GZ-6\tekla-copy-annotations-probe-28717373-s0-to-s8.json`
- `outputs\tekla-process-drawings-10-3GZ-6\tekla-copy-annotations-probe-28717373-s0-to-s9.json`
- `outputs\tekla-process-drawings-10-3GZ-6\tekla-copy-annotations-probe-28717373-s0-to-s10.json`
- `outputs\tekla-process-drawings-10-3GZ-6\tekla-process-sheets-inspection-28717373.json`

结论更新：

- 尺寸和文字标注复制路线稳定：5 张新副页 sheet 6-10 关闭重开后均保留 `Dimensions=96/Text=5`。
- 原生 PartMark 对象也仍为 `Mark=40`，但它们对应全量零件，不能代表阶段图的正确标号集合。
- 阶段隐藏仍未保留：5 张副页均为 `hiddenParts=0`、`visibleParts=120`，说明 `HideFromDrawingView()` 仍不能作为阶段筛选机制。
- 正式 Tekla 工序图路线应采用“普通图纸/副页上重建阶段几何 + 复制/重建关键尺寸和标注”，而不是继续尝试隐藏 AssemblyDrawing 自动 Part 对象。

## Fixture True Projection GA Prototype

用户确认应改为“柱子躺平在胎架上，再按 Tekla 实体真实投影重建几何”。本轮新增 POC 命令：

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe `
  --probe-ga-fixture-projection-model-id 28717373 `
  --source-sheet 0 `
  --step 1 `
  --out I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6
```

结果：

```text
Ordered assembly part ids: 40
Creating fixture true projection GA drawing for step 1.
Fixture true projection edges=248 projected=248 insertedLines=248 parts=8 frame=MODEL_AXIS_2_HEIGHT_0_MIN_ON_FIXTURE.
GA fixture projection inserted lines=248 failed=0 texts=4 dimension=True.
Immediate primitive stats: lines=248 texts=4 dims=2 parts=0 marks=0 views=0
Reopened primitive stats: lines=248 texts=4 dims=2 parts=0 marks=0 views=0
```

输出证据：

- `outputs\tekla-process-drawings-10-3GZ-6\tekla-ga-fixture-projection-28717373-step1.json`

JSON 关键字段：

```text
visible_part_count=8
solid_edge_count=248
projected_edge_count=248
lines_inserted=248
lines_failed=0
text_inserted=4
dimension_inserted=True
fixture_frame.AxisIndex=2
fixture_frame.WidthIndex=1
fixture_frame.HeightIndex=0
fixture_frame.FixtureFace=MODEL_AXIS_2_HEIGHT_0_MIN_ON_FIXTURE
projected_bounds=3505 x 950
```

结论：

- 这张新 GA 图纸名为 `PROCESS-FIXTURE-10-3GZ-6-S1`。
- 几何不再来自 AssemblyDrawing 自动 Part，也不再复制原图标注；线条来自 Tekla `Part.GetSolid().GetEdgeEnumerator()`。
- 当前第 1 步 8 个零件被转到胎架坐标：模型长轴 `AxisIndex=2` 转为图纸横向，`HeightIndex=0` 的最小侧作为胎架底面。
- 重开后普通线、文字和尺寸均保留，且 `parts=0/marks=0/views=0`，没有 Tekla 自动 Part 对象恢复污染。
- 仍需下一步补可见边过滤、真实工艺步骤映射、零件号和定位尺寸自动避让；当前只是几何一致性原型，不是最终工序图。

## Fixture U-Stage GA Prototype

用户要求先出一张第一阶段“底板 + 两个侧面”。原先按物理 Part 选择底板/侧板失败，诊断证据显示 40 个图纸关联零件中主壁板不是 3/4 个独立板，而是单个 Tekla 主零件：

```text
PartId=28705233
PartPosition=10-3Z-128
Name=GKZ60-2
Profile=BOX600*600*30*30
Material=Q355B
AssemblyPosition=10-3GZ-6
```

因此本轮新增 U-stage fallback：当物理底板/侧板集合为空时，识别 BOX profile 主零件，并按 `VIRTUAL_DECOMPOSED_BOX_PROFILE` 生成阶段主视图。几何来源为 Tekla `Part.GetSolid()` 外包尺寸和 BOX profile 厚度，不声明 Tekla 模型中存在三块独立板。

运行命令：

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe `
  --probe-ga-fixture-u-stage-model-id 28717373 `
  --source-sheet 0 `
  --out I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6
```

结果：

```text
Fixture U-stage using virtual BOX profile decomposition from part 28705233 profile=BOX600*600*30*30.
Fixture U-stage selection bottom=0 sideMin=0 sideMax=0 selected=1.
Fixture U-stage virtual BOX geometry part=28705233 length=3505 width=600 thickness=30 lines=12.
GA fixture U-stage selected=1 lines=12 failed=0 texts=5 dimension=True.
Immediate primitive stats: lines=12 texts=5 dims=4 parts=0 marks=0 views=0
Reopened primitive stats: lines=12 texts=5 dims=4 parts=0 marks=0 views=0
```

输出证据：

- Tekla 图纸名：`PROCESS-FIXTURE-U-10-3GZ-6-S1`
- Tekla 图纸 mark：`[21]`
- JSON：`outputs\tekla-process-drawings-10-3GZ-6\tekla-ga-fixture-u-stage-28717373-step1.json`

当前限制：

- 这是 BOX 主零件的虚拟 U-stage 主视表达，尚未生成正式剖面图。
- 当前标注为总长和总宽维度，下一步需要补零件号引出、胎架基准边、内外侧方向和焊接/放置注释的版式避让。
### U-Stage Dimension Artifact Fix

用户截图中旧图 `PROCESS-FIXTURE-U-10-3GZ-6-S1 / [21]` 出现的黑色三角、蓝色竖排 `Tekla Structures` 和粉色问号，根因是 POC 在 GA sheet 坐标上调用 Tekla 原生 `StraightDimensionSetHandler.CreateDimensionSet()`。这些尺寸点没有关联真实 drawing view/model object，Tekla 将原生尺寸箭头、尺寸文字/占位符渲染到图面上，形成看似乱码的对象。

修正：U-stage 图不再插入 `StraightDimensionSet/StraightDimension`，改用普通 `Line` 和 `Text` 绘制总长/总宽尺寸。

重新生成命令同上，clean 版结果：

```text
Drawing=PROCESS-FIXTURE-U-10-3GZ-6-S1-CLEAN
Mark=[22]
Mode=VIRTUAL_DECOMPOSED_BOX_PROFILE
Lines=22
Texts=7
Dimensions=0
StraightDimensions=0
StraightDimensionSets=0
Parts=0
Marks=0
Views=0
```

结论：旧图 `[21]` 的乱码来自 Tekla 原生尺寸对象；新图 `[22]` 已移除原生尺寸对象，只保留普通线和普通文字。
### U-Stage Annotation Layout DTO Smoke - 2026-07-09

The Tekla U-stage POC now routes stage notes, dimensions, thickness callout, fixture note, and part mark through a layout DTO before rendering. Renderer output uses only ordinary `Line` and `Text` objects for GA sheet annotations.

Command:

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe --probe-ga-fixture-u-stage-model-id 28717373 --source-sheet 0 --out I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6
```

Result:

- Drawing: `PROCESS-FIXTURE-U-10-3GZ-6-S1-CLEAN`
- Mark: `[24]`
- Layout status: `OK`
- Collision count: `0`
- Layout lines/texts: `lines=12 texts=9`
- Primitive dimension flag: `dimension_inserted=False primitive_dimension_lines_inserted=True`
- Reopened stats: `lines=24 texts=9 dimensions=0 straightDimensions=0 straightDimensionSets=0 parts=0 marks=0 views=0`
- JSON evidence: `I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6\tekla-ga-fixture-u-stage-28717373-step1.json`

Decision: keep Tekla GA dimensions as primitive line/text until a drawing-view-bound native dimension path is proven safe. This avoids the black triangle / pink question mark artifacts previously produced by native `StraightDimensionSet` insertion on a GA sheet.