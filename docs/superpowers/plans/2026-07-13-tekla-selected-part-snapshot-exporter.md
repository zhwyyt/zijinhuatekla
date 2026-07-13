# Tekla Selected-Part Snapshot Exporter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Tekla Structures 2017 command-line mode that exports each directly selected flat `Part` as an auditable `partDrawingSnapshot.v1` JSON file for the existing Python drawing engine.

**Architecture:** Build a small contract and pure geometry layer in `TeklaSectionClassifier`, then put Tekla selection, Solid-face, bolt, boolean, and report-property adaptation behind `Tekla2017PartDrawingSnapshotExporter`. The Runner only parses the new flag and dispatches; Python remains a separate consumer.

**Tech Stack:** C# / .NET Framework 4.8, Tekla Structures 2017 Open API, `DataContractJsonSerializer`, xUnit 2.9.2, Microsoft.NET.Test.Sdk 17.12.0, Python 3.10+ contract tests.

---

## Scope And Worktree

The source repository `I:\xingcaisuanfa` currently contains extensive uncommitted user work, including modifications to `Program.cs`, project files, geometry extraction, and generated binaries. Do not implement in that working directory.

At execution time, use `superpowers:using-git-worktrees` and create:

```text
Worktree: I:\tmp\xingcaisuanfa-part-snapshot-exporter
Branch:   codex/part-drawing-snapshot-exporter
Base:     codex/upstream-axis-audit-20260428 at current committed HEAD
```

Do not copy uncommitted files from `I:\xingcaisuanfa` into the worktree. Do not clean or modify the original worktree.

## File Structure

- Create: `TeklaSectionClassifier/PartDrawingSnapshotContracts.cs`
  - Versioned JSON DTOs, result/status DTOs, and stable reason codes.
- Create: `TeklaSectionClassifier/PartDrawingGeometry.cs`
  - Pure local-frame validation, projection, loop cleanup/classification, containment, and line-segment creation.
- Create: `TeklaSectionClassifier/PartDrawingSnapshotBuilder.cs`
  - Pure candidate-facts validation and contract assembly.
- Create: `TeklaSectionClassifier/Tekla2017PartDrawingSnapshotExporter.cs`
  - Tekla selection, Part facts, Solid face loops, Contour/Chamfer, BoltGroup, Boolean cut, output, and summary.
- Create: `TeklaSectionClassifier.Tests/TeklaSectionClassifier.Tests.csproj`
- Create: `TeklaSectionClassifier.Tests/PartDrawingSnapshotContractTests.cs`
- Create: `TeklaSectionClassifier.Tests/PartDrawingGeometryTests.cs`
- Create: `TeklaSectionClassifier.Tests/PartDrawingSnapshotBuilderTests.cs`
- Modify: `TeklaSectionClassifier/TeklaSectionClassifier.csproj`
  - Add `System.Runtime.Serialization` explicitly.
- Modify: `TeklaSectionClassifier.Runner/Program.cs`
  - Dispatch the new mode before the existing Web3D/member pipeline.
- Create: `TeklaSectionClassifier.Runner/Properties/AssemblyInfo.cs`
  - Expose internal option parsing only to the named test assembly.
- Modify: `README.md`
  - Document selection semantics, command, outputs, and separate Python command.
- Create: `I:\zijinhuatekla\docs\verification\2026-07-13-tekla-selected-part-snapshot-exporter.md`
  - Record bounded test/build/contract/smoke evidence.

## Task 1: Isolate The Exporter Worktree And Establish Tests

**Files:**
- Create: `TeklaSectionClassifier.Tests/TeklaSectionClassifier.Tests.csproj`
- Modify: `TeklaSectionClassifier/TeklaSectionClassifier.csproj`

- [ ] **Step 1: Create the isolated worktree**

Run from `I:\xingcaisuanfa` after invoking `superpowers:using-git-worktrees`:

```powershell
git worktree add I:\tmp\xingcaisuanfa-part-snapshot-exporter -b codex/part-drawing-snapshot-exporter
```

Expected: new clean worktree at the current committed HEAD; original `I:\xingcaisuanfa` status remains byte-for-byte unchanged.

- [ ] **Step 2: Create the xUnit test project**

Create `TeklaSectionClassifier.Tests/TeklaSectionClassifier.Tests.csproj`:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net48</TargetFramework>
    <LangVersion>latest</LangVersion>
    <Nullable>enable</Nullable>
    <ImplicitUsings>disable</ImplicitUsings>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.12.0" />
    <PackageReference Include="xunit" Version="2.9.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2">
      <PrivateAssets>all</PrivateAssets>
    </PackageReference>
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="..\TeklaSectionClassifier\TeklaSectionClassifier.csproj" />
    <ProjectReference Include="..\TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj" />
  </ItemGroup>
</Project>
```

- [ ] **Step 3: Prove the empty test project builds**

Run:

```powershell
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj --no-restore
```

If assets do not exist, run once without `--no-restore`; package versions are already present in the local NuGet cache. Expected: build succeeds with zero tests.

- [ ] **Step 4: Add serialization assembly reference**

Add to `TeklaSectionClassifier/TeklaSectionClassifier.csproj`:

```xml
<ItemGroup>
  <Reference Include="System.Runtime.Serialization" />
</ItemGroup>
```

- [ ] **Step 5: Commit the test harness**

```powershell
git add TeklaSectionClassifier.Tests/TeklaSectionClassifier.Tests.csproj TeklaSectionClassifier/TeklaSectionClassifier.csproj
git commit -m "test: add exporter test harness"
```

## Task 2: Lock The JSON Contract With A Failing Serialization Test

**Files:**
- Create: `TeklaSectionClassifier/PartDrawingSnapshotContracts.cs`
- Create: `TeklaSectionClassifier.Tests/PartDrawingSnapshotContractTests.cs`

- [ ] **Step 1: Write the failing contract test**

Create `PartDrawingSnapshotContractTests.cs` with a test that constructs the wished-for DTO, serializes it, parses the result with `DataContractJsonSerializer` or string assertions, and requires these exact names:

```csharp
[Fact]
public void Serialize_UsesPartDrawingSnapshotV1Shape()
{
    var snapshot = PartDrawingSnapshotFactory.CreateRectangleForTests(
        partId: "1001",
        partPosition: "P-1001",
        thickness: 10.0);

    var json = PartDrawingSnapshotJson.Serialize(snapshot);

    Assert.Contains("\"schemaVersion\":\"partDrawingSnapshot.v1\"", json);
    Assert.Contains("\"partPosition\":\"P-1001\"", json);
    Assert.Contains("\"origin\":[0,0,0]", json);
    Assert.Contains("\"kind\":\"LINE\"", json);
    Assert.DoesNotContain("PartPosition", json);
}
```

Add a second test requiring `SafeFileStem("P:1001", "42") == "P_1001-42"` and requiring two entity ids to produce different names.

- [ ] **Step 2: Run the test and verify RED**

```powershell
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj --filter PartDrawingSnapshotContractTests
```

Expected: compile failure because `PartDrawingSnapshotFactory`, DTOs, and serializer do not exist.

- [ ] **Step 3: Implement the minimal versioned DTOs**

Create public DataContract DTOs whose members exactly match the Python parser:

```csharp
[DataContract]
public sealed class PartDrawingSnapshotDocument
{
    [DataMember(Name = "schemaVersion", Order = 1)]
    public string SchemaVersion { get; set; } = "partDrawingSnapshot.v1";

    [DataMember(Name = "exporterVersion", Order = 2)]
    public string ExporterVersion { get; set; } = "tekla2017.selectedPart.v1";

    [DataMember(Name = "modelIdentifier", Order = 3)]
    public string ModelIdentifier { get; set; } = string.Empty;

    [DataMember(Name = "exportedAt", Order = 4)]
    public string ExportedAt { get; set; } = string.Empty;

    [DataMember(Name = "part", Order = 5)]
    public PartDrawingSnapshotPart Part { get; set; } = new PartDrawingSnapshotPart();
}
```

Define `PartDrawingSnapshotPart`, `PartDrawingLocalFrame`, `PartDrawingContourSegment`, `PartDrawingHole`, and `PartDrawingCut` with `double[]` for every 3D point/vector so serialization matches Python arrays. The part fields must be `partId`, `partPosition`, `assemblyId`, `name`, `profile`, `material`, `quantity`, `thickness`, `localFrame`, `outerLoop`, `innerLoops`, `holes`, `cuts`, and `sourceEvidence`.

Implement:

```csharp
public static class PartDrawingSnapshotJson
{
    public static string Serialize(PartDrawingSnapshotDocument value)
    {
        using (var stream = new MemoryStream())
        {
            new DataContractJsonSerializer(typeof(PartDrawingSnapshotDocument)).WriteObject(stream, value);
            return Encoding.UTF8.GetString(stream.ToArray());
        }
    }

    public static void Write(string path, PartDrawingSnapshotDocument value)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        File.WriteAllText(path, Serialize(value), new UTF8Encoding(false));
    }

    public static string SafeFileStem(string partPosition, string partId)
    {
        var invalid = new HashSet<char>(Path.GetInvalidFileNameChars());
        var safePosition = new string((partPosition ?? string.Empty)
            .Select(character => invalid.Contains(character) ? '_' : character)
            .ToArray()).Trim(' ', '.');
        return (string.IsNullOrWhiteSpace(safePosition) ? "unnamed-part" : safePosition) + "-" + partId;
    }
}
```

Keep `PartDrawingSnapshotFactory.CreateRectangleForTests` out of production. Replace the test setup with direct DTO construction once the types exist.

- [ ] **Step 4: Run tests and verify GREEN**

```powershell
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj --filter PartDrawingSnapshotContractTests
```

Expected: both tests pass.

- [ ] **Step 5: Commit the contract**

```powershell
git add TeklaSectionClassifier/PartDrawingSnapshotContracts.cs TeklaSectionClassifier.Tests/PartDrawingSnapshotContractTests.cs
git commit -m "feat: add part drawing snapshot contract"
```

## Task 3: Build Deterministic Loop Geometry

**Files:**
- Create: `TeklaSectionClassifier/PartDrawingGeometry.cs`
- Create: `TeklaSectionClassifier.Tests/PartDrawingGeometryTests.cs`

- [ ] **Step 1: Write failing loop tests**

Add focused tests for:

```csharp
[Fact]
public void ClassifyLoops_SelectsLargestContainingLoopAsOuter()
{
    var frame = TestFrames.WorldXY;
    var outer = Points.Rectangle(0, 0, 200, 100);
    var inner = Points.Rectangle(20, 20, 40, 40);

    var result = PartDrawingGeometry.ClassifyLoops(new[] { inner, outer }, frame, 0.01);

    Assert.Equal(4, result.OuterLoop.Count);
    Assert.Single(result.InnerLoops);
    Assert.Empty(result.Issues);
}
```

Also test adjacent duplicate removal, reversed input direction, an open/degenerate loop, a self-intersection, and two disconnected outer loops returning `MULTIPLE_OUTER_LOOPS`.

- [ ] **Step 2: Run and verify RED**

```powershell
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj --filter PartDrawingGeometryTests
```

Expected: compile failure because geometry APIs do not exist.

- [ ] **Step 3: Implement minimal pure geometry**

Provide these public contracts:

```csharp
public sealed class PartDrawingFrame
{
    public Point3D Origin { get; set; } = new Point3D();
    public Vector3D XAxis { get; set; } = new Vector3D(1, 0, 0);
    public Vector3D YAxis { get; set; } = new Vector3D(0, 1, 0);
    public Vector3D Normal { get; set; } = new Vector3D(0, 0, 1);
}

public sealed class PartDrawingLoopClassification
{
    public List<Point3D> OuterLoop { get; } = new List<Point3D>();
    public List<List<Point3D>> InnerLoops { get; } = new List<List<Point3D>>();
    public List<string> Issues { get; } = new List<string>();
}
```

Implement `ValidateFrame`, `Project`, `CleanLoop`, `SignedArea`, `PointInPolygon`, `SegmentsIntersect`, and `ClassifyLoops`. Use `0.01 mm` cleanup tolerance and do not close a true geometric gap larger than tolerance. Convert a valid vertex loop to LINE segments with the last segment ending at the first point.

- [ ] **Step 4: Verify GREEN and refactor only after green**

```powershell
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj --filter PartDrawingGeometryTests
```

Expected: all loop tests pass.

- [ ] **Step 5: Commit pure geometry**

```powershell
git add TeklaSectionClassifier/PartDrawingGeometry.cs TeklaSectionClassifier.Tests/PartDrawingGeometryTests.cs
git commit -m "feat: classify flat part face loops"
```

## Task 4: Add The Pure Quality Gate And Snapshot Builder

**Files:**
- Create: `TeklaSectionClassifier/PartDrawingSnapshotBuilder.cs`
- Create: `TeklaSectionClassifier.Tests/PartDrawingSnapshotBuilderTests.cs`

- [ ] **Step 1: Write failing candidate tests**

Define tests against a pure `PartDrawingCandidateFacts` input. Cover:

- valid rectangle produces `EXPORTED`, `quantity=1`, and source evidence;
- missing `partPosition` returns `PART_POSITION_MISSING`;
- non-positive thickness returns `THICKNESS_UNRESOLVED`;
- bent/unsupported type returns `UNSUPPORTED_PART_TYPE`;
- invalid frame returns `LOCAL_FRAME_INVALID`;
- multiple outer loops returns `MULTIPLE_OUTER_LOOPS`;
- `HasUnresolvedCurvedEdge=true` returns `UNSUPPORTED_CURVE_GEOMETRY`.

The primary test should read:

```csharp
var result = new PartDrawingSnapshotBuilder().Build(Candidates.Rectangle());
Assert.Equal(PartDrawingExportStatus.Exported, result.Status);
Assert.Equal("P-1001", result.Snapshot.Part.PartPosition);
Assert.Equal(1, result.Snapshot.Part.Quantity);
```

- [ ] **Step 2: Run and verify RED**

```powershell
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj --filter PartDrawingSnapshotBuilderTests
```

Expected: compile failure because candidate, result, and builder do not exist.

- [ ] **Step 3: Implement the minimal builder**

Create:

```csharp
public enum PartDrawingExportStatus { Exported, Skipped, Rejected }

public sealed class PartDrawingBuildResult
{
    public PartDrawingExportStatus Status { get; set; }
    public string ReasonCode { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public PartDrawingSnapshotDocument? Snapshot { get; set; }
}
```

`PartDrawingCandidateFacts` contains only plain values: identity/properties, frame, face loops, explicit contour segments, holes, cuts, evidence, `IsSupportedPlate`, and `HasUnresolvedCurvedEdge`. `Build()` validates in stable order, classifies loops, prefers explicit proven ARC segments only when they match the final loop endpoints, otherwise emits final LINE segments.

- [ ] **Step 4: Run focused and complete tests**

```powershell
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj --filter PartDrawingSnapshotBuilderTests
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj
```

Expected: all tests pass.

- [ ] **Step 5: Commit the quality gate**

```powershell
git add TeklaSectionClassifier/PartDrawingSnapshotBuilder.cs TeklaSectionClassifier.Tests/PartDrawingSnapshotBuilderTests.cs
git commit -m "feat: validate flat part snapshot candidates"
```

## Task 5: Adapt Tekla 2017 Selection And Final Solid Facts

**Files:**
- Create: `TeklaSectionClassifier/Tekla2017PartDrawingSnapshotExporter.cs`

- [ ] **Step 1: Add an adapter seam before Tekla code**

Introduce internal interfaces for the only hard-to-test boundaries:

```csharp
internal interface ISelectedModelObjects
{
    IEnumerable<ModelObject> Read();
}

internal interface IPartDrawingSnapshotSink
{
    string Write(PartDrawingSnapshotDocument snapshot, string directory);
    void WriteSummary(PartDrawingExportSummary summary, string directory);
}
```

The default implementations use `Tekla.Structures.Model.UI.ModelObjectSelector` and `PartDrawingSnapshotJson`. Do not add test-only methods to production classes.

- [ ] **Step 2: Write a failing selection-orchestration test**

Use a fake `ISelectedModelObjects` returning plain injectable candidate sources through a small `IPartDrawingCandidateExtractor` seam. Require that duplicate part ids are processed once, non-Part objects are `SKIPPED`, and one rejected candidate does not prevent another export.

Run and verify failure before implementation:

```powershell
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj --filter PartDrawingExporterOrchestrationTests
```

- [ ] **Step 3: Implement selection orchestration**

`Tekla2017PartDrawingSnapshotExporter.Export(Model model, string outputRoot)` must:

1. enumerate direct selected objects;
2. deduplicate Part identifiers;
3. call the candidate extractor per Part inside an isolated try/catch;
4. call the pure builder;
5. write `<safe-partPosition>-<partId>.json` only for `EXPORTED`;
6. append bounded summary entries for all statuses;
7. write `export-summary.json` even when no part is exported;
8. return exit code `0` only when at least one item is exported and none is rejected.

- [ ] **Step 4: Implement final Solid face-loop extraction**

For each candidate Part:

- reject `BentPlate`;
- accept `ContourPlate` or a profile beginning with `PL`;
- read `PART_POS`/`PART_POSITION` with exact report-property fallback order and never infer it;
- read thickness from explicit report properties then verified `PL` parsing;
- build an orthonormal frame from `GetCoordinateSystem()`;
- enumerate `part.GetSolid().GetFaceEnumerator()`;
- retain faces whose normal is parallel to the plate normal within the documented angle tolerance;
- enumerate each face's loops with `GetLoopEnumerator()` and ordered vertices with `GetVertexEnumerator()`;
- choose the valid face that yields the greatest outer projected area;
- pass its loops to the pure builder.

Do not use global unordered `SolidEdges` to build loops. Do not use bounding-box minimum dimension as thickness.

- [ ] **Step 5: Verify adapter tests and build**

```powershell
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj
dotnet build TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj
```

Expected: tests and build pass without requiring a live Tekla connection.

- [ ] **Step 6: Commit the Tekla adapter**

```powershell
git add TeklaSectionClassifier/Tekla2017PartDrawingSnapshotExporter.cs TeklaSectionClassifier.Tests/PartDrawingExporterOrchestrationTests.cs
git commit -m "feat: export selected Tekla part facts"
```

## Task 6: Add Holes, Cuts, And Proven Curves

**Files:**
- Modify: `TeklaSectionClassifier/Tekla2017PartDrawingSnapshotExporter.cs`
- Modify: `TeklaSectionClassifier/PartDrawingSnapshotBuilder.cs`
- Modify: `TeklaSectionClassifier.Tests/PartDrawingSnapshotBuilderTests.cs`

- [ ] **Step 1: Write failing hole mapping tests**

Against plain `PartDrawingHoleFacts`, require:

- ordinary BoltGroup -> `kind=ROUND`, `diameter=BoltSize`, center preserved;
- slot with one positive slot extension -> `kind=SLOT`, `length=BoltSize+extension`, `width=BoltSize`, direction from bolt coordinate frame;
- duplicate BoltGroup positions collapse by group id plus center tolerance;
- hole belonging only to a different part is excluded.

- [ ] **Step 2: Run and verify RED**

```powershell
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj --filter "PartDrawingSnapshotBuilderTests"
```

Expected: failing assertions because hole mapping does not exist.

- [ ] **Step 3: Implement BoltGroup facts**

Read `Part.GetBolts()`, deduplicate by BoltGroup identifier, verify the selected Part is one of the bolted parts, and export positions from `BoltPositions`. Use `HoleType`, `SlottedHoleX`, `SlottedHoleY`, and `RotateSlots`; do not derive hole centers from BoltGroup solid bounding boxes.

- [ ] **Step 4: Write and implement cut evidence tests**

Require each `BooleanPart` cut to produce a bounded dictionary/object containing operation id, type, operative part id, and bounding box. Fitting evidence must identify its runtime type and source id when accessible. The builder passes these facts into `cuts` without interpreting machining dimensions.

- [ ] **Step 5: Write and implement curve rejection tests**

Map explicit ContourPoint Chamfer evidence to ARC only when center and direction can be deterministically computed and matched to the final outer loop. If Tekla reports a curved Solid edge but no supported Chamfer evidence matches it, set `HasUnresolvedCurvedEdge=true` and reject with `UNSUPPORTED_CURVE_GEOMETRY`.

- [ ] **Step 6: Run all C# tests and build**

```powershell
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj
dotnet build TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj
```

- [ ] **Step 7: Commit operations support**

```powershell
git add TeklaSectionClassifier/Tekla2017PartDrawingSnapshotExporter.cs TeklaSectionClassifier/PartDrawingSnapshotBuilder.cs TeklaSectionClassifier.Tests/PartDrawingSnapshotBuilderTests.cs
git commit -m "feat: export selected part holes and cuts"
```

## Task 7: Wire The Runner Flag Without Changing Default Behavior

**Files:**
- Modify: `TeklaSectionClassifier.Runner/Program.cs`
- Create: `TeklaSectionClassifier.Runner/Properties/AssemblyInfo.cs`
- Create: `TeklaSectionClassifier.Tests/RunnerOptionTests.cs`

- [ ] **Step 1: Write a failing option test**

Create `TeklaSectionClassifier.Runner/Properties/AssemblyInfo.cs` with the narrow test visibility declaration:

```csharp
using System.Runtime.CompilerServices;

[assembly: InternalsVisibleTo("TeklaSectionClassifier.Tests")]
```

Require:

```csharp
var options = RunnerOptions.Parse(new[] { "--export-part-drawing-snapshots", "--output", "out" });
Assert.True(options.ExportPartDrawingSnapshots);
Assert.Equal("out", options.OutputDirectory);
```

Also require an empty argument list to leave the new property false.

- [ ] **Step 2: Run and verify RED**

Expected: compile failure or false assertion because the property/flag does not exist.

- [ ] **Step 3: Implement the flag and dispatch**

Add `ExportPartDrawingSnapshots` to `RunnerOptions`, parse the exact flag, and dispatch immediately after successful model connection:

```csharp
if (options.ExportPartDrawingSnapshots)
{
    var exporter = new Tekla2017PartDrawingSnapshotExporter();
    var result = exporter.Export(model, options.OutputDirectory);
    Console.WriteLine($"零件图快照导出: EXPORTED={result.ExportedCount}, SKIPPED={result.SkippedCount}, REJECTED={result.RejectedCount}");
    Console.WriteLine($"快照目录: {result.OutputDirectory}");
    return result.ExitCode;
}
```

This branch must appear before Web3D and member extraction so it cannot call the existing Assembly expansion path.

- [ ] **Step 4: Run option tests, all tests, and build**

```powershell
dotnet test TeklaSectionClassifier.Tests\TeklaSectionClassifier.Tests.csproj
dotnet build TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj
```

- [ ] **Step 5: Commit Runner integration**

```powershell
git add TeklaSectionClassifier.Runner/Program.cs TeklaSectionClassifier.Runner/Properties/AssemblyInfo.cs TeklaSectionClassifier.Tests/RunnerOptionTests.cs
git commit -m "feat: add selected part snapshot command"
```

## Task 8: Prove Cross-Language Compatibility

**Files:**
- Modify: `README.md`
- Create: `I:\zijinhuatekla\docs\verification\2026-07-13-tekla-selected-part-snapshot-exporter.md`

- [ ] **Step 1: Generate a deterministic C# contract fixture**

Use the test builder to write a rectangle snapshot into a temporary test output. Do not hand-edit the JSON.

- [ ] **Step 2: Parse it with the Python consumer**

From `I:\tmp\zijinhuatekla-part-drawing-engine` run a bounded command or focused test that calls:

```python
snapshot = load_part_snapshot(Path(csharp_output))
assert snapshot.schema_version == "partDrawingSnapshot.v1"
assert snapshot.part_position == "P-1001"
assert snapshot.thickness == 10.0
assert len(snapshot.outer_loop) == 4
```

Then run:

```powershell
python -m unittest tests.test_part_drawing_contracts tests.test_part_drawing_geometry tests.test_part_drawing_pipeline
```

Expected: all focused Python tests pass.

- [ ] **Step 3: Document exact operator workflow**

Add to README:

```powershell
TeklaSectionClassifier.Runner.exe --export-part-drawing-snapshots --output I:\exports\selected-parts
python -m zijinhua_tekla.cli draw-parts --snapshot-root I:\exports\selected-parts\part-drawing-snapshots --out I:\exports\selected-part-drawings
```

State clearly: select Part objects directly; Assembly selection is ignored; C# does not invoke Python.

- [ ] **Step 4: Record automatic evidence**

In the verification document record commit, test counts, build result, C# fixture path, Python parse assertions, and any unverified Tekla-only behavior. Keep stdout summaries bounded.

- [ ] **Step 5: Run CCG verify-change and commit docs**

Run the repository-scoped `verify-change` gate, then:

```powershell
git add README.md
git commit -m "docs: explain selected part snapshot export"
```

Commit the main-project verification record separately in `I:\zijinhuatekla`, without including unrelated changes.

## Task 9: Run A Real Tekla Selection Smoke

**Files:**
- Modify: `I:\zijinhuatekla\docs\verification\2026-07-13-tekla-selected-part-snapshot-exporter.md`
- Modify: `I:\zijinhuatekla\STATUS.md`
- Modify: `I:\zijinhuatekla\TASKLIST.md`

- [ ] **Step 1: Confirm preconditions**

Tekla 2017 must be open with a model connected. Select at least one direct ordinary flat Part, preferably one rectangle and one plate with holes. Do not select an Assembly as a substitute.

- [ ] **Step 2: Run the real exporter**

```powershell
I:\tmp\xingcaisuanfa-part-snapshot-exporter\TeklaSectionClassifier.Runner\bin\Debug\net48\TeklaSectionClassifier.Runner.exe --export-part-drawing-snapshots --output I:\tmp\tekla-selected-part-snapshot-smoke-20260713
```

Expected: `export-summary.json` exists; at least one `EXPORTED`; no silent curve degradation.

- [ ] **Step 3: Run Python drawings**

```powershell
python -m zijinhua_tekla.cli draw-parts --snapshot-root I:\tmp\tekla-selected-part-snapshot-smoke-20260713\part-drawing-snapshots --out outputs\tekla-selected-part-drawing-smoke-20260713
```

Run from the offline-engine worktree. Expected: per-position drawing output or explicit review/rejection evidence.

- [ ] **Step 4: Audit outputs**

Run focused Python/full regression as proportional verification, `ezdxf.audit()` on generated DXF, and PDF readback. Manually compare part position, material, thickness, contour, holes, and slots against Tekla.

- [ ] **Step 5: Record truthfully**

If Tekla is unavailable or no suitable selection exists, record that real smoke is pending and do not claim end-to-end completion. If it succeeds, record selected entity ids/positions only as concise evidence, not a full model dump.

- [ ] **Step 6: Run final gates**

Invoke `superpowers:verification-before-completion`, run CCG `verify-change`, and perform one narrow semantic review before any merge decision. PR #1 remains unmerged until the user accepts the generated drawing visually.

## Plan Self-Review

- Spec coverage: command isolation, direct selection semantics, strict position, flatness/thickness/frame gates, final face loops, holes/slots, cuts, curve rejection, summary/exit behavior, default-mode regression, cross-language parsing, and real smoke each have an implementation and verification task.
- Placeholder scan: no TBD/TODO or unspecified “handle errors” steps remain.
- Type consistency: the plan consistently uses `PartDrawingSnapshotDocument`, `PartDrawingCandidateFacts`, `PartDrawingBuildResult`, `PartDrawingExportSummary`, and `Tekla2017PartDrawingSnapshotExporter`.
- Scope: no DXF/PDF renderer work or existing member-export refactor is included.
