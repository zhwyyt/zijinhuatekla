# Tekla Fixture True Projection GA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one Tekla GA prototype for `10-3GZ-6` that lays the column into a fixture coordinate system and draws stage geometry from Tekla solid edges instead of copied assembly drawing objects.

**Architecture:** Keep the existing `tools/tekla2017_progressive_drawing_poc` command-line POC, but add a new command path instead of modifying the failed AssemblyDrawing hide/copy route. Pure geometry helpers choose a fixture frame, transform model solid edge endpoints into fixture coordinates, project them into drawing coordinates, and emit a verification payload. Tekla-specific code reads model parts, inserts GA `Line/Text/StraightDimensionSet` primitives, saves the drawing, then reopens it to verify primitive object counts.

**Tech Stack:** C#/.NET Framework 4.8, Tekla Structures 2017 Open API, `System.Web.Extensions` JSON serializer, existing PowerShell verification commands.

---

## Files

- Modify: `I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\Program.cs`
  - Add option `--probe-ga-fixture-projection-model-id <id>`.
  - Add fixture-frame and projection helper classes inside the existing POC file to avoid a broad refactor.
  - Add Tekla solid edge extraction and GA primitive insertion.
- Modify: `I:\zijinhuatekla\docs\verification\2026-07-07-tekla-openapi-existing-drawing-inspection.md`
  - Append fixture projection smoke results after the command runs.
- Modify: `I:\zijinhuatekla\STATUS.md`
  - Record the prototype drawing mark, JSON evidence, and known limits.
- Modify: `I:\zijinhuatekla\TASKLIST.md`
  - Mark the failed hide/copy route as superseded by fixture projection GA prototype, while keeping the formal production task open.

## Task 1: Add Fixture Projection Command Skeleton

**Files:**
- Modify: `I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\Program.cs`

- [ ] **Step 1: Add parser and usage entries**

Add `ProbeGaFixtureProjectionModelId` to `Options`, parse `--probe-ga-fixture-projection-model-id`, include it in the no-command guard, and route it near the existing `ProbeGaStageDrawing` block:

```csharp
if (!string.IsNullOrWhiteSpace(options.ProbeGaFixtureProjectionModelId))
{
    return DrawingPocRunner.ProbeGaFixtureProjectionDrawing(
        options.ProbeGaFixtureProjectionModelId,
        options.SourceSheetNumber,
        options.StepNumber,
        options.OutputDirectory,
        Console.Out,
        Console.Error);
}
```

- [ ] **Step 2: Run build to verify the skeleton compiles**

Run:

```powershell
dotnet build I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\BoxProgressiveDrawingPoc.csproj
```

Expected:

```text
0 warnings
0 errors
```

## Task 2: Add Pure Fixture Projection Helpers

**Files:**
- Modify: `I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\Program.cs`

- [ ] **Step 1: Add geometry data structures**

Add focused internal classes near `ModelPartBox`:

```csharp
internal sealed class ModelPartEdge
{
    public string PartId { get; set; }
    public Tekla.Structures.Geometry3d.Point Start { get; set; }
    public Tekla.Structures.Geometry3d.Point End { get; set; }
}

internal sealed class FixtureFrame
{
    public int AxisIndex { get; set; }
    public int WidthIndex { get; set; }
    public int HeightIndex { get; set; }
    public double AxisMin { get; set; }
    public double AxisMax { get; set; }
    public double WidthMin { get; set; }
    public double WidthMax { get; set; }
    public double HeightMin { get; set; }
    public double HeightMax { get; set; }
    public string FixtureFace { get; set; }
}

internal sealed class ProjectedModelEdge
{
    public string PartId { get; set; }
    public double X1 { get; set; }
    public double Y1 { get; set; }
    public double X2 { get; set; }
    public double Y2 { get; set; }
    public double ModelLength { get; set; }
    public double ProjectionLength { get; set; }
}
```

- [ ] **Step 2: Implement fixture frame selection**

Use all selected stage edges to find model extents. The longest extent is the member axis. The larger remaining cross-section extent is drawing vertical width; the smaller remaining extent is fixture height. The minimum fixture height side is treated as the bottom face:

```csharp
private static FixtureFrame BuildFixtureFrame(List<ModelPartEdge> edges)
{
    var points = edges.SelectMany(edge => new[] { edge.Start, edge.End }).ToList();
    var min = new[] { points.Min(point => point.X), points.Min(point => point.Y), points.Min(point => point.Z) };
    var max = new[] { points.Max(point => point.X), points.Max(point => point.Y), points.Max(point => point.Z) };
    var extents = new[] { max[0] - min[0], max[1] - min[1], max[2] - min[2] };
    var axis = 0;
    if (extents[1] > extents[axis]) axis = 1;
    if (extents[2] > extents[axis]) axis = 2;
    var cross = Enumerable.Range(0, 3).Where(index => index != axis).OrderByDescending(index => extents[index]).ToList();
    var width = cross[0];
    var height = cross[1];
    return new FixtureFrame
    {
        AxisIndex = axis,
        WidthIndex = width,
        HeightIndex = height,
        AxisMin = min[axis],
        AxisMax = max[axis],
        WidthMin = min[width],
        WidthMax = max[width],
        HeightMin = min[height],
        HeightMax = max[height],
        FixtureFace = "MODEL_AXIS_" + axis + "_HEIGHT_" + height + "_MIN_ON_FIXTURE",
    };
}
```

- [ ] **Step 3: Implement model-to-fixture projection**

Map member axis to drawing X and fixture width to drawing Y. Do not use fixture height in the main view except for reporting.

```csharp
private static ProjectedModelEdge ProjectEdge(ModelPartEdge edge, FixtureFrame frame)
{
    var x1 = CoordinateAt(edge.Start, frame.AxisIndex) - frame.AxisMin;
    var x2 = CoordinateAt(edge.End, frame.AxisIndex) - frame.AxisMin;
    var y1 = CoordinateAt(edge.Start, frame.WidthIndex) - frame.WidthMin;
    var y2 = CoordinateAt(edge.End, frame.WidthIndex) - frame.WidthMin;
    var modelLength = Distance3d(edge.Start, edge.End);
    var projectionLength = Math.Sqrt((x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1));
    return new ProjectedModelEdge
    {
        PartId = edge.PartId,
        X1 = x1,
        Y1 = y1,
        X2 = x2,
        Y2 = y2,
        ModelLength = modelLength,
        ProjectionLength = projectionLength,
    };
}
```

- [ ] **Step 4: Add helper validation**

Reject empty edge sets and zero-span frames before inserting any drawing:

```csharp
private static bool IsValidFixtureFrame(FixtureFrame frame)
{
    return frame != null
        && Math.Abs(frame.AxisMax - frame.AxisMin) > 1.0
        && Math.Abs(frame.WidthMax - frame.WidthMin) > 1.0;
}
```

## Task 3: Extract Tekla Solid Edges

**Files:**
- Modify: `I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\Program.cs`

- [ ] **Step 1: Implement `ModelPartEdges`**

Select each model `Part`, call `GetSolid()`, enumerate solid edges, and store exact model endpoints. Skip degenerate edges shorter than `0.5mm`.

```csharp
private static List<ModelPartEdge> ModelPartEdges(List<string> visiblePartIds, TextWriter output)
{
    var result = new List<ModelPartEdge>();
    var model = new Tekla.Structures.Model.Model();
    if (!model.GetConnectionStatus())
    {
        output.WriteLine("Model API not connected for solid edge geometry.");
        return result;
    }

    foreach (var partId in visiblePartIds ?? new List<string>())
    {
        int id;
        if (!int.TryParse(partId, out id))
        {
            continue;
        }

        try
        {
            var part = model.SelectModelObject(new Identifier(id)) as Tekla.Structures.Model.Part;
            if (part == null)
            {
                output.WriteLine("Part " + partId + " not found in model.");
                continue;
            }

            var solid = part.GetSolid();
            var edges = solid == null ? null : solid.GetEdgeEnumerator();
            while (edges != null && edges.MoveNext())
            {
                var edge = edges.Current as Tekla.Structures.Solid.Edge;
                if (edge == null || edge.StartPoint == null || edge.EndPoint == null)
                {
                    continue;
                }

                var start = CopyPoint(edge.StartPoint);
                var end = CopyPoint(edge.EndPoint);
                if (Distance3d(start, end) < 0.5)
                {
                    continue;
                }

                result.Add(new ModelPartEdge { PartId = partId, Start = start, End = end });
            }
        }
        catch (Exception ex)
        {
            output.WriteLine("Solid edge read failed for part " + partId + ": " + ExceptionText(ex));
        }
    }

    return result;
}
```

- [ ] **Step 2: Build**

Run:

```powershell
dotnet build I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\BoxProgressiveDrawingPoc.csproj
```

Expected: if `Tekla.Structures.Solid.Edge` is not the correct type name in Tekla 2017, build fails. Fix the type by inspecting the Tekla 2017 API type exposed by `solid.GetEdgeEnumerator().Current`.

## Task 4: Draw GA Fixture Projection

**Files:**
- Modify: `I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\Program.cs`

- [ ] **Step 1: Implement `DrawFixtureProjectionStageGeometry`**

Scale projected edges into a stable GA drawing area and insert ordinary `Line` primitives. Track inserted lines, failed lines, source edge count, part count, and projected bounds.

```csharp
private static StageDrawResult DrawFixtureProjectionStageGeometry(
    ContainerView sheet,
    string assemblyId,
    List<string> visiblePartIds,
    TextWriter output,
    out FixtureFrame frame,
    out List<object> evidence)
{
    evidence = new List<object>();
    var edges = ModelPartEdges(visiblePartIds, output);
    var result = new StageDrawResult();
    frame = edges.Count == 0 ? null : BuildFixtureFrame(edges);
    if (!IsValidFixtureFrame(frame))
    {
        output.WriteLine("No valid fixture frame; solidEdges=" + edges.Count + ".");
        return result;
    }

    var projected = edges.Select(edge => ProjectEdge(edge, frame)).ToList();
    var minX = projected.Min(edge => Math.Min(edge.X1, edge.X2));
    var maxX = projected.Max(edge => Math.Max(edge.X1, edge.X2));
    var minY = projected.Min(edge => Math.Min(edge.Y1, edge.Y2));
    var maxY = projected.Max(edge => Math.Max(edge.Y1, edge.Y2));
    var drawLeft = 35.0;
    var drawBottom = 80.0;
    var drawWidth = 500.0;
    var drawHeight = 180.0;
    var scale = Math.Min(drawWidth / Math.Max(1.0, maxX - minX), drawHeight / Math.Max(1.0, maxY - minY));

    foreach (var edge in projected)
    {
        var x1 = drawLeft + (edge.X1 - minX) * scale;
        var y1 = drawBottom + (edge.Y1 - minY) * scale;
        var x2 = drawLeft + (edge.X2 - minX) * scale;
        var y2 = drawBottom + (edge.Y2 - minY) * scale;
        InsertLine(sheet, x1, y1, x2, y2, result);
        result.Rectangles = 1;
        result.MinX = result.LinesInserted == 1 ? Math.Min(x1, x2) : Math.Min(result.MinX, Math.Min(x1, x2));
        result.MaxX = result.LinesInserted == 1 ? Math.Max(x1, x2) : Math.Max(result.MaxX, Math.Max(x1, x2));
        result.MinY = result.LinesInserted == 1 ? Math.Min(y1, y2) : Math.Min(result.MinY, Math.Min(y1, y2));
        result.MaxY = result.LinesInserted == 1 ? Math.Max(y1, y2) : Math.Max(result.MaxY, Math.Max(y1, y2));
    }

    evidence.Add(new
    {
        visible_part_count = visiblePartIds.Count,
        solid_edge_count = edges.Count,
        projected_edge_count = projected.Count,
        frame = new
        {
            frame.AxisIndex,
            frame.WidthIndex,
            frame.HeightIndex,
            frame.AxisMin,
            frame.AxisMax,
            frame.WidthMin,
            frame.WidthMax,
            frame.HeightMin,
            frame.HeightMax,
            frame.FixtureFace,
        },
        projected_bounds = new { min_x = minX, max_x = maxX, min_y = minY, max_y = maxY },
    });

    output.WriteLine("Fixture true projection edges=" + edges.Count + " insertedLines=" + result.LinesInserted + " frame=" + frame.FixtureFace + ".");
    return result;
}
```

- [ ] **Step 2: Implement `ProbeGaFixtureProjectionDrawing`**

Follow `ProbeGaStageDrawing`, but call `DrawFixtureProjectionStageGeometry` and name the drawing:

```text
PROCESS-FIXTURE-10-3GZ-6-S<step>
```

Insert text notes:

```text
FIXTURE TRUE PROJECTION
STEP <n>
FIXTURE FACE <frame.FixtureFace>
SOURCE solid.GetEdgeEnumerator()
```

Insert one overall dimension using the projected bounds.

- [ ] **Step 3: Run build**

Run:

```powershell
dotnet build I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\BoxProgressiveDrawingPoc.csproj
```

Expected:

```text
0 warnings
0 errors
```

## Task 5: Tekla Smoke Verification

**Files:**
- Modify: `I:\zijinhuatekla\docs\verification\2026-07-07-tekla-openapi-existing-drawing-inspection.md`
- Modify: `I:\zijinhuatekla\STATUS.md`
- Modify: `I:\zijinhuatekla\TASKLIST.md`

- [ ] **Step 1: Run the fixture projection prototype**

Run:

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe `
  --probe-ga-fixture-projection-model-id 28717373 `
  --source-sheet 0 `
  --step 1 `
  --out I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6
```

Expected output must include:

```text
Fixture true projection edges=<positive>
insertedLines=<positive>
Immediate primitive stats: lines=<positive> texts=<positive> dims=<positive> parts=0 marks=0 views=0
Reopened primitive stats: lines=<same positive> texts=<positive> dims=<positive> parts=0 marks=0 views=0
```

- [ ] **Step 2: Validate JSON evidence**

Open:

```text
I:\zijinhuatekla\outputs\tekla-process-drawings-10-3GZ-6\tekla-ga-fixture-projection-28717373-step1.json
```

Verify:

```text
solid_edge_count > 0
projected_edge_count == solid_edge_count
inserted_lines == projected_edge_count
parts == 0
marks == 0
dimensions > 0
texts >= 4
```

- [ ] **Step 3: Close active Tekla drawing**

Run:

```powershell
$env:SESSIONNAME='Console'
I:\zijinhuatekla\tools\tekla2017_progressive_drawing_poc\bin\Debug\net48\BoxProgressiveDrawingPoc.exe --close-active-drawing
```

Expected:

```text
Active drawing: <none>
```

- [ ] **Step 4: Record outcome**

Append a section to the verification document:

```markdown
## Fixture True Projection GA Prototype

- Drawing: `PROCESS-FIXTURE-10-3GZ-6-S1`
- Source: Tekla `Part.GetSolid().GetEdgeEnumerator()`
- Frame: `<fixture_face>`
- Result: `<lines/texts/dimensions/parts/marks/views>`
- Decision: use this route for the next工序图 prototype if lines are readable; otherwise add visible-edge filtering before expanding steps.
```

## Self-Review

- Spec coverage: The plan covers the user's requirement that the column lies on a fixture and that rebuilt geometry must be traceable to Tekla solids.
- Placeholder scan: No placeholder tasks remain; each implementation step names concrete files, commands, and expected evidence.
- Type consistency: New command, helper names, output file name, and verification commands are consistent across tasks.
