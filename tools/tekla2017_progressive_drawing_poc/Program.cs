using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Web.Script.Serialization;
using Tekla.Structures;
using Tekla.Structures.Drawing.Automation;
using Tekla.Structures.Drawing;
using Tekla.Structures.Model.Operations;

namespace ZijinhuaTekla.ProgressiveDrawingPoc
{
    internal static class Program
    {
        private static int Main(string[] args)
        {
            var options = Options.Parse(args);
            if (
                string.IsNullOrWhiteSpace(options.StepsPath)
                && !options.ListDrawings
                && !options.SelectedModel
                && string.IsNullOrWhiteSpace(options.InspectDrawingModelId)
                && string.IsNullOrWhiteSpace(options.GenerateProcessDrawingsModelId)
                && string.IsNullOrWhiteSpace(options.InspectProcessSheetsModelId)
                && string.IsNullOrWhiteSpace(options.ProbeNativeProcessDrawingModelId)
                && string.IsNullOrWhiteSpace(options.ProbeCloneDrawingModelId)
                && string.IsNullOrWhiteSpace(options.ProbeDrawingFilterOptionsModelId)
                && string.IsNullOrWhiteSpace(options.ProbeCopyAnnotationsModelId)
                && string.IsNullOrWhiteSpace(options.ProbePrunePartsModelId)
                && string.IsNullOrWhiteSpace(options.ProbeRestrictViewPartsModelId)
                && string.IsNullOrWhiteSpace(options.ProbeRelatedObjectsModelId)
                && string.IsNullOrWhiteSpace(options.ProbeGaStageModelId)
                && string.IsNullOrWhiteSpace(options.ProbeGaFixtureProjectionModelId)
                && string.IsNullOrWhiteSpace(options.ProbeGaFixtureUStageModelId)
                && string.IsNullOrWhiteSpace(options.DeleteDrawingModelId)
                && string.IsNullOrWhiteSpace(options.OpenCloseDrawingModelId)
                && !options.CloseActiveDrawing
            )
            {
                Console.Error.WriteLine("Usage: BoxProgressiveDrawingPoc --steps <steps.json> [--step 1] [--dry-run] [--create-drawing] [--run-macro] [--list-drawings] [--selected-model] [--close-active-drawing] [--inspect-drawing-model-id <id>] [--generate-process-drawings-model-id <id>] [--inspect-process-sheets-model-id <id>] [--probe-native-process-drawing-model-id <id>] [--probe-clone-drawing-model-id <id>] [--probe-drawing-filter-options-model-id <id>] [--probe-copy-annotations-model-id <id> --source-sheet <n> --target-sheet <n>] [--probe-prune-parts-model-id <id> --source-sheet <n> --target-sheet <n> --step <n>] [--probe-ga-fixture-projection-model-id <id> --source-sheet <n> --step <n>] [--probe-ga-fixture-u-stage-model-id <id> --source-sheet <n>] [--delete-drawing-model-id <id> --delete-sheet <n>] [--open-close-drawing-model-id <id> --drawing-sheet <n>] [--out <dir>]");
                return 2;
            }

            EnsureTeklaSessionName();

            if (options.SelectedModel)
            {
                return DrawingPocRunner.ListSelectedModelObjects(Console.Out, Console.Error);
            }

            if (options.CloseActiveDrawing)
            {
                return DrawingPocRunner.CloseActiveDrawing(Console.Out, Console.Error);
            }

            if (!string.IsNullOrWhiteSpace(options.DeleteDrawingModelId))
            {
                return DrawingPocRunner.DeleteDrawingSheet(options.DeleteDrawingModelId, options.DeleteSheetNumber, Console.Out, Console.Error);
            }

            if (!string.IsNullOrWhiteSpace(options.OpenCloseDrawingModelId))
            {
                return DrawingPocRunner.OpenAndCloseDrawingSheet(options.OpenCloseDrawingModelId, options.DrawingSheetNumber, Console.Out, Console.Error);
            }

            if (!string.IsNullOrWhiteSpace(options.InspectDrawingModelId))
            {
                return DrawingPocRunner.InspectDrawingByModelId(options.InspectDrawingModelId, Console.Out, Console.Error);
            }

            if (!string.IsNullOrWhiteSpace(options.GenerateProcessDrawingsModelId))
            {
                return DrawingPocRunner.GenerateProcessDrawings(options.GenerateProcessDrawingsModelId, options.OutputDirectory, Console.Out, Console.Error);
            }

            if (!string.IsNullOrWhiteSpace(options.InspectProcessSheetsModelId))
            {
                return DrawingPocRunner.InspectProcessSheets(options.InspectProcessSheetsModelId, options.OutputDirectory, Console.Out, Console.Error);
            }

            if (!string.IsNullOrWhiteSpace(options.ProbeNativeProcessDrawingModelId))
            {
                return DrawingPocRunner.ProbeNativeProcessDrawing(options.ProbeNativeProcessDrawingModelId, options.OutputDirectory, Console.Out, Console.Error);
            }

            if (!string.IsNullOrWhiteSpace(options.ProbeCloneDrawingModelId))
            {
                return DrawingPocRunner.ProbeCloneDrawing(options.ProbeCloneDrawingModelId, options.OutputDirectory, Console.Out, Console.Error);
            }

            if (!string.IsNullOrWhiteSpace(options.ProbeDrawingFilterOptionsModelId))
            {
                return DrawingPocRunner.ProbeDrawingFilterOptions(options.ProbeDrawingFilterOptionsModelId, options.OutputDirectory, Console.Out, Console.Error);
            }

            if (!string.IsNullOrWhiteSpace(options.ProbeCopyAnnotationsModelId))
            {
                return DrawingPocRunner.ProbeCopyAnnotations(
                    options.ProbeCopyAnnotationsModelId,
                    options.SourceSheetNumber,
                    options.TargetSheetNumber,
                    options.OutputDirectory,
                    Console.Out,
                    Console.Error);
            }

            if (!string.IsNullOrWhiteSpace(options.ProbePrunePartsModelId))
            {
                return DrawingPocRunner.ProbePruneParts(
                    options.ProbePrunePartsModelId,
                    options.SourceSheetNumber,
                    options.TargetSheetNumber,
                    options.StepNumber,
                    options.OutputDirectory,
                    Console.Out,
                    Console.Error);
            }

            if (!string.IsNullOrWhiteSpace(options.ProbeRestrictViewPartsModelId))
            {
                return DrawingPocRunner.ProbeRestrictViewParts(
                    options.ProbeRestrictViewPartsModelId,
                    options.SourceSheetNumber,
                    options.TargetSheetNumber,
                    options.StepNumber,
                    options.OutputDirectory,
                    Console.Out,
                    Console.Error);
            }

            if (!string.IsNullOrWhiteSpace(options.ProbeRelatedObjectsModelId))
            {
                return DrawingPocRunner.ProbePartRelatedObjects(
                    options.ProbeRelatedObjectsModelId,
                    options.SourceSheetNumber,
                    options.OutputDirectory,
                    Console.Out,
                    Console.Error);
            }

            if (!string.IsNullOrWhiteSpace(options.ProbeGaStageModelId))
            {
                return DrawingPocRunner.ProbeGaStageDrawing(
                    options.ProbeGaStageModelId,
                    options.SourceSheetNumber,
                    options.StepNumber,
                    options.OutputDirectory,
                    Console.Out,
                    Console.Error);
            }

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

            if (!string.IsNullOrWhiteSpace(options.ProbeGaFixtureUStageModelId))
            {
                return DrawingPocRunner.ProbeGaFixtureUStageDrawing(
                    options.ProbeGaFixtureUStageModelId,
                    options.SourceSheetNumber,
                    options.OutputDirectory,
                    Console.Out,
                    Console.Error);
            }

            if (options.ListDrawings)
            {
                return DrawingPocRunner.ListDrawings(options, Console.Out, Console.Error);
            }

            StepPayload payload;
            try
            {
                payload = StepPayload.Load(options.StepsPath);
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("Failed to read steps JSON: " + ex.Message);
                return 3;
            }

            var step = payload.StepByNumber(options.StepNumber) ?? payload.Steps.FirstOrDefault();
            if (step == null)
            {
                Console.Error.WriteLine("No drawing steps found in " + options.StepsPath);
                return 4;
            }

            Console.WriteLine("Loaded member: " + payload.MemberId);
            Console.WriteLine("Loaded assembly: " + payload.AssemblyId);
            Console.WriteLine("Loaded steps: " + payload.Steps.Count);
            Console.WriteLine("Selected step: " + step.StepNo + " " + step.StepType);
            Console.WriteLine("Visible parts: " + step.VisiblePartIds.Count);
            Console.WriteLine("New parts: " + step.NewPartIds.Count);

            if (options.DryRun)
            {
                return 0;
            }

            if (options.RunMacro)
            {
                return TeklaMacroLauncher.Run(options);
            }

            return DrawingPocRunner.ApplyStepToActiveDrawing(payload, step, options.CreateDrawing, Console.Out, Console.Error);
        }

        private static void EnsureTeklaSessionName()
        {
            if (!string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("SESSIONNAME")))
            {
                return;
            }

            Environment.SetEnvironmentVariable("SESSIONNAME", "Console", EnvironmentVariableTarget.Process);
        }
    }

    public static class MacroEntry
    {
        public static int Run(string configPath)
        {
            var logPath = Path.Combine(Path.GetTempPath(), "BoxProgressiveDrawingPoc.macro.log");
            using (var writer = new StreamWriter(logPath, true))
            {
                writer.WriteLine("[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "] MacroEntry start");
                try
                {
                    var options = Options.LoadConfig(configPath);
                    var payload = StepPayload.Load(options.StepsPath);
                    var step = payload.StepByNumber(options.StepNumber) ?? payload.Steps.FirstOrDefault();
                    if (step == null)
                    {
                        writer.WriteLine("No drawing steps found in " + options.StepsPath);
                        return 4;
                    }

                    return DrawingPocRunner.ApplyStepToActiveDrawing(payload, step, options.CreateDrawing, writer, writer);
                }
                catch (Exception ex)
                {
                    writer.WriteLine(ex);
                    return 99;
                }
            }
        }
    }

    public static class DrawingPocRunner
    {
        public static int InspectProcessSheets(string modelId, string outputDirectory, TextWriter output, TextWriter error)
        {
            try
            {
                var handler = new DrawingHandler();
                if (!handler.GetConnectionStatus())
                {
                    error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                    return 10;
                }

                var drawings = DrawingsByModelId(handler, modelId).OrderBy(item => item.SheetNumber).ToList();
                if (drawings.Count == 0)
                {
                    error.WriteLine("No drawings found for modelId=" + modelId + ".");
                    return 50;
                }

                outputDirectory = string.IsNullOrWhiteSpace(outputDirectory)
                    ? Path.Combine("outputs", "tekla-process-drawings-" + modelId)
                    : outputDirectory;
                Directory.CreateDirectory(outputDirectory);

                var rows = new List<object>();
                foreach (var drawing in drawings)
                {
                    try
                    {
                        if (!handler.SetActiveDrawing(drawing, true))
                        {
                            output.WriteLine("Could not open drawing sheet=" + drawing.SheetNumber + ".");
                            rows.Add(new { sheet = drawing.SheetNumber, opened = false });
                            continue;
                        }

                        var active = handler.GetActiveDrawing() as AssemblyDrawing ?? drawing;
                        var sheet = active.GetSheet();
                        if (sheet == null)
                        {
                            output.WriteLine("Drawing sheet=" + active.SheetNumber + " has no sheet view.");
                            rows.Add(new { sheet = active.SheetNumber, opened = true, has_sheet = false });
                            handler.CloseActiveDrawing(false);
                            continue;
                        }

                        var stats = DrawingSheetStats(active, sheet);
                        rows.Add(stats);
                        output.WriteLine(
                            "sheet=" + stats.Sheet
                            + " mark=" + stats.Mark
                            + " parts=" + stats.Parts
                            + " visibleParts=" + stats.VisibleParts
                            + " hiddenParts=" + stats.HiddenParts
                            + " marks=" + stats.Marks
                            + " dimensions=" + stats.Dimensions
                            + " texts=" + stats.Texts
                            + " weldMarks=" + stats.WeldMarks
                            + " views=" + stats.Views
                        );
                        handler.CloseActiveDrawing(false);
                    }
                    catch (Exception ex)
                    {
                        output.WriteLine("Inspect failed for sheet=" + drawing.SheetNumber + ": " + ExceptionText(ex));
                        rows.Add(new { sheet = drawing.SheetNumber, opened = false, exception = ExceptionText(ex) });
                        try
                        {
                            handler.CloseActiveDrawing(false);
                        }
                        catch
                        {
                            // Ignore Tekla cleanup failures in read-only inspection.
                        }
                    }
                }

                var path = Path.Combine(outputDirectory, "tekla-process-sheets-inspection-" + modelId + ".json");
                File.WriteAllText(path, new JavaScriptSerializer().Serialize(new { model_id = modelId, sheets = rows }));
                output.WriteLine("Wrote inspection: " + Path.GetFullPath(path));
                return 0;
            }
            catch (Exception ex)
            {
                error.WriteLine("InspectProcessSheets failed: " + ExceptionText(ex));
                return 59;
            }
        }

        public static int CloseActiveDrawing(TextWriter output, TextWriter error)
        {
            try
            {
                var handler = new DrawingHandler();
                if (!handler.GetConnectionStatus())
                {
                    error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                    return 10;
                }

                var active = handler.GetActiveDrawing();
                if (active == null)
                {
                    output.WriteLine("Active drawing: <none>");
                    return 0;
                }

                output.WriteLine("Closing active drawing: " + DrawingSummary(active, null));
                if (!handler.CloseActiveDrawing(false))
                {
                    output.WriteLine("CloseActiveDrawing(false) returned false; retrying with save=true.");
                    if (!handler.CloseActiveDrawing(true))
                    {
                        output.WriteLine("CloseActiveDrawing(true) returned false; trying to reopen active drawing visibly before close.");
                        try
                        {
                            output.WriteLine("SetActiveDrawing(active, true) returned " + handler.SetActiveDrawing(active, true) + ".");
                            try
                            {
                                active.CommitChanges();
                                output.WriteLine("CommitChanges() attempted before final close.");
                            }
                            catch (Exception ex)
                            {
                                output.WriteLine("CommitChanges() before final close failed: " + ExceptionText(ex));
                            }

                            output.WriteLine("SaveActiveDrawing() returned " + handler.SaveActiveDrawing() + ".");
                        }
                        catch (Exception ex)
                        {
                            output.WriteLine("Reopen/save before final close failed: " + ExceptionText(ex));
                        }

                        if (!handler.CloseActiveDrawing())
                        {
                            output.WriteLine("CloseActiveDrawing() returned false; trying Tekla UI macro close.");
                            if (!RunMacroAndWait(@"FabricationInspectionDrawings\CloseDrawingEditor.cs", output))
                            {
                                error.WriteLine("Tekla UI macro close failed.");
                                return 11;
                            }

                            Thread.Sleep(1000);
                            var stillActive = handler.GetActiveDrawing();
                            if (stillActive != null)
                            {
                                error.WriteLine("Tekla UI macro close ran but active drawing remains: " + DrawingSummary(stillActive, null));
                                return 11;
                            }

                            output.WriteLine("Active drawing closed by Tekla UI macro.");
                            return 0;
                        }

                        output.WriteLine("Active drawing closed with no-argument fallback.");
                        return 0;
                    }

                    output.WriteLine("Active drawing closed with save=true fallback.");
                    return 0;
                }

                output.WriteLine("Active drawing closed without saving.");
                return 0;
            }
            catch (Exception ex)
            {
                error.WriteLine("CloseActiveDrawing failed: " + ExceptionText(ex));
                return 12;
            }
        }

        public static int DeleteDrawingSheet(string modelId, int sheetNumber, TextWriter output, TextWriter error)
        {
            if (sheetNumber < 0)
            {
                error.WriteLine("--delete-sheet must be >= 0.");
                return 2;
            }

            try
            {
                var handler = new DrawingHandler();
                if (!handler.GetConnectionStatus())
                {
                    error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                    return 10;
                }

                var drawing = DrawingsByModelId(handler, modelId).FirstOrDefault(item => item.SheetNumber == sheetNumber);
                if (drawing == null)
                {
                    output.WriteLine("No drawing found for modelId=" + modelId + " sheet=" + sheetNumber + ".");
                    return 0;
                }

                output.WriteLine("Deleting drawing: " + DrawingSummary(drawing, null));
                if (!drawing.Delete())
                {
                    error.WriteLine("Drawing.Delete() returned false.");
                    return 71;
                }

                output.WriteLine("Drawing deleted.");
                return 0;
            }
            catch (Exception ex)
            {
                error.WriteLine("DeleteDrawingSheet failed: " + ExceptionText(ex));
                return 72;
            }
        }

        public static int OpenAndCloseDrawingSheet(string modelId, int sheetNumber, TextWriter output, TextWriter error)
        {
            if (sheetNumber < 0)
            {
                error.WriteLine("--drawing-sheet must be >= 0.");
                return 2;
            }

            try
            {
                var handler = new DrawingHandler();
                if (!handler.GetConnectionStatus())
                {
                    error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                    return 10;
                }

                var drawing = DrawingsByModelId(handler, modelId).FirstOrDefault(item => item.SheetNumber == sheetNumber);
                if (drawing == null)
                {
                    error.WriteLine("No drawing found for modelId=" + modelId + " sheet=" + sheetNumber + ".");
                    return 40;
                }

                output.WriteLine("Opening drawing: " + DrawingSummary(drawing, null));
                if (!handler.SetActiveDrawing(drawing, true))
                {
                    error.WriteLine("SetActiveDrawing returned false.");
                    return 41;
                }

                var active = handler.GetActiveDrawing() ?? drawing;
                output.WriteLine("Opened drawing: " + DrawingSummary(active, null));
                var sheet = active.GetSheet();
                if (sheet != null)
                {
                    var stats = DrawingSheetStats(active as AssemblyDrawing ?? drawing, sheet);
                    output.WriteLine("Stats: parts=" + stats.Parts + " marks=" + stats.Marks + " dimensions=" + stats.Dimensions + " texts=" + stats.Texts + " views=" + stats.Views + ".");
                }

                if (!handler.CloseActiveDrawing(false))
                {
                    output.WriteLine("CloseActiveDrawing(false) returned false; trying close with save=true.");
                    if (!handler.CloseActiveDrawing(true))
                    {
                        error.WriteLine("CloseActiveDrawing(true) returned false.");
                        return 42;
                    }
                }

                output.WriteLine("Opened drawing closed.");
                return 0;
            }
            catch (Exception ex)
            {
                error.WriteLine("OpenAndCloseDrawingSheet failed: " + ExceptionText(ex));
                return 43;
            }
        }

        public static int ProbeNativeProcessDrawing(string modelId, string outputDirectory, TextWriter output, TextWriter error)
        {
            try
            {
                var handler = new DrawingHandler();
                if (!handler.GetConnectionStatus())
                {
                    error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                    return 10;
                }

                var sourceDrawing = DrawingsByModelId(handler, modelId)
                    .OrderBy(item => item.SheetNumber == 0 ? 0 : 1)
                    .ThenBy(item => item.SheetNumber)
                    .FirstOrDefault();
                if (sourceDrawing == null)
                {
                    error.WriteLine("No source drawing found for modelId=" + modelId + ".");
                    return 40;
                }

                output.WriteLine("Source drawing: " + DrawingSummary(sourceDrawing, null));
                if (!handler.SetActiveDrawing(sourceDrawing, true))
                {
                    error.WriteLine("Could not open source drawing for modelId=" + modelId + ".");
                    return 41;
                }

                var sourceActive = handler.GetActiveDrawing() as AssemblyDrawing ?? sourceDrawing;
                var sourceSheet = sourceActive.GetSheet();
                if (sourceSheet == null)
                {
                    error.WriteLine("Source drawing has no sheet.");
                    return 42;
                }

                var sourceStats = DrawingSheetStats(sourceActive, sourceSheet);
                var drawingPartIds = DrawingPartModelIds(sourceSheet);
                var orderedPartIds = OrderAssemblyPartIds(modelId, drawingPartIds, output);
                var visiblePartIds = orderedPartIds.Take(Math.Min(8, orderedPartIds.Count)).ToList();
                handler.CloseActiveDrawing(false);

                output.WriteLine("Source stats: parts=" + sourceStats.Parts + " marks=" + sourceStats.Marks + " dimensions=" + sourceStats.Dimensions + " texts=" + sourceStats.Texts + " views=" + sourceStats.Views + ".");
                output.WriteLine("Probe visible target unique parts: " + string.Join(",", visiblePartIds));

                outputDirectory = string.IsNullOrWhiteSpace(outputDirectory)
                    ? Path.Combine("outputs", "tekla-process-drawings-" + modelId)
                    : outputDirectory;
                Directory.CreateDirectory(outputDirectory);

                var existingSheets = ExistingSheetNumbers(handler, modelId);
                var nextSheet = NextAvailableSheetNumber(existingSheets, existingSheets.Count == 0 ? 1 : existingSheets.Max() + 1);
                var attributeName = string.IsNullOrWhiteSpace(sourceDrawing.Name) ? "standard" : sourceDrawing.Name;
                var results = new List<object>();

                results.Add(CreateProbeSheet(handler, modelId, nextSheet, attributeName, "source_attributes_no_hide", visiblePartIds, false, output));
                existingSheets.Add(nextSheet);
                nextSheet = NextAvailableSheetNumber(existingSheets, nextSheet + 1);
                results.Add(CreateProbeSheet(handler, modelId, nextSheet, attributeName, "source_attributes_hide_whole_drawing", visiblePartIds, true, output));

                var path = Path.Combine(outputDirectory, "tekla-native-process-probe-" + modelId + ".json");
                File.WriteAllText(
                    path,
                    new JavaScriptSerializer().Serialize(
                        new
                        {
                            model_id = modelId,
                            source_drawing = DrawingSummary(sourceDrawing, null),
                            source_stats = sourceStats,
                            attribute_name = attributeName,
                            visible_part_ids = visiblePartIds,
                            probes = results,
                        }
                    )
                );
                output.WriteLine("Wrote native process probe: " + Path.GetFullPath(path));
                return 0;
            }
            catch (Exception ex)
            {
                error.WriteLine("ProbeNativeProcessDrawing failed: " + ExceptionText(ex));
                return 69;
            }
        }

        public static int ProbeCloneDrawing(string modelId, string outputDirectory, TextWriter output, TextWriter error)
        {
            try
            {
                var handler = new DrawingHandler();
                if (!handler.GetConnectionStatus())
                {
                    error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                    return 10;
                }

                var before = DrawingsByModelId(handler, modelId).OrderBy(item => item.SheetNumber).ToList();
                var sourceDrawing = before.FirstOrDefault(item => item.SheetNumber == 0) ?? before.FirstOrDefault();
                if (sourceDrawing == null)
                {
                    error.WriteLine("No source drawing found for modelId=" + modelId + ".");
                    return 40;
                }

                outputDirectory = string.IsNullOrWhiteSpace(outputDirectory)
                    ? Path.Combine("outputs", "tekla-process-drawings-" + modelId)
                    : outputDirectory;
                Directory.CreateDirectory(outputDirectory);

                var beforeSummaries = before.Select(item => DrawingSummary(item, null)).ToList();
                output.WriteLine("Clone probe source: " + DrawingSummary(sourceDrawing, null));
                output.WriteLine("Drawings before clone probe: " + before.Count);
                foreach (var summary in beforeSummaries)
                {
                    output.WriteLine("  before " + summary);
                }

                var active = handler.GetActiveDrawing();
                if (active != null)
                {
                    output.WriteLine("Active drawing exists before clone probe, closing: " + DrawingSummary(active, null));
                    handler.CloseActiveDrawing(false);
                }

                if (!SelectAssemblyMainPartInModel(new Identifier(int.Parse(modelId)), output))
                {
                    error.WriteLine("Could not select assembly main part for modelId=" + modelId + ".");
                    return 80;
                }

                if (!RunMacroAndWait(@"FabricationInspectionDrawings\OpenDrawingList.cs", output))
                {
                    return 81;
                }

                // In this China environment value 7 selects the existing assembly drawing
                // attributes; value 10 maps to a different option and returns no rows.
                var assemblyFilterMacro = EnsureDrawingFilterOptionMacro(7);
                if (!RunMacroAndWait(assemblyFilterMacro, output))
                {
                    return 82;
                }

                var selected = SelectedAssemblyDrawings(handler).ToList();
                output.WriteLine("Selected drawings after UI filter: " + selected.Count);
                foreach (var drawing in selected)
                {
                    output.WriteLine("  selected " + DrawingSummary(drawing, null));
                }

                var selectedSource = selected.FirstOrDefault(item => DrawingModelIdentifier(item) == modelId && item.SheetNumber == sourceDrawing.SheetNumber);
                var resultStatus = "not_cloned";
                var cloneRan = false;
                if (selectedSource == null)
                {
                    output.WriteLine("Clone probe aborted because UI did not select source sheet=" + sourceDrawing.SheetNumber + ".");
                }
                else
                {
                    if (!RunMacroAndWait(@"FabricationInspectionDrawings\CloneDrawing.cs", output))
                    {
                        return 83;
                    }

                    cloneRan = true;
                    resultStatus = "clone_macro_ran";
                    output.WriteLine("Clone macro ran; waiting for drawing list change.");
                }

                var after = before;
                var newDrawings = new List<AssemblyDrawing>();
                if (cloneRan)
                {
                    var beforeSheets = new HashSet<int>(before.Select(item => item.SheetNumber));
                    for (var index = 0; index < 60; index++)
                    {
                        Thread.Sleep(1000);
                        after = DrawingsByModelId(handler, modelId).OrderBy(item => item.SheetNumber).ToList();
                        newDrawings = after.Where(item => !beforeSheets.Contains(item.SheetNumber)).ToList();
                        if (newDrawings.Count > 0)
                        {
                            break;
                        }
                    }
                }

                var probeStats = new List<object>();
                foreach (var drawing in newDrawings)
                {
                    var stats = TryReadDrawingStats(handler, drawing, output);
                    probeStats.Add(new { drawing = DrawingSummary(drawing, null), stats });
                }

                if (newDrawings.Count > 0)
                {
                    resultStatus = "clone_created";
                }
                else if (cloneRan)
                {
                    resultStatus = "clone_macro_ran_no_new_drawing";
                }

                var path = Path.Combine(outputDirectory, "tekla-clone-drawing-probe-" + modelId + ".json");
                File.WriteAllText(
                    path,
                    new JavaScriptSerializer().Serialize(
                        new
                        {
                            model_id = modelId,
                            status = resultStatus,
                            source_drawing = DrawingSummary(sourceDrawing, null),
                            before_drawings = beforeSummaries,
                            selected_drawings = selected.Select(item => DrawingSummary(item, null)).ToList(),
                            clone_ran = cloneRan,
                            after_drawings = after.Select(item => DrawingSummary(item, null)).ToList(),
                            new_drawings = newDrawings.Select(item => DrawingSummary(item, null)).ToList(),
                            new_drawing_stats = probeStats,
                        }
                    )
                );

                output.WriteLine("Clone probe status: " + resultStatus + ".");
                output.WriteLine("Wrote clone probe: " + Path.GetFullPath(path));
                return 0;
            }
            catch (Exception ex)
            {
                error.WriteLine("ProbeCloneDrawing failed: " + ExceptionText(ex));
                return 89;
            }
        }

        public static int ProbeDrawingFilterOptions(string modelId, string outputDirectory, TextWriter output, TextWriter error)
        {
            try
            {
                var handler = new DrawingHandler();
                if (!handler.GetConnectionStatus())
                {
                    error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                    return 10;
                }

                var drawings = DrawingsByModelId(handler, modelId).OrderBy(item => item.SheetNumber).ToList();
                if (drawings.Count == 0)
                {
                    error.WriteLine("No drawings found for modelId=" + modelId + ".");
                    return 40;
                }

                outputDirectory = string.IsNullOrWhiteSpace(outputDirectory)
                    ? Path.Combine("outputs", "tekla-process-drawings-" + modelId)
                    : outputDirectory;
                Directory.CreateDirectory(outputDirectory);

                if (!SelectAssemblyMainPartInModel(new Identifier(int.Parse(modelId)), output))
                {
                    error.WriteLine("Could not select assembly main part for modelId=" + modelId + ".");
                    return 80;
                }

                if (!RunMacroAndWait(@"FabricationInspectionDrawings\OpenDrawingList.cs", output))
                {
                    return 81;
                }

                var rows = new List<object>();
                // Values above 15 can switch Tekla into the startup/settings UI in this
                // TS2017 China environment, which temporarily disconnects DrawingHandler.
                for (var option = 0; option <= 15; option++)
                {
                    var macroName = EnsureDrawingFilterOptionMacro(option);
                    if (!RunMacroAndWait(macroName, output))
                    {
                        rows.Add(new { option, macro = macroName, macro_ok = false });
                        continue;
                    }

                    Thread.Sleep(500);
                    var selected = SelectedAssemblyDrawings(handler).ToList();
                    var summaries = selected.Select(item => DrawingSummary(item, null)).ToList();
                    output.WriteLine("filterOption=" + option + " selected=" + selected.Count);
                    foreach (var summary in summaries)
                    {
                        output.WriteLine("  option " + option + " selected " + summary);
                    }

                    rows.Add(new { option, macro = macroName, macro_ok = true, selected = summaries });
                }

                var path = Path.Combine(outputDirectory, "tekla-drawing-filter-options-" + modelId + ".json");
                File.WriteAllText(
                    path,
                    new JavaScriptSerializer().Serialize(
                        new
                        {
                            model_id = modelId,
                            known_drawings = drawings.Select(item => DrawingSummary(item, null)).ToList(),
                            filter_options = rows,
                        }
                    )
                );
                output.WriteLine("Wrote drawing filter option probe: " + Path.GetFullPath(path));
                return 0;
            }
            catch (Exception ex)
            {
                error.WriteLine("ProbeDrawingFilterOptions failed: " + ExceptionText(ex));
                return 91;
            }
        }

        public static int ProbeCopyAnnotations(string modelId, int sourceSheetNumber, int targetSheetNumber, string outputDirectory, TextWriter output, TextWriter error)
        {
            if (sourceSheetNumber < 0 || targetSheetNumber < 0)
            {
                error.WriteLine("--source-sheet and --target-sheet must be >= 0.");
                return 2;
            }

            try
            {
                var handler = new DrawingHandler();
                if (!handler.GetConnectionStatus())
                {
                    error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                    return 10;
                }

                var drawings = DrawingsByModelId(handler, modelId).OrderBy(item => item.SheetNumber).ToList();
                var sourceDrawing = drawings.FirstOrDefault(item => item.SheetNumber == sourceSheetNumber);
                var targetDrawing = drawings.FirstOrDefault(item => item.SheetNumber == targetSheetNumber);
                if (sourceDrawing == null)
                {
                    error.WriteLine("No source drawing found for modelId=" + modelId + " sheet=" + sourceSheetNumber + ".");
                    return 40;
                }

                if (targetDrawing == null)
                {
                    error.WriteLine("No target drawing found for modelId=" + modelId + " sheet=" + targetSheetNumber + ".");
                    return 41;
                }

                output.WriteLine("Copy annotation source: " + DrawingSummary(sourceDrawing, null));
                output.WriteLine("Copy annotation target: " + DrawingSummary(targetDrawing, null));

                if (!handler.SetActiveDrawing(sourceDrawing, true))
                {
                    error.WriteLine("Could not open source drawing.");
                    return 42;
                }

                var sourceActive = handler.GetActiveDrawing() as AssemblyDrawing ?? sourceDrawing;
                var sourceSheet = sourceActive.GetSheet();
                if (sourceSheet == null)
                {
                    error.WriteLine("Source drawing has no sheet.");
                    return 43;
                }

                var sourceStats = DrawingSheetStats(sourceActive, sourceSheet);
                var sourceViews = DrawingViews(sourceSheet);
                var texts = CaptureTexts(sourceSheet, sourceViews);
                var dimensionSets = CaptureStraightDimensionSets(sourceSheet, sourceViews);
                output.WriteLine("Captured annotations from source: texts=" + texts.Count + " straightDimensionSets=" + dimensionSets.Count + " sourceDimensions=" + sourceStats.Dimensions + ".");

                handler.CloseActiveDrawing(false);

                if (!handler.SetActiveDrawing(targetDrawing, true))
                {
                    error.WriteLine("Could not open target drawing.");
                    return 44;
                }

                var targetActive = handler.GetActiveDrawing() as AssemblyDrawing ?? targetDrawing;
                var targetSheet = targetActive.GetSheet();
                if (targetSheet == null)
                {
                    error.WriteLine("Target drawing has no sheet.");
                    return 45;
                }

                var before = DrawingSheetStats(targetActive, targetSheet);
                var targetViews = DrawingViews(targetSheet);
                var insertedTexts = 0;
                var failedTexts = 0;
                foreach (var item in texts)
                {
                    var targetView = ResolveTargetView(targetSheet, targetViews, item.ViewIndex);
                    try
                    {
                        var copied = new Text(targetView, CopyPoint(item.InsertionPoint), item.TextString, item.Attributes);
                        if (copied.Insert())
                        {
                            insertedTexts += 1;
                        }
                        else
                        {
                            failedTexts += 1;
                        }
                    }
                    catch (Exception ex)
                    {
                        failedTexts += 1;
                        output.WriteLine("Text insert failed: " + ExceptionText(ex));
                    }
                }

                var insertedDimensionSets = 0;
                var failedDimensionSets = 0;
                foreach (var item in dimensionSets)
                {
                    var targetView = ResolveTargetView(targetSheet, targetViews, item.ViewIndex);
                    try
                    {
                        var copied = new StraightDimensionSetHandler().CreateDimensionSet(
                            targetView,
                            CopyPointList(item.DimensionPoints),
                            CopyVector(item.UpDirection),
                            item.Distance,
                            item.LeftTagLineOffset,
                            item.RightTagLineOffset,
                            item.Attributes);
                        if (copied != null)
                        {
                            insertedDimensionSets += 1;
                        }
                        else
                        {
                            failedDimensionSets += 1;
                        }
                    }
                    catch (Exception ex)
                    {
                        failedDimensionSets += 1;
                        output.WriteLine("StraightDimensionSet insert failed: " + ExceptionText(ex));
                    }
                }

                targetActive.CommitChanges();
                handler.SaveActiveDrawing();
                var after = DrawingSheetStats(targetActive, targetActive.GetSheet());
                handler.CloseActiveDrawing(true);

                outputDirectory = string.IsNullOrWhiteSpace(outputDirectory)
                    ? Path.Combine("outputs", "tekla-process-drawings-" + modelId)
                    : outputDirectory;
                Directory.CreateDirectory(outputDirectory);
                var path = Path.Combine(outputDirectory, "tekla-copy-annotations-probe-" + modelId + "-s" + sourceSheetNumber + "-to-s" + targetSheetNumber + ".json");
                File.WriteAllText(
                    path,
                    new JavaScriptSerializer().Serialize(
                        new
                        {
                            model_id = modelId,
                            source_sheet = sourceSheetNumber,
                            target_sheet = targetSheetNumber,
                            source = sourceStats,
                            before,
                            inserted_texts = insertedTexts,
                            failed_texts = failedTexts,
                            inserted_straight_dimension_sets = insertedDimensionSets,
                            failed_straight_dimension_sets = failedDimensionSets,
                            after,
                        }
                    )
                );

                output.WriteLine(
                    "Copied annotations to target sheet="
                    + targetSheetNumber
                    + " texts "
                    + insertedTexts
                    + "/"
                    + texts.Count
                    + " dimensionSets "
                    + insertedDimensionSets
                    + "/"
                    + dimensionSets.Count
                    + ".");
                output.WriteLine(
                    "Target stats before(dim="
                    + before.Dimensions
                    + ", texts="
                    + before.Texts
                    + ") after(dim="
                    + after.Dimensions
                    + ", texts="
                    + after.Texts
                    + ", views="
                    + after.Views
                    + ").");
                output.WriteLine("Wrote copy annotations probe: " + Path.GetFullPath(path));
                return 0;
            }
            catch (Exception ex)
            {
                error.WriteLine("ProbeCopyAnnotations failed: " + ExceptionText(ex));
                return 92;
            }
        }

        public static int ProbePruneParts(string modelId, int sourceSheetNumber, int targetSheetNumber, int stepNumber, string outputDirectory, TextWriter output, TextWriter error)
        {
            if (sourceSheetNumber < 0 || targetSheetNumber < 0 || stepNumber <= 0)
            {
                error.WriteLine("--source-sheet and --target-sheet must be >= 0; --step must be > 0.");
                return 2;
            }

            try
            {
                var handler = new DrawingHandler();
                if (!handler.GetConnectionStatus())
                {
                    error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                    return 10;
                }

                var drawings = DrawingsByModelId(handler, modelId).OrderBy(item => item.SheetNumber).ToList();
                var sourceDrawing = drawings.FirstOrDefault(item => item.SheetNumber == sourceSheetNumber);
                var targetDrawing = drawings.FirstOrDefault(item => item.SheetNumber == targetSheetNumber);
                if (sourceDrawing == null)
                {
                    error.WriteLine("No source drawing found for modelId=" + modelId + " sheet=" + sourceSheetNumber + ".");
                    return 40;
                }

                if (targetDrawing == null)
                {
                    error.WriteLine("No target drawing found for modelId=" + modelId + " sheet=" + targetSheetNumber + ".");
                    return 41;
                }

                output.WriteLine("Prune source: " + DrawingSummary(sourceDrawing, null));
                output.WriteLine("Prune target: " + DrawingSummary(targetDrawing, null));

                if (!handler.SetActiveDrawing(sourceDrawing, true))
                {
                    error.WriteLine("Could not open source drawing.");
                    return 42;
                }

                var sourceActive = handler.GetActiveDrawing() as AssemblyDrawing ?? sourceDrawing;
                var sourceSheet = sourceActive.GetSheet();
                if (sourceSheet == null)
                {
                    error.WriteLine("Source drawing has no sheet.");
                    return 43;
                }

                var drawingPartIds = DrawingPartModelIds(sourceSheet);
                output.WriteLine("Source unique drawing part ids: " + drawingPartIds.Count);
                handler.CloseActiveDrawing(false);

                var orderedPartIds = OrderAssemblyPartIds(modelId, drawingPartIds, output);
                var steps = BuildSimpleProcessSteps(orderedPartIds, 5);
                var step = steps.FirstOrDefault(item => item.StepNo == stepNumber);
                if (step == null)
                {
                    error.WriteLine("No simple process step " + stepNumber + ".");
                    return 44;
                }

                if (!handler.SetActiveDrawing(targetDrawing, true))
                {
                    error.WriteLine("Could not open target drawing.");
                    return 45;
                }

                var targetActive = handler.GetActiveDrawing() as AssemblyDrawing ?? targetDrawing;
                var targetSheet = targetActive.GetSheet();
                if (targetSheet == null)
                {
                    error.WriteLine("Target drawing has no sheet.");
                    return 46;
                }

                var before = DrawingSheetStats(targetActive, targetSheet);
                int kept;
                int deleted;
                int failed;
                DeleteExtraDrawingParts(targetSheet, step.VisiblePartIds, out kept, out deleted, out failed);
                targetActive.CommitChanges();
                handler.SaveActiveDrawing();
                var after = DrawingSheetStats(targetActive, targetActive.GetSheet());
                handler.CloseActiveDrawing(true);

                outputDirectory = string.IsNullOrWhiteSpace(outputDirectory)
                    ? Path.Combine("outputs", "tekla-process-drawings-" + modelId)
                    : outputDirectory;
                Directory.CreateDirectory(outputDirectory);
                var path = Path.Combine(outputDirectory, "tekla-prune-parts-probe-" + modelId + "-s" + targetSheetNumber + "-step" + stepNumber + ".json");
                File.WriteAllText(
                    path,
                    new JavaScriptSerializer().Serialize(
                        new
                        {
                            model_id = modelId,
                            source_sheet = sourceSheetNumber,
                            target_sheet = targetSheetNumber,
                            step = new { step.StepNo, visible_part_ids = step.VisiblePartIds },
                            before,
                            kept,
                            deleted,
                            failed,
                            after,
                        }
                    )
                );

                output.WriteLine(
                    "Pruned target sheet="
                    + targetSheetNumber
                    + " step="
                    + stepNumber
                    + " kept="
                    + kept
                    + " deleted="
                    + deleted
                    + " failed="
                    + failed
                    + ".");
                output.WriteLine(
                    "Target stats before(parts="
                    + before.Parts
                    + ", unique="
                    + before.UniquePartIds
                    + ", marks="
                    + before.Marks
                    + ", dim="
                    + before.Dimensions
                    + ") after(parts="
                    + after.Parts
                    + ", unique="
                    + after.UniquePartIds
                    + ", marks="
                    + after.Marks
                    + ", dim="
                    + after.Dimensions
                    + ").");
                output.WriteLine("Wrote prune parts probe: " + Path.GetFullPath(path));
                return 0;
            }
            catch (Exception ex)
            {
                error.WriteLine("ProbePruneParts failed: " + ExceptionText(ex));
                return 93;
            }
        }

        public static int ProbeRestrictViewParts(string modelId, int sourceSheetNumber, int targetSheetNumber, int stepNumber, string outputDirectory, TextWriter output, TextWriter error)
        {
            if (sourceSheetNumber < 0 || targetSheetNumber < 0 || stepNumber <= 0)
            {
                error.WriteLine("--source-sheet and --target-sheet must be >= 0; --step must be > 0.");
                return 2;
            }

            try
            {
                var handler = new DrawingHandler();
                if (!handler.GetConnectionStatus())
                {
                    error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                    return 10;
                }

                var drawings = DrawingsByModelId(handler, modelId).OrderBy(item => item.SheetNumber).ToList();
                var sourceDrawing = drawings.FirstOrDefault(item => item.SheetNumber == sourceSheetNumber);
                var targetDrawing = drawings.FirstOrDefault(item => item.SheetNumber == targetSheetNumber);
                if (sourceDrawing == null || targetDrawing == null)
                {
                    error.WriteLine("Missing source or target drawing for modelId=" + modelId + ".");
                    return 40;
                }

                output.WriteLine("Restrict source: " + DrawingSummary(sourceDrawing, null));
                output.WriteLine("Restrict target: " + DrawingSummary(targetDrawing, null));
                if (!handler.SetActiveDrawing(sourceDrawing, true))
                {
                    error.WriteLine("Could not open source drawing.");
                    return 41;
                }

                var sourceActive = handler.GetActiveDrawing() as AssemblyDrawing ?? sourceDrawing;
                var sourceSheet = sourceActive.GetSheet();
                if (sourceSheet == null)
                {
                    error.WriteLine("Source drawing has no sheet.");
                    return 42;
                }

                var drawingPartIds = DrawingPartModelIds(sourceSheet);
                handler.CloseActiveDrawing(false);
                var orderedPartIds = OrderAssemblyPartIds(modelId, drawingPartIds, output);
                var steps = BuildSimpleProcessSteps(orderedPartIds, 5);
                var step = steps.FirstOrDefault(item => item.StepNo == stepNumber);
                if (step == null)
                {
                    error.WriteLine("No simple process step " + stepNumber + ".");
                    return 43;
                }

                if (!handler.SetActiveDrawing(targetDrawing, true))
                {
                    error.WriteLine("Could not open target drawing.");
                    return 44;
                }

                var targetActive = handler.GetActiveDrawing() as AssemblyDrawing ?? targetDrawing;
                var targetSheet = targetActive.GetSheet();
                if (targetSheet == null)
                {
                    error.WriteLine("Target drawing has no sheet.");
                    return 45;
                }

                var before = DrawingSheetStats(targetActive, targetSheet);
                var changedViews = 0;
                var failedViews = 0;
                foreach (var viewBase in DrawingViews(targetSheet))
                {
                    var view = viewBase as View;
                    if (view == null)
                    {
                        continue;
                    }

                    try
                    {
                        SetReflectionValue(view, "Parts", ToIntList(step.VisiblePartIds));
                        if (view.Modify())
                        {
                            changedViews += 1;
                        }
                        else
                        {
                            failedViews += 1;
                        }
                    }
                    catch (Exception ex)
                    {
                        failedViews += 1;
                        output.WriteLine("View.Parts modify failed: " + ExceptionText(ex));
                    }
                }

                targetActive.CommitChanges();
                handler.SaveActiveDrawing();
                var immediate = DrawingSheetStats(targetActive, targetActive.GetSheet());
                handler.CloseActiveDrawing(true);

                var reopenedDrawing = DrawingsByModelId(handler, modelId).FirstOrDefault(item => item.SheetNumber == targetSheetNumber);
                SheetStats reopened = null;
                if (reopenedDrawing != null && handler.SetActiveDrawing(reopenedDrawing, true))
                {
                    var reopenedActive = handler.GetActiveDrawing() as AssemblyDrawing ?? reopenedDrawing;
                    reopened = DrawingSheetStats(reopenedActive, reopenedActive.GetSheet());
                    handler.CloseActiveDrawing(false);
                }

                outputDirectory = string.IsNullOrWhiteSpace(outputDirectory)
                    ? Path.Combine("outputs", "tekla-process-drawings-" + modelId)
                    : outputDirectory;
                Directory.CreateDirectory(outputDirectory);
                var path = Path.Combine(outputDirectory, "tekla-restrict-view-parts-probe-" + modelId + "-s" + targetSheetNumber + "-step" + stepNumber + ".json");
                File.WriteAllText(
                    path,
                    new JavaScriptSerializer().Serialize(
                        new
                        {
                            model_id = modelId,
                            source_sheet = sourceSheetNumber,
                            target_sheet = targetSheetNumber,
                            step = new { step.StepNo, visible_part_ids = step.VisiblePartIds },
                            before,
                            changed_views = changedViews,
                            failed_views = failedViews,
                            immediate,
                            reopened,
                        }
                    )
                );

                output.WriteLine(
                    "Restricted target sheet="
                    + targetSheetNumber
                    + " step="
                    + stepNumber
                    + " changedViews="
                    + changedViews
                    + " failedViews="
                    + failedViews
                    + ".");
                output.WriteLine(
                    "Stats before(parts="
                    + before.Parts
                    + ", unique="
                    + before.UniquePartIds
                    + ", marks="
                    + before.Marks
                    + ", dim="
                    + before.Dimensions
                    + ") immediate(parts="
                    + immediate.Parts
                    + ", unique="
                    + immediate.UniquePartIds
                    + ", marks="
                    + immediate.Marks
                    + ", dim="
                    + immediate.Dimensions
                    + ") reopened(parts="
                    + (reopened == null ? -1 : reopened.Parts)
                    + ", unique="
                    + (reopened == null ? -1 : reopened.UniquePartIds)
                    + ", marks="
                    + (reopened == null ? -1 : reopened.Marks)
                    + ", dim="
                    + (reopened == null ? -1 : reopened.Dimensions)
                    + ").");
                output.WriteLine("Wrote restrict view parts probe: " + Path.GetFullPath(path));
                return 0;
            }
            catch (Exception ex)
            {
                error.WriteLine("ProbeRestrictViewParts failed: " + ExceptionText(ex));
                return 94;
            }
        }

        public static int ProbePartRelatedObjects(string modelId, int sourceSheetNumber, string outputDirectory, TextWriter output, TextWriter error)
        {
            if (sourceSheetNumber < 0)
            {
                error.WriteLine("--source-sheet must be >= 0.");
                return 2;
            }

            try
            {
                var handler = new DrawingHandler();
                if (!handler.GetConnectionStatus())
                {
                    error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                    return 10;
                }

                var sourceDrawing = DrawingsByModelId(handler, modelId).FirstOrDefault(item => item.SheetNumber == sourceSheetNumber);
                if (sourceDrawing == null)
                {
                    error.WriteLine("No source drawing found for modelId=" + modelId + " sheet=" + sourceSheetNumber + ".");
                    return 40;
                }

                output.WriteLine("Related object source: " + DrawingSummary(sourceDrawing, null));
                if (!handler.SetActiveDrawing(sourceDrawing, true))
                {
                    error.WriteLine("Could not open source drawing.");
                    return 41;
                }

                var sourceActive = handler.GetActiveDrawing() as AssemblyDrawing ?? sourceDrawing;
                var sourceSheet = sourceActive.GetSheet();
                if (sourceSheet == null)
                {
                    error.WriteLine("Source drawing has no sheet.");
                    return 42;
                }

                var rows = new List<object>();
                var aggregate = new Dictionary<string, int>();
                var objects = sourceSheet.GetAllObjects(new[] { typeof(Part) });
                var partIndex = 0;
                while (objects.MoveNext())
                {
                    var part = objects.Current as Part;
                    if (part == null)
                    {
                        continue;
                    }

                    partIndex += 1;
                    var relatedCounts = new Dictionary<string, int>();
                    try
                    {
                        var related = part.GetRelatedObjects();
                        while (related.MoveNext())
                        {
                            if (related.Current == null)
                            {
                                continue;
                            }

                            var name = related.Current.GetType().FullName;
                            Increment(relatedCounts, name);
                            Increment(aggregate, name);
                        }
                    }
                    catch (Exception ex)
                    {
                        Increment(relatedCounts, "ERROR:" + ExceptionText(ex));
                    }

                    if (partIndex <= 12)
                    {
                        rows.Add(
                            new
                            {
                                index = partIndex,
                                model_id = part.ModelIdentifier == null ? "" : part.ModelIdentifier.ID.ToString(),
                                related = relatedCounts.OrderBy(item => item.Key).Select(item => new { type = item.Key, count = item.Value }).ToList(),
                            });
                    }
                }

                handler.CloseActiveDrawing(false);

                outputDirectory = string.IsNullOrWhiteSpace(outputDirectory)
                    ? Path.Combine("outputs", "tekla-process-drawings-" + modelId)
                    : outputDirectory;
                Directory.CreateDirectory(outputDirectory);
                var path = Path.Combine(outputDirectory, "tekla-part-related-objects-" + modelId + "-s" + sourceSheetNumber + ".json");
                File.WriteAllText(
                    path,
                    new JavaScriptSerializer().Serialize(
                        new
                        {
                            model_id = modelId,
                            source_sheet = sourceSheetNumber,
                            part_count = partIndex,
                            aggregate = aggregate.OrderBy(item => item.Key).Select(item => new { type = item.Key, count = item.Value }).ToList(),
                            sample_parts = rows,
                        }));

                output.WriteLine("Related object probe parts=" + partIndex + ".");
                foreach (var item in aggregate.OrderByDescending(item => item.Value).Take(20))
                {
                    output.WriteLine("  " + item.Key + "=" + item.Value);
                }
                output.WriteLine("Wrote related object probe: " + Path.GetFullPath(path));
                return 0;
            }
            catch (Exception ex)
            {
                error.WriteLine("ProbePartRelatedObjects failed: " + ExceptionText(ex));
                return 95;
            }
        }

        public static int ProbeGaStageDrawing(string modelId, int sourceSheetNumber, int stepNumber, string outputDirectory, TextWriter output, TextWriter error)
        {
            if (sourceSheetNumber < 0 || stepNumber <= 0)
            {
                error.WriteLine("--source-sheet must be >= 0; --step must be > 0.");
                return 2;
            }

            try
            {
                var handler = new DrawingHandler();
                if (!handler.GetConnectionStatus())
                {
                    error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                    return 10;
                }

                var sourceDrawing = DrawingsByModelId(handler, modelId).FirstOrDefault(item => item.SheetNumber == sourceSheetNumber);
                if (sourceDrawing == null)
                {
                    error.WriteLine("No source drawing found for modelId=" + modelId + " sheet=" + sourceSheetNumber + ".");
                    return 40;
                }

                if (!handler.SetActiveDrawing(sourceDrawing, true))
                {
                    error.WriteLine("Could not open source drawing.");
                    return 41;
                }

                var sourceActive = handler.GetActiveDrawing() as AssemblyDrawing ?? sourceDrawing;
                var sourceSheet = sourceActive.GetSheet();
                var drawingPartIds = DrawingPartModelIds(sourceSheet);
                var orderedPartIds = OrderAssemblyPartIds(modelId, drawingPartIds, output);
                var steps = BuildSimpleProcessSteps(orderedPartIds, 5);
                var step = steps.FirstOrDefault(item => item.StepNo == stepNumber);
                handler.CloseActiveDrawing(false);
                if (step == null)
                {
                    error.WriteLine("No simple process step " + stepNumber + ".");
                    return 42;
                }

                var ga = new GADrawing("standard");
                ga.Name = "PROCESS-GA-10-3GZ-6-S" + stepNumber;
                ga.Title1 = "10-3GZ-6 PROCESS STEP " + stepNumber;
                ga.Title2 = "Codex GA primitive geometry probe";
                output.WriteLine("Creating GA process drawing for step " + stepNumber + ".");
                if (!ga.Insert())
                {
                    error.WriteLine("GADrawing.Insert returned false.");
                    return 43;
                }

                if (!handler.SetActiveDrawing(ga, true))
                {
                    error.WriteLine("Could not open inserted GA drawing.");
                    return 44;
                }

                var active = handler.GetActiveDrawing() as GADrawing ?? ga;
                var sheet = active.GetSheet();
                var drawResult = DrawModelAabbStageGeometry(sheet, modelId, step.VisiblePartIds, output);
                var text = new Text(sheet, new Tekla.Structures.Geometry3d.Point(30, 30, 0), "PROCESS STEP " + stepNumber + " / visible parts " + step.VisiblePartIds.Count);
                var textInserted = text.Insert();
                var dimensionInserted = InsertProbeOverallDimension(sheet, drawResult);
                active.CommitChanges();
                handler.SaveActiveDrawing();
                var immediate = CountPrimitiveSheetStats(active, sheet);
                handler.CloseActiveDrawing(true);

                var reopenedStats = TryReadPrimitiveDrawingStats(handler, ga, output);

                outputDirectory = string.IsNullOrWhiteSpace(outputDirectory)
                    ? Path.Combine("outputs", "tekla-process-drawings-" + modelId)
                    : outputDirectory;
                Directory.CreateDirectory(outputDirectory);
                var path = Path.Combine(outputDirectory, "tekla-ga-stage-probe-" + modelId + "-step" + stepNumber + ".json");
                File.WriteAllText(
                    path,
                    new JavaScriptSerializer().Serialize(
                        new
                        {
                            model_id = modelId,
                            step = new { step.StepNo, visible_part_ids = step.VisiblePartIds },
                            ga_mark = SafeText(ga.Mark),
                            ga_name = SafeText(ga.Name),
                            rectangles = drawResult.Rectangles,
                            lines_inserted = drawResult.LinesInserted,
                            lines_failed = drawResult.LinesFailed,
                            text_inserted = textInserted,
                            dimension_inserted = dimensionInserted,
                            immediate,
                            reopened = reopenedStats,
                        }));

                output.WriteLine(
                    "GA stage probe inserted rectangles="
                    + drawResult.Rectangles
                    + " lines="
                    + drawResult.LinesInserted
                    + " failed="
                    + drawResult.LinesFailed
                    + " text="
                    + textInserted
                    + " dimension="
                    + dimensionInserted
                    + ".");
                output.WriteLine("Immediate primitive stats: " + PrimitiveStatsText(immediate));
                output.WriteLine("Reopened primitive stats: " + PrimitiveStatsText(reopenedStats));
                output.WriteLine("Wrote GA stage probe: " + Path.GetFullPath(path));
                return 0;
            }
            catch (Exception ex)
            {
                error.WriteLine("ProbeGaStageDrawing failed: " + ExceptionText(ex));
                return 96;
            }
        }

        public static int ProbeGaFixtureProjectionDrawing(string modelId, int sourceSheetNumber, int stepNumber, string outputDirectory, TextWriter output, TextWriter error)
        {
            if (sourceSheetNumber < 0 || stepNumber <= 0)
            {
                error.WriteLine("--source-sheet must be >= 0; --step must be > 0.");
                return 2;
            }

            try
            {
                var handler = new DrawingHandler();
                if (!handler.GetConnectionStatus())
                {
                    error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                    return 10;
                }

                var sourceDrawing = DrawingsByModelId(handler, modelId).FirstOrDefault(item => item.SheetNumber == sourceSheetNumber);
                if (sourceDrawing == null)
                {
                    error.WriteLine("No source drawing found for modelId=" + modelId + " sheet=" + sourceSheetNumber + ".");
                    return 40;
                }

                if (!handler.SetActiveDrawing(sourceDrawing, true))
                {
                    error.WriteLine("Could not open source drawing.");
                    return 41;
                }

                var sourceActive = handler.GetActiveDrawing() as AssemblyDrawing ?? sourceDrawing;
                var sourceSheet = sourceActive.GetSheet();
                var drawingPartIds = DrawingPartModelIds(sourceSheet);
                var orderedPartIds = OrderAssemblyPartIds(modelId, drawingPartIds, output);
                var steps = BuildSimpleProcessSteps(orderedPartIds, 5);
                var step = steps.FirstOrDefault(item => item.StepNo == stepNumber);
                handler.CloseActiveDrawing(false);
                if (step == null)
                {
                    error.WriteLine("No simple process step " + stepNumber + ".");
                    return 42;
                }

                var ga = new GADrawing("standard");
                ga.Name = "PROCESS-FIXTURE-10-3GZ-6-S" + stepNumber;
                ga.Title1 = "10-3GZ-6 FIXTURE TRUE PROJECTION S" + stepNumber;
                ga.Title2 = "Codex solid-edge fixture projection probe";
                output.WriteLine("Creating fixture true projection GA drawing for step " + stepNumber + ".");
                if (!ga.Insert())
                {
                    error.WriteLine("GADrawing.Insert returned false.");
                    return 43;
                }

                if (!handler.SetActiveDrawing(ga, true))
                {
                    error.WriteLine("Could not open inserted GA drawing.");
                    return 44;
                }

                var active = handler.GetActiveDrawing() as GADrawing ?? ga;
                var sheet = active.GetSheet();
                FixtureFrame frame;
                List<object> evidence;
                var drawResult = DrawFixtureProjectionStageGeometry(sheet, modelId, step.VisiblePartIds, output, out frame, out evidence);
                var textInserted = 0;
                textInserted += InsertText(sheet, 30, 42, "FIXTURE TRUE PROJECTION");
                textInserted += InsertText(sheet, 30, 34, "STEP " + stepNumber + " / visible parts " + step.VisiblePartIds.Count);
                textInserted += InsertText(sheet, 30, 26, "SOURCE Tekla Part.GetSolid().GetEdgeEnumerator()");
                textInserted += InsertText(sheet, 30, 18, "FIXTURE FACE " + (frame == null ? "<none>" : frame.FixtureFace));
                var dimensionInserted = InsertProbeOverallDimension(sheet, drawResult);
                active.CommitChanges();
                handler.SaveActiveDrawing();
                var immediate = CountPrimitiveSheetStats(active, sheet);
                handler.CloseActiveDrawing(true);

                var reopenedStats = TryReadPrimitiveDrawingStats(handler, ga, output);

                outputDirectory = string.IsNullOrWhiteSpace(outputDirectory)
                    ? Path.Combine("outputs", "tekla-process-drawings-" + modelId)
                    : outputDirectory;
                Directory.CreateDirectory(outputDirectory);
                var path = Path.Combine(outputDirectory, "tekla-ga-fixture-projection-" + modelId + "-step" + stepNumber + ".json");
                File.WriteAllText(
                    path,
                    new JavaScriptSerializer().Serialize(
                        new
                        {
                            model_id = modelId,
                            source_sheet = sourceSheetNumber,
                            step = new { step.StepNo, visible_part_ids = step.VisiblePartIds },
                            ga_mark = SafeText(ga.Mark),
                            ga_name = SafeText(ga.Name),
                            fixture_frame = frame,
                            lines_inserted = drawResult.LinesInserted,
                            lines_failed = drawResult.LinesFailed,
                            text_inserted = textInserted,
                            dimension_inserted = dimensionInserted,
                            evidence,
                            immediate,
                            reopened = reopenedStats,
                        }));

                output.WriteLine(
                    "GA fixture projection inserted lines="
                    + drawResult.LinesInserted
                    + " failed="
                    + drawResult.LinesFailed
                    + " texts="
                    + textInserted
                    + " dimension="
                    + dimensionInserted
                    + ".");
                output.WriteLine("Immediate primitive stats: " + PrimitiveStatsText(immediate));
                output.WriteLine("Reopened primitive stats: " + PrimitiveStatsText(reopenedStats));
                output.WriteLine("Wrote GA fixture projection probe: " + Path.GetFullPath(path));
                return 0;
            }
            catch (Exception ex)
            {
                error.WriteLine("ProbeGaFixtureProjectionDrawing failed: " + ExceptionText(ex));
                return 97;
            }
        }
        public static int ProbeGaFixtureUStageDrawing(string modelId, int sourceSheetNumber, string outputDirectory, TextWriter output, TextWriter error)
        {
            if (sourceSheetNumber < 0)
            {
                error.WriteLine("--source-sheet must be >= 0.");
                return 2;
            }

            try
            {
                var handler = new DrawingHandler();
                if (!handler.GetConnectionStatus())
                {
                    error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                    return 10;
                }

                var sourceDrawing = DrawingsByModelId(handler, modelId).FirstOrDefault(item => item.SheetNumber == sourceSheetNumber);
                if (sourceDrawing == null)
                {
                    error.WriteLine("No source drawing found for modelId=" + modelId + " sheet=" + sourceSheetNumber + ".");
                    return 40;
                }

                if (!handler.SetActiveDrawing(sourceDrawing, true))
                {
                    error.WriteLine("Could not open source drawing.");
                    return 41;
                }

                var sourceActive = handler.GetActiveDrawing() as AssemblyDrawing ?? sourceDrawing;
                var sourceSheet = sourceActive.GetSheet();
                var drawingPartIds = DrawingPartModelIds(sourceSheet);
                var orderedPartIds = OrderAssemblyPartIds(modelId, drawingPartIds, output);
                handler.CloseActiveDrawing(false);

                FixtureFrame selectionFrame;
                List<object> selectionEvidence;
                var stagePartIds = SelectFixtureUStagePartIds(orderedPartIds, output, out selectionFrame, out selectionEvidence);
                if (stagePartIds.Count == 0)
                {
                    outputDirectory = string.IsNullOrWhiteSpace(outputDirectory)
                        ? Path.Combine("outputs", "tekla-process-drawings-" + modelId)
                        : outputDirectory;
                    Directory.CreateDirectory(outputDirectory);
                    var selectionFailurePath = Path.Combine(outputDirectory, "tekla-ga-fixture-u-stage-" + modelId + "-step1-selection-failed.json");
                    File.WriteAllText(
                        selectionFailurePath,
                        new JavaScriptSerializer().Serialize(
                            new
                            {
                                model_id = modelId,
                                source_sheet = sourceSheetNumber,
                                stage = "BASE_PLUS_TWO_SIDE_WALLS",
                                ordered_part_ids = orderedPartIds,
                                selection_frame = selectionFrame,
                                selection_evidence = selectionEvidence,
                            }));
                    error.WriteLine("Wrote U-stage selection failure evidence: " + Path.GetFullPath(selectionFailurePath));
                    error.WriteLine("No parts selected for fixture U stage.");
                    return 42;
                }

                var ga = new GADrawing("standard");
                ga.Name = "PROCESS-FIXTURE-U-10-3GZ-6-S1-CLEAN";
                ga.Title1 = "10-3GZ-6 STAGE 1 BASE + SIDE WALLS";
                ga.Title2 = "Codex fixture U-stage solid-edge projection";
                output.WriteLine("Creating fixture U-stage GA drawing; selected parts=" + stagePartIds.Count + ".");
                if (!ga.Insert())
                {
                    error.WriteLine("GADrawing.Insert returned false.");
                    return 43;
                }

                if (!handler.SetActiveDrawing(ga, true))
                {
                    error.WriteLine("Could not open inserted GA drawing.");
                    return 44;
                }

                var active = handler.GetActiveDrawing() as GADrawing ?? ga;
                var sheet = active.GetSheet();
                FixtureFrame drawFrame;
                List<object> drawEvidence;
                var drawResult = DrawFixtureUStageProjectionGeometry(sheet, modelId, stagePartIds, output, out drawFrame, out drawEvidence);
                var sourcePartLabel = UStageSourcePartLabel(drawEvidence);
                var annotationLayout = BuildFixtureUStageAnnotationLayout(drawResult, drawFrame, sourcePartLabel);
                var textInserted = RenderAnnotationLayout(sheet, annotationLayout, drawResult);
                var primitiveDimensionLinesInserted = annotationLayout.Lines.Any(line => line.Kind == "DIMENSION");
                active.CommitChanges();
                handler.SaveActiveDrawing();
                var immediate = CountPrimitiveSheetStats(active, sheet);
                handler.CloseActiveDrawing(true);

                var reopenedStats = TryReadPrimitiveDrawingStats(handler, ga, output);

                outputDirectory = string.IsNullOrWhiteSpace(outputDirectory)
                    ? Path.Combine("outputs", "tekla-process-drawings-" + modelId)
                    : outputDirectory;
                Directory.CreateDirectory(outputDirectory);
                var path = Path.Combine(outputDirectory, "tekla-ga-fixture-u-stage-" + modelId + "-step1.json");
                File.WriteAllText(
                    path,
                    new JavaScriptSerializer().Serialize(
                        new
                        {
                            model_id = modelId,
                            source_sheet = sourceSheetNumber,
                            stage = "BASE_PLUS_TWO_SIDE_WALLS",
                            selected_part_ids = stagePartIds,
                            selection_frame = selectionFrame,
                            selection_evidence = selectionEvidence,
                            ga_mark = SafeText(ga.Mark),
                            ga_name = SafeText(ga.Name),
                            fixture_frame = drawFrame,
                            lines_inserted = drawResult.LinesInserted,
                            lines_failed = drawResult.LinesFailed,
                            text_inserted = textInserted,
                            dimension_inserted = false,
                            primitive_dimension_lines_inserted = primitiveDimensionLinesInserted,
                            draw_evidence = drawEvidence,
                            annotation_layout = annotationLayout,
                            annotation_layout_status = annotationLayout.LayoutStatus,
                            annotation_collision_count = annotationLayout.CollisionCount,
                            immediate,
                            reopened = reopenedStats,
                        }));

                output.WriteLine(
                    "GA fixture U-stage selected="
                    + stagePartIds.Count
                    + " lines="
                    + drawResult.LinesInserted
                    + " failed="
                    + drawResult.LinesFailed
                    + " texts="
                    + textInserted
                    + " primitiveDimensionLines="
                    + primitiveDimensionLinesInserted
                    + ".");
                output.WriteLine("Immediate primitive stats: " + PrimitiveStatsText(immediate));
                output.WriteLine("Reopened primitive stats: " + PrimitiveStatsText(reopenedStats));
                output.WriteLine("Wrote GA fixture U-stage probe: " + Path.GetFullPath(path));
                return 0;
            }
            catch (Exception ex)
            {
                error.WriteLine("ProbeGaFixtureUStageDrawing failed: " + ExceptionText(ex));
                return 98;
            }
        }
        public static int GenerateProcessDrawings(string modelId, string outputDirectory, TextWriter output, TextWriter error)
        {
            var handler = new DrawingHandler();
            if (!handler.GetConnectionStatus())
            {
                error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                return 10;
            }

            var sourceDrawing = FindDrawingByModelId(handler, modelId);
            if (sourceDrawing == null)
            {
                error.WriteLine("No source drawing found for modelId=" + modelId + ".");
                return 40;
            }

            output.WriteLine("Source drawing: " + DrawingSummary(sourceDrawing, null));
            if (!handler.SetActiveDrawing(sourceDrawing, true))
            {
                error.WriteLine("Could not open source drawing for modelId=" + modelId + ".");
                return 41;
            }

            var sourceActive = handler.GetActiveDrawing() ?? sourceDrawing;
            var sourceSheet = sourceActive.GetSheet();
            if (sourceSheet == null)
            {
                error.WriteLine("Source drawing has no sheet.");
                return 42;
            }

            var drawingPartIds = DrawingPartModelIds(sourceSheet);
            output.WriteLine("Source drawing unique drawing part ids: " + drawingPartIds.Count);
            if (drawingPartIds.Count == 0)
            {
                error.WriteLine("Source drawing has no drawing Part objects.");
                return 43;
            }

            var orderedPartIds = OrderAssemblyPartIds(modelId, drawingPartIds, output);
            var steps = BuildSimpleProcessSteps(orderedPartIds, 5);
            handler.CloseActiveDrawing(false);
            output.WriteLine("Closed source drawing without saving before process sheet insertion.");
            var existingSheets = ExistingSheetNumbers(handler, modelId);
            output.WriteLine("Existing process/source sheet numbers for assembly: " + string.Join(",", existingSheets.OrderBy(value => value)));
            var nextSheet = NextAvailableSheetNumber(existingSheets, existingSheets.Count == 0 ? 1 : existingSheets.Max() + 1);
            outputDirectory = string.IsNullOrWhiteSpace(outputDirectory)
                ? Path.Combine("outputs", "tekla-process-drawings-" + modelId)
                : outputDirectory;
            Directory.CreateDirectory(outputDirectory);

            var stepResults = new List<object>();
            foreach (var step in steps)
            {
                while (existingSheets.Contains(nextSheet))
                {
                    nextSheet += 1;
                }

                var sheetNumber = nextSheet++;
                existingSheets.Add(sheetNumber);
                AssemblyDrawing stageDrawing;
                try
                {
                    stageDrawing = new AssemblyDrawing(new Identifier(int.Parse(modelId)), sheetNumber);
                    output.WriteLine("Creating process drawing sheet " + sheetNumber + " for step " + step.StepNo + ".");
                    if (!stageDrawing.Insert())
                    {
                        output.WriteLine("AssemblyDrawing.Insert returned false for sheet " + sheetNumber + ".");
                        stepResults.Add(new { step = step.StepNo, sheetNumber, inserted = false, visible = step.VisiblePartIds.Count, hidden = 0, matched = 0 });
                        continue;
                    }
                }
                catch (Exception ex)
                {
                    output.WriteLine("AssemblyDrawing.Insert threw for sheet " + sheetNumber + ": " + ExceptionText(ex));
                    stepResults.Add(new { step = step.StepNo, sheetNumber, inserted = false, exception = ExceptionText(ex), visible = step.VisiblePartIds.Count, hidden = 0, matched = 0 });
                    continue;
                }

                try
                {
                    if (!handler.SetActiveDrawing(stageDrawing, true))
                    {
                        output.WriteLine("SetActiveDrawing returned false for process sheet " + sheetNumber + ".");
                        stepResults.Add(new { step = step.StepNo, sheetNumber, inserted = true, opened = false, visible = step.VisiblePartIds.Count, hidden = 0, matched = 0 });
                        continue;
                    }
                }
                catch (Exception ex)
                {
                    output.WriteLine("SetActiveDrawing threw for process sheet " + sheetNumber + ": " + ExceptionText(ex));
                    stepResults.Add(new { step = step.StepNo, sheetNumber, inserted = true, opened = false, exception = ExceptionText(ex), visible = step.VisiblePartIds.Count, hidden = 0, matched = 0 });
                    continue;
                }

                var active = handler.GetActiveDrawing() ?? stageDrawing;
                var sheet = active.GetSheet();
                if (sheet == null)
                {
                    output.WriteLine("Process sheet " + sheetNumber + " has no sheet view.");
                    stepResults.Add(new { step = step.StepNo, sheetNumber, inserted = true, opened = true, visible = step.VisiblePartIds.Count, hidden = 0, matched = 0 });
                    continue;
                }

                int matched;
                int hidden;
                ApplyVisibilityOnly(sheet, step.VisiblePartIds, false, out matched, out hidden);
                try
                {
                    active.CommitChanges();
                    handler.SaveActiveDrawing();
                    output.WriteLine("Step " + step.StepNo + " saved sheet=" + sheetNumber + " matched=" + matched + " hidden=" + hidden + " visibleTarget=" + step.VisiblePartIds.Count + ".");
                    stepResults.Add(new { step = step.StepNo, sheetNumber, inserted = true, opened = true, visible = step.VisiblePartIds.Count, hidden, matched });
                    handler.CloseActiveDrawing(true);
                }
                catch (Exception ex)
                {
                    output.WriteLine("Commit/save threw for process sheet " + sheetNumber + ": " + ExceptionText(ex));
                    stepResults.Add(new { step = step.StepNo, sheetNumber, inserted = true, opened = true, saved = false, exception = ExceptionText(ex), visible = step.VisiblePartIds.Count, hidden, matched });
                    handler.CloseActiveDrawing(false);
                }
            }

            var planPath = Path.Combine(outputDirectory, "tekla-process-drawings-" + modelId + ".json");
            var serializer = new JavaScriptSerializer();
            File.WriteAllText(
                planPath,
                serializer.Serialize(
                    new
                    {
                        source_model_id = modelId,
                        source_drawing = DrawingSummary(sourceDrawing, null),
                        part_count = orderedPartIds.Count,
                        steps = steps.Select(step => new { step_no = step.StepNo, title = step.StepType, visible_part_ids = step.VisiblePartIds, new_part_ids = step.NewPartIds }).ToList(),
                        generated_sheets = stepResults,
                    }
                )
            );
            output.WriteLine("Wrote process plan: " + Path.GetFullPath(planPath));
            return 0;
        }

        private static object CreateProbeSheet(DrawingHandler handler, string modelId, int sheetNumber, string attributeName, string label, List<string> visiblePartIds, bool hideWholeDrawing, TextWriter output)
        {
            AssemblyDrawing drawing;
            try
            {
                drawing = new AssemblyDrawing(new Identifier(int.Parse(modelId)), sheetNumber, attributeName);
                output.WriteLine("Creating probe sheet " + sheetNumber + " label=" + label + " attributes=" + attributeName + ".");
                if (!drawing.Insert())
                {
                    output.WriteLine("Probe sheet " + sheetNumber + " Insert returned false.");
                    return new { label, sheetNumber, inserted = false };
                }
            }
            catch (Exception ex)
            {
                output.WriteLine("Probe sheet " + sheetNumber + " Insert threw: " + ExceptionText(ex));
                return new { label, sheetNumber, inserted = false, exception = ExceptionText(ex) };
            }

            try
            {
                if (!handler.SetActiveDrawing(drawing, true))
                {
                    output.WriteLine("Probe sheet " + sheetNumber + " SetActiveDrawing returned false.");
                    return new { label, sheetNumber, inserted = true, opened = false };
                }

                var active = handler.GetActiveDrawing() as AssemblyDrawing ?? drawing;
                var sheet = active.GetSheet();
                if (sheet == null)
                {
                    output.WriteLine("Probe sheet " + sheetNumber + " has no sheet.");
                    return new { label, sheetNumber, inserted = true, opened = true, has_sheet = false };
                }

                var before = DrawingSheetStats(active, sheet);
                int matched = 0;
                int hidden = 0;
                if (hideWholeDrawing)
                {
                    ApplyVisibilityOnly(sheet, visiblePartIds, true, out matched, out hidden);
                }

                active.CommitChanges();
                handler.SaveActiveDrawing();
                var after = DrawingSheetStats(active, active.GetSheet());
                output.WriteLine(
                    "Probe sheet " + sheetNumber
                    + " label=" + label
                    + " before(dim=" + before.Dimensions + ", marks=" + before.Marks + ", texts=" + before.Texts + ", parts=" + before.Parts + ")"
                    + " after(dim=" + after.Dimensions + ", marks=" + after.Marks + ", texts=" + after.Texts + ", parts=" + after.Parts + ", hiddenParts=" + after.HiddenParts + ")"
                    + " matched=" + matched
                    + " hiddenOps=" + hidden
                    + "."
                );
                handler.CloseActiveDrawing(true);
                return new { label, sheetNumber, inserted = true, opened = true, matched, hidden, before, after };
            }
            catch (Exception ex)
            {
                output.WriteLine("Probe sheet " + sheetNumber + " failed: " + ExceptionText(ex));
                try
                {
                    handler.CloseActiveDrawing(false);
                }
                catch
                {
                    // Ignore Tekla cleanup failures for probe drawings.
                }
                return new { label, sheetNumber, inserted = true, opened = false, exception = ExceptionText(ex) };
            }
        }

        public static int InspectDrawingByModelId(string modelId, TextWriter output, TextWriter error)
        {
            var handler = new DrawingHandler();
            if (!handler.GetConnectionStatus())
            {
                error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                return 10;
            }

            var drawings = handler.GetDrawings();
            while (drawings.MoveNext())
            {
                var drawing = drawings.Current;
                if (drawing == null || DrawingModelIdentifier(drawing) != modelId)
                {
                    continue;
                }

                output.WriteLine("Found drawing: " + DrawingSummary(drawing, null));
                if (!handler.SetActiveDrawing(drawing, true))
                {
                    error.WriteLine("SetActiveDrawing returned false for modelId=" + modelId + ".");
                    return 30;
                }

                var active = handler.GetActiveDrawing() ?? drawing;
                var sheet = active.GetSheet();
                if (sheet == null)
                {
                    error.WriteLine("Drawing has no sheet: modelId=" + modelId + ".");
                    return 31;
                }

                output.WriteLine("Opened drawing: " + DrawingSummary(active, null));
                output.WriteLine("Sheet Part objects: " + CountDrawingObjects(sheet, typeof(Part)));
                output.WriteLine("Sheet Mark objects: " + CountDrawingObjects(sheet, typeof(Mark)));
                output.WriteLine("Sheet View objects: " + CountDrawingObjects(sheet, typeof(View)));
                output.WriteLine("No hide/show/save operations were executed.");
                return 0;
            }

            error.WriteLine("No drawing found for modelId=" + modelId + ".");
            return 32;
        }

        private static Drawing FindDrawingByModelId(DrawingHandler handler, string modelId)
        {
            var drawings = handler.GetDrawings();
            while (drawings.MoveNext())
            {
                var drawing = drawings.Current;
                if (drawing != null && DrawingModelIdentifier(drawing) == modelId)
                {
                    return drawing;
                }
            }

            return null;
        }

        private static IEnumerable<AssemblyDrawing> SelectedAssemblyDrawings(DrawingHandler handler)
        {
            var selected = handler.GetDrawingSelector().GetSelected();
            while (selected.MoveNext())
            {
                var drawing = selected.Current as AssemblyDrawing;
                if (drawing != null)
                {
                    yield return drawing;
                }
            }
        }

        private static List<AssemblyDrawing> DrawingsByModelId(DrawingHandler handler, string modelId)
        {
            var result = new List<AssemblyDrawing>();
            var drawings = handler.GetDrawings();
            while (drawings.MoveNext())
            {
                var drawing = drawings.Current as AssemblyDrawing;
                if (drawing != null && DrawingModelIdentifier(drawing) == modelId)
                {
                    result.Add(drawing);
                }
            }

            return result;
        }

        private static SheetStats TryReadDrawingStats(DrawingHandler handler, AssemblyDrawing drawing, TextWriter output)
        {
            try
            {
                if (!handler.SetActiveDrawing(drawing, true))
                {
                    output.WriteLine("Could not open cloned drawing for stats: " + DrawingSummary(drawing, null));
                    return null;
                }

                var active = handler.GetActiveDrawing() as AssemblyDrawing ?? drawing;
                var sheet = active.GetSheet();
                if (sheet == null)
                {
                    output.WriteLine("Cloned drawing has no sheet: " + DrawingSummary(active, null));
                    handler.CloseActiveDrawing(false);
                    return null;
                }

                var stats = DrawingSheetStats(active, sheet);
                output.WriteLine(
                    "Cloned stats sheet=" + stats.Sheet
                    + " parts=" + stats.Parts
                    + " marks=" + stats.Marks
                    + " dimensions=" + stats.Dimensions
                    + " texts=" + stats.Texts
                    + " views=" + stats.Views
                    + "."
                );
                handler.CloseActiveDrawing(false);
                return stats;
            }
            catch (Exception ex)
            {
                output.WriteLine("Could not read cloned drawing stats: " + ExceptionText(ex));
                try
                {
                    handler.CloseActiveDrawing(false);
                }
                catch
                {
                    // Ignore cleanup failures while probing cloned drawings.
                }
                return null;
            }
        }

        public static int ListSelectedModelObjects(TextWriter output, TextWriter error)
        {
            var model = new Tekla.Structures.Model.Model();
            if (!model.GetConnectionStatus())
            {
                error.WriteLine("Tekla Model API is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                return 20;
            }

            var selected = new Tekla.Structures.Model.UI.ModelObjectSelector().GetSelectedObjects();
            var count = 0;
            while (selected.MoveNext())
            {
                var modelObject = selected.Current as Tekla.Structures.Model.ModelObject;
                if (modelObject == null || modelObject.Identifier == null)
                {
                    continue;
                }

                count += 1;
                output.WriteLine(count + ". " + ModelObjectSummary(modelObject));
            }

            output.WriteLine("Selected model objects: " + count);
            return 0;
        }

        public static int ListDrawings(Options options, TextWriter output, TextWriter error)
        {
            var handler = new DrawingHandler();
            if (!handler.GetConnectionStatus())
            {
                error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                return 10;
            }

            StepPayload payload = null;
            if (!string.IsNullOrWhiteSpace(options.StepsPath) && File.Exists(options.StepsPath))
            {
                payload = StepPayload.Load(options.StepsPath);
                output.WriteLine("Target member: " + payload.MemberId);
                output.WriteLine("Target assembly: " + payload.AssemblyId);
            }

            var active = handler.GetActiveDrawing();
            output.WriteLine("Active drawing: " + (active == null ? "<none>" : DrawingSummary(active, payload)));
            output.WriteLine("Drawings:");

            var count = 0;
            var drawings = handler.GetDrawings();
            while (drawings.MoveNext())
            {
                var drawing = drawings.Current;
                if (drawing == null)
                {
                    continue;
                }

                count += 1;
                output.WriteLine("  " + count + ". " + DrawingSummary(drawing, payload));
            }

            output.WriteLine("Total drawings: " + count);
            return 0;
        }

        public static int ApplyStepToActiveDrawing(StepPayload payload, DrawingStep step, bool createDrawing, TextWriter output, TextWriter error)
        {
            var handler = new DrawingHandler();
            if (!handler.GetConnectionStatus())
            {
                error.WriteLine("Tekla DrawingHandler is not connected. Open Tekla Structures 2017 and a drawing, then rerun.");
                return 10;
            }

            var drawing = handler.GetActiveDrawing();
            if (drawing == null && createDrawing)
            {
                var candidateIdentifiers = ResolveDrawingAssemblyIdentifiers(payload, step, output);
                var attemptedIds = new List<string>();
                foreach (var candidateIdentifier in candidateIdentifiers)
                {
                    attemptedIds.Add(candidateIdentifier.ID.ToString());
                    drawing = OpenOrCreateAssemblyDrawing(handler, candidateIdentifier, output);
                    if (drawing != null)
                    {
                        break;
                    }
                }

                if (drawing == null)
                {
                    error.WriteLine("AssemblyDrawing could not be opened or inserted. Attempted assembly identifiers: " + string.Join(", ", attemptedIds));
                    return 14;
                }
            }

            if (drawing == null)
            {
                error.WriteLine("No active drawing. Open an assembly drawing or rerun with --create-drawing.");
                return 11;
            }

            var sheet = drawing.GetSheet();
            if (sheet == null)
            {
                error.WriteLine("Active drawing has no sheet view.");
                return 12;
            }

            var visibleIds = new HashSet<string>(step.VisiblePartIds);
            var newIds = new HashSet<string>(step.NewPartIds);
            var matchedParts = 0;
            var hiddenParts = 0;
            var markAttempts = 0;
            var markInserted = 0;

            var objects = sheet.GetAllObjects(new[] { typeof(Part) });
            while (objects.MoveNext())
            {
                var part = objects.Current as Part;
                if (part == null || part.ModelIdentifier == null)
                {
                    continue;
                }

                var modelId = part.ModelIdentifier.ID.ToString();
                if (!visibleIds.Contains(modelId))
                {
                    part.Hideable.HideFromDrawingView();
                    hiddenParts += 1;
                    continue;
                }

                matchedParts += 1;
                part.Hideable.ShowInDrawingView();
                if (!newIds.Contains(modelId))
                {
                    continue;
                }

                markAttempts += 1;
                try
                {
                    var mark = new Mark(part);
                    if (mark.Insert())
                    {
                        markInserted += 1;
                    }
                }
                catch (Exception ex)
                {
                    output.WriteLine("Mark insert failed for part " + modelId + ": " + ex.Message);
                }
            }

            drawing.CommitChanges();
            handler.SaveActiveDrawing();
            output.WriteLine("Matched visible drawing parts: " + matchedParts);
            output.WriteLine("Hidden drawing parts: " + hiddenParts);
            output.WriteLine("Mark attempts: " + markAttempts);
            output.WriteLine("Marks inserted: " + markInserted);
            return 0;
        }

        private static string DrawingSummary(Drawing drawing, StepPayload payload)
        {
            var modelId = DrawingModelIdentifier(drawing);
            var match = payload != null && modelId == payload.AssemblyId ? " MATCH_TARGET" : "";
            return string.Join(
                " | ",
                new[]
                {
                    drawing.GetType().Name + match,
                    "modelId=" + modelId,
                    "sheet=" + DrawingSheetNumber(drawing),
                    "mark=" + SafeText(drawing.Mark),
                    "name=" + SafeText(drawing.Name),
                    "title1=" + SafeText(drawing.Title1),
                    "title2=" + SafeText(drawing.Title2),
                    "title3=" + SafeText(drawing.Title3),
                    "upToDate=" + drawing.UpToDateStatus,
                    "locked=" + drawing.IsLocked,
                }
            );
        }

        private static string DrawingModelIdentifier(Drawing drawing)
        {
            var assemblyDrawing = drawing as AssemblyDrawing;
            if (assemblyDrawing != null && assemblyDrawing.AssemblyIdentifier != null)
            {
                return assemblyDrawing.AssemblyIdentifier.ID.ToString();
            }

            var singlePartDrawing = drawing as SinglePartDrawing;
            if (singlePartDrawing != null && singlePartDrawing.PartIdentifier != null)
            {
                return singlePartDrawing.PartIdentifier.ID.ToString();
            }

            var castUnitDrawing = drawing as CastUnitDrawing;
            if (castUnitDrawing != null && castUnitDrawing.CastUnitIdentifier != null)
            {
                return castUnitDrawing.CastUnitIdentifier.ID.ToString();
            }

            return "";
        }

        private static string DrawingSheetNumber(Drawing drawing)
        {
            var assemblyDrawing = drawing as AssemblyDrawing;
            if (assemblyDrawing != null)
            {
                return assemblyDrawing.SheetNumber.ToString();
            }

            var singlePartDrawing = drawing as SinglePartDrawing;
            if (singlePartDrawing != null)
            {
                return singlePartDrawing.SheetNumber.ToString();
            }

            return "";
        }

        private static int CountDrawingObjects(ContainerView sheet, Type objectType)
        {
            var count = 0;
            var objects = sheet.GetAllObjects(new[] { objectType });
            while (objects.MoveNext())
            {
                if (objects.Current != null)
                {
                    count += 1;
                }
            }

            return count;
        }

        private static void Increment(Dictionary<string, int> counts, string key)
        {
            if (string.IsNullOrWhiteSpace(key))
            {
                key = "<empty>";
            }

            int value;
            counts.TryGetValue(key, out value);
            counts[key] = value + 1;
        }

        private static SheetStats DrawingSheetStats(AssemblyDrawing drawing, ContainerView sheet)
        {
            int partCount;
            int hiddenParts;
            int visibleParts;
            CountParts(sheet, out partCount, out visibleParts, out hiddenParts);
            return new SheetStats
            {
                Sheet = drawing.SheetNumber,
                Mark = SafeText(drawing.Mark),
                Name = SafeText(drawing.Name),
                Title1 = SafeText(drawing.Title1),
                Parts = partCount,
                VisibleParts = visibleParts,
                HiddenParts = hiddenParts,
                UniquePartIds = DrawingPartModelIds(sheet).Count,
                Marks = CountDrawingObjects(sheet, typeof(Mark)),
                MarkSets = CountDrawingObjects(sheet, typeof(MarkSet)),
                StraightDimensions = CountDrawingObjects(sheet, typeof(StraightDimension)),
                StraightDimensionSets = CountDrawingObjects(sheet, typeof(StraightDimensionSet)),
                AngleDimensions = CountDrawingObjects(sheet, typeof(AngleDimension)),
                RadiusDimensions = CountDrawingObjects(sheet, typeof(RadiusDimension)),
                CurvedDimensions = CountDrawingObjects(sheet, typeof(CurvedDimensionOrthogonal)) + CountDrawingObjects(sheet, typeof(CurvedDimensionRadial)),
                Texts = CountDrawingObjects(sheet, typeof(Text)),
                Welds = CountDrawingObjects(sheet, typeof(Weld)),
                WeldMarks = CountDrawingObjects(sheet, typeof(WeldMark)),
                Bolts = CountDrawingObjects(sheet, typeof(Bolt)),
                SectionMarks = CountDrawingObjects(sheet, typeof(SectionMark)),
                Views = CountDrawingObjects(sheet, typeof(View)),
            };
        }

        private static void CountParts(ContainerView sheet, out int partCount, out int visibleParts, out int hiddenParts)
        {
            partCount = 0;
            visibleParts = 0;
            hiddenParts = 0;
            var objects = sheet.GetAllObjects(new[] { typeof(Part) });
            while (objects.MoveNext())
            {
                var part = objects.Current as Part;
                if (part == null)
                {
                    continue;
                }

                partCount += 1;
                if (part.Hideable != null && part.Hideable.IsHidden)
                {
                    hiddenParts += 1;
                }
                else
                {
                    visibleParts += 1;
                }
            }
        }

        private static List<string> DrawingPartModelIds(ContainerView sheet)
        {
            var result = new List<string>();
            var seen = new HashSet<string>();
            var objects = sheet.GetAllObjects(new[] { typeof(Part) });
            while (objects.MoveNext())
            {
                var part = objects.Current as Part;
                if (part == null || part.ModelIdentifier == null)
                {
                    continue;
                }

                var modelId = part.ModelIdentifier.ID.ToString();
                if (seen.Add(modelId))
                {
                    result.Add(modelId);
                }
            }

            return result;
        }

        private static List<string> SelectFixtureUStagePartIds(List<string> orderedPartIds, TextWriter output, out FixtureFrame frame, out List<object> evidence)
        {
            evidence = new List<object>();
            var allEdges = ModelPartEdges(orderedPartIds, output);
            frame = allEdges.Count == 0 ? null : BuildFixtureFrame(allEdges);
            if (!IsValidFixtureFrame(frame))
            {
                output.WriteLine("Could not build fixture frame for U-stage selection; solidEdges=" + allEdges.Count + ".");
                return new List<string>();
            }

            var fixtureFrame = frame;
            var boxes = ModelPartBoxes(orderedPartIds, output);
            var snapshots = boxes.Select(box => BuildFixturePartSnapshot(box, fixtureFrame)).ToList();
            if (snapshots.Count == 0)
            {
                return new List<string>();
            }

            var axisExtent = Math.Max(1.0, fixtureFrame.AxisMax - fixtureFrame.AxisMin);
            var widthExtent = Math.Max(1.0, fixtureFrame.WidthMax - fixtureFrame.WidthMin);
            var heightExtent = Math.Max(1.0, fixtureFrame.HeightMax - fixtureFrame.HeightMin);
            var minAxisSpan = Math.Max(800.0, axisExtent * 0.10);
            var thinWidthLimit = widthExtent * 0.25;
            var thinHeightLimit = heightExtent * 0.25;
            var wideLimit = widthExtent * 0.45;
            var tallLimit = heightExtent * 0.45;
            var bottomCenterLimit = fixtureFrame.HeightMin + heightExtent * 0.25;
            var sideMinCenterLimit = fixtureFrame.WidthMin + widthExtent * 0.25;
            var sideMaxCenterLimit = fixtureFrame.WidthMax - widthExtent * 0.25;

            var bottom = snapshots
                .Where(item => item.AxisSpan >= minAxisSpan && item.WidthSpan >= wideLimit && item.HeightSpan <= thinHeightLimit && item.HeightCenter <= bottomCenterLimit)
                .OrderBy(item => item.AxisMin)
                .ToList();
            var sideMin = snapshots
                .Where(item => item.AxisSpan >= minAxisSpan && item.HeightSpan >= tallLimit && item.WidthSpan <= thinWidthLimit && item.WidthCenter <= sideMinCenterLimit)
                .OrderBy(item => item.AxisMin)
                .ToList();
            var sideMax = snapshots
                .Where(item => item.AxisSpan >= minAxisSpan && item.HeightSpan >= tallLimit && item.WidthSpan <= thinWidthLimit && item.WidthCenter >= sideMaxCenterLimit)
                .OrderBy(item => item.AxisMin)
                .ToList();

            var selected = new List<string>();
            foreach (var item in bottom.Concat(sideMin).Concat(sideMax))
            {
                if (!selected.Contains(item.PartId))
                {
                    selected.Add(item.PartId);
                }
            }

            var selectionMode = "PHYSICAL_PARTS";
            FixturePartSnapshot virtualBox = null;
            if (selected.Count == 0)
            {
                virtualBox = snapshots
                    .Where(item => IsBoxProfile(item.Profile))
                    .OrderByDescending(item => item.AxisSpan)
                    .ThenByDescending(item => item.WidthSpan * item.HeightSpan)
                    .FirstOrDefault();
                if (virtualBox != null)
                {
                    selected.Add(virtualBox.PartId);
                    selectionMode = "VIRTUAL_DECOMPOSED_BOX_PROFILE";
                    output.WriteLine("Fixture U-stage using virtual BOX profile decomposition from part " + virtualBox.PartId + " profile=" + virtualBox.Profile + ".");
                }
            }

            var order = orderedPartIds.Select((id, index) => new { id, index }).ToDictionary(item => item.id, item => item.index);
            selected = selected.OrderBy(id => order.ContainsKey(id) ? order[id] : int.MaxValue).ToList();
            evidence.Add(new
            {
                frame = new
                {
                    fixtureFrame.AxisIndex,
                    fixtureFrame.WidthIndex,
                    fixtureFrame.HeightIndex,
                    fixtureFrame.AxisMin,
                    fixtureFrame.AxisMax,
                    fixtureFrame.WidthMin,
                    fixtureFrame.WidthMax,
                    fixtureFrame.HeightMin,
                    fixtureFrame.HeightMax,
                    fixtureFrame.FixtureFace,
                },
                thresholds = new
                {
                    min_axis_span = minAxisSpan,
                    thin_width_limit = thinWidthLimit,
                    thin_height_limit = thinHeightLimit,
                    wide_limit = wideLimit,
                    tall_limit = tallLimit,
                    bottom_center_limit = bottomCenterLimit,
                    side_min_center_limit = sideMinCenterLimit,
                    side_max_center_limit = sideMaxCenterLimit,
                },
                bottom_part_ids = bottom.Select(item => item.PartId).ToList(),
                side_min_part_ids = sideMin.Select(item => item.PartId).ToList(),
                side_max_part_ids = sideMax.Select(item => item.PartId).ToList(),
                selection_mode = selectionMode,
                virtual_box_part_id = virtualBox == null ? "" : virtualBox.PartId,
                virtual_box_profile = virtualBox == null ? "" : virtualBox.Profile,
                virtual_box_part_position = virtualBox == null ? "" : virtualBox.PartPosition,
                selected_part_ids = selected,
                snapshots = snapshots.Select(item => new
                {
                    item.PartId,
                    item.Name,
                    item.Profile,
                    item.Material,
                    item.PartPosition,
                    item.AssemblyPosition,
                    item.AxisSpan,
                    item.WidthSpan,
                    item.HeightSpan,
                    item.AxisCenter,
                    item.WidthCenter,
                    item.HeightCenter,
                }).ToList(),
            });
            output.WriteLine(
                "Fixture U-stage selection bottom="
                + bottom.Count
                + " sideMin="
                + sideMin.Count
                + " sideMax="
                + sideMax.Count
                + " selected="
                + selected.Count
                + ".");
            return selected;
        }

        private static FixturePartSnapshot BuildFixturePartSnapshot(ModelPartBox box, FixtureFrame frame)
        {
            var axisMin = CoordinateAt(box.Min, frame.AxisIndex);
            var axisMax = CoordinateAt(box.Max, frame.AxisIndex);
            var widthMin = CoordinateAt(box.Min, frame.WidthIndex);
            var widthMax = CoordinateAt(box.Max, frame.WidthIndex);
            var heightMin = CoordinateAt(box.Min, frame.HeightIndex);
            var heightMax = CoordinateAt(box.Max, frame.HeightIndex);
            return new FixturePartSnapshot
            {
                PartId = box.PartId,
                Name = box.Name,
                Profile = box.Profile,
                Material = box.Material,
                PartPosition = box.PartPosition,
                AssemblyPosition = box.AssemblyPosition,
                AxisMin = axisMin,
                AxisMax = axisMax,
                WidthMin = widthMin,
                WidthMax = widthMax,
                HeightMin = heightMin,
                HeightMax = heightMax,
                AxisSpan = Math.Abs(axisMax - axisMin),
                WidthSpan = Math.Abs(widthMax - widthMin),
                HeightSpan = Math.Abs(heightMax - heightMin),
                AxisCenter = (axisMin + axisMax) / 2.0,
                WidthCenter = (widthMin + widthMax) / 2.0,
                HeightCenter = (heightMin + heightMax) / 2.0,
            };
        }
        private static StageDrawResult DrawFixtureUStageProjectionGeometry(
            ContainerView sheet,
            string assemblyId,
            List<string> visiblePartIds,
            TextWriter output,
            out FixtureFrame frame,
            out List<object> evidence)
        {
            evidence = new List<object>();
            var edges = ModelPartEdges(visiblePartIds, output);
            frame = edges.Count == 0 ? null : BuildFixtureFrame(edges);
            if (!IsValidFixtureFrame(frame))
            {
                output.WriteLine("No valid fixture frame for U-stage; solidEdges=" + edges.Count + ".");
                return new StageDrawResult();
            }

            var fixtureFrame = frame;
            var boxes = ModelPartBoxes(visiblePartIds, output);
            var box = boxes
                .Where(item => IsBoxProfile(item.Profile))
                .OrderByDescending(item => CoordinateAt(item.Max, fixtureFrame.AxisIndex) - CoordinateAt(item.Min, fixtureFrame.AxisIndex))
                .FirstOrDefault();
            if (box == null)
            {
                output.WriteLine("No BOX profile source found for U-stage geometry; falling back to full solid edge projection.");
                return DrawFixtureProjectionStageGeometry(sheet, assemblyId, visiblePartIds, output, out frame, out evidence);
            }

            var axisSpan = Math.Max(1.0, fixtureFrame.AxisMax - fixtureFrame.AxisMin);
            var widthSpan = Math.Max(1.0, fixtureFrame.WidthMax - fixtureFrame.WidthMin);
            var wallThickness = ParseBoxWallThickness(box.Profile);
            if (wallThickness <= 0.0 || wallThickness >= widthSpan / 2.0)
            {
                wallThickness = Math.Max(10.0, widthSpan * 0.05);
            }
            wallThickness = Math.Min(wallThickness, widthSpan / 3.0);

            var drawLeft = 35.0;
            var drawBottom = 80.0;
            var drawWidth = 500.0;
            var drawHeight = 180.0;
            var scale = Math.Min(drawWidth / axisSpan, drawHeight / widthSpan);
            var left = drawLeft;
            var right = drawLeft + axisSpan * scale;
            var bottom = drawBottom;
            var top = drawBottom + widthSpan * scale;
            var thickness = Math.Max(2.0, wallThickness * scale);
            var result = new StageDrawResult();
            result.ModelLength = axisSpan;
            result.ModelWidth = widthSpan;
            result.ModelThickness = wallThickness;

            InsertProjectionRectangle(sheet, left, bottom, right, top, result);
            InsertProjectionRectangle(sheet, left, bottom, right, bottom + thickness, result);
            InsertProjectionRectangle(sheet, left, top - thickness, right, top, result);

            evidence.Add(new
            {
                mode = "VIRTUAL_DECOMPOSED_BOX_PROFILE",
                source_part = new
                {
                    box.PartId,
                    box.Name,
                    box.Profile,
                    box.Material,
                    box.PartPosition,
                    box.AssemblyPosition,
                },
                visible_part_count = visiblePartIds.Count,
                solid_edge_count = edges.Count,
                axis_span = axisSpan,
                width_span = widthSpan,
                wall_thickness = wallThickness,
                drawing_scale = scale,
                fixture_frame = new
                {
                    fixtureFrame.AxisIndex,
                    fixtureFrame.WidthIndex,
                    fixtureFrame.HeightIndex,
                    fixtureFrame.AxisMin,
                    fixtureFrame.AxisMax,
                    fixtureFrame.WidthMin,
                    fixtureFrame.WidthMax,
                    fixtureFrame.HeightMin,
                    fixtureFrame.HeightMax,
                    fixtureFrame.FixtureFace,
                },
                projected_bounds = new { min_x = 0.0, max_x = axisSpan, min_y = 0.0, max_y = widthSpan },
            });
            output.WriteLine("Fixture U-stage virtual BOX geometry part=" + box.PartId + " length=" + axisSpan + " width=" + widthSpan + " thickness=" + wallThickness + " lines=" + result.LinesInserted + ".");
            return result;
        }

        private static bool IsBoxProfile(string profile)
        {
            return !string.IsNullOrWhiteSpace(profile)
                && profile.Trim().StartsWith("BOX", StringComparison.OrdinalIgnoreCase);
        }

        private static double ParseBoxWallThickness(string profile)
        {
            if (string.IsNullOrWhiteSpace(profile))
            {
                return 0.0;
            }

            var numbers = new List<double>();
            var token = "";
            foreach (var ch in profile)
            {
                if (char.IsDigit(ch) || ch == '.')
                {
                    token += ch;
                }
                else if (token.Length > 0)
                {
                    double value;
                    if (double.TryParse(token, out value))
                    {
                        numbers.Add(value);
                    }
                    token = "";
                }
            }

            if (token.Length > 0)
            {
                double value;
                if (double.TryParse(token, out value))
                {
                    numbers.Add(value);
                }
            }

            if (numbers.Count >= 4)
            {
                return Math.Min(numbers[2], numbers[3]);
            }
            if (numbers.Count >= 3)
            {
                return numbers[2];
            }
            return 0.0;
        }

        private static void InsertProjectionRectangle(ContainerView sheet, double left, double bottom, double right, double top, StageDrawResult result)
        {
            if (Math.Abs(right - left) < 1.0)
            {
                right = left + 1.0;
            }
            if (Math.Abs(top - bottom) < 1.0)
            {
                top = bottom + 1.0;
            }

            InsertLine(sheet, left, bottom, right, bottom, result);
            InsertLine(sheet, right, bottom, right, top, result);
            InsertLine(sheet, right, top, left, top, result);
            InsertLine(sheet, left, top, left, bottom, result);
            result.Rectangles += 1;
            result.MinX = result.Rectangles == 1 ? left : Math.Min(result.MinX, left);
            result.MaxX = result.Rectangles == 1 ? right : Math.Max(result.MaxX, right);
            result.MinY = result.Rectangles == 1 ? bottom : Math.Min(result.MinY, bottom);
            result.MaxY = result.Rectangles == 1 ? top : Math.Max(result.MaxY, top);
        }
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

            var fixtureFrame = frame;
            var projected = edges.Select(edge => ProjectEdge(edge, fixtureFrame)).ToList();
            var minX = projected.Min(edge => Math.Min(edge.X1, edge.X2));
            var maxX = projected.Max(edge => Math.Max(edge.X1, edge.X2));
            var minY = projected.Min(edge => Math.Min(edge.Y1, edge.Y2));
            var maxY = projected.Max(edge => Math.Max(edge.Y1, edge.Y2));
            var drawLeft = 35.0;
            var drawBottom = 80.0;
            var drawWidth = 500.0;
            var drawHeight = 180.0;
            var scale = Math.Min(drawWidth / Math.Max(1.0, maxX - minX), drawHeight / Math.Max(1.0, maxY - minY));
            var attempted = 0;

            foreach (var edge in projected)
            {
                attempted += 1;
                var x1 = drawLeft + (edge.X1 - minX) * scale;
                var y1 = drawBottom + (edge.Y1 - minY) * scale;
                var x2 = drawLeft + (edge.X2 - minX) * scale;
                var y2 = drawBottom + (edge.Y2 - minY) * scale;
                InsertLine(sheet, x1, y1, x2, y2, result);
                if (attempted == 1)
                {
                    result.MinX = Math.Min(x1, x2);
                    result.MaxX = Math.Max(x1, x2);
                    result.MinY = Math.Min(y1, y2);
                    result.MaxY = Math.Max(y1, y2);
                }
                else
                {
                    result.MinX = Math.Min(result.MinX, Math.Min(x1, x2));
                    result.MaxX = Math.Max(result.MaxX, Math.Max(x1, x2));
                    result.MinY = Math.Min(result.MinY, Math.Min(y1, y2));
                    result.MaxY = Math.Max(result.MaxY, Math.Max(y1, y2));
                }
            }

            result.Rectangles = result.LinesInserted > 0 ? 1 : 0;
            var distinctParts = edges.Select(edge => edge.PartId).Distinct().Count();
            evidence.Add(
                new
                {
                    visible_part_count = visiblePartIds.Count,
                    solid_edge_count = edges.Count,
                    projected_edge_count = projected.Count,
                    distinct_part_count = distinctParts,
                    drawing_scale = scale,
                    fixture_frame = new
                    {
                        fixtureFrame.AxisIndex,
                        fixtureFrame.WidthIndex,
                        fixtureFrame.HeightIndex,
                        fixtureFrame.AxisMin,
                        fixtureFrame.AxisMax,
                        fixtureFrame.WidthMin,
                        fixtureFrame.WidthMax,
                        fixtureFrame.HeightMin,
                        fixtureFrame.HeightMax,
                        fixtureFrame.FixtureFace,
                    },
                    projected_bounds = new { min_x = minX, max_x = maxX, min_y = minY, max_y = maxY },
                    max_projection_shortening = projected.Count == 0 ? 0.0 : projected.Max(edge => edge.ModelLength - edge.ProjectionLength),
                });

            output.WriteLine(
                "Fixture true projection edges="
                + edges.Count
                + " projected="
                + projected.Count
                + " insertedLines="
                + result.LinesInserted
                + " parts="
                + distinctParts
                + " frame="
                + frame.FixtureFace
                + ".");
            return result;
        }

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
                    var edgeEnumerator = solid == null ? null : solid.GetEdgeEnumerator();
                    while (edgeEnumerator != null && edgeEnumerator.MoveNext())
                    {
                        var edge = edgeEnumerator.Current as Tekla.Structures.Solid.Edge;
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

        private static bool IsValidFixtureFrame(FixtureFrame frame)
        {
            return frame != null
                && Math.Abs(frame.AxisMax - frame.AxisMin) > 1.0
                && Math.Abs(frame.WidthMax - frame.WidthMin) > 1.0;
        }

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

        private static double Distance3d(Tekla.Structures.Geometry3d.Point first, Tekla.Structures.Geometry3d.Point second)
        {
            var dx = first.X - second.X;
            var dy = first.Y - second.Y;
            var dz = first.Z - second.Z;
            return Math.Sqrt(dx * dx + dy * dy + dz * dz);
        }

        private static int InsertText(ContainerView sheet, double x, double y, string value)
        {
            try
            {
                var text = new Text(sheet, new Tekla.Structures.Geometry3d.Point(x, y, 0), value);
                return text.Insert() ? 1 : 0;
            }
            catch
            {
                return 0;
            }
        }
        private static StageDrawResult DrawModelAabbStageGeometry(ContainerView sheet, string assemblyId, List<string> visiblePartIds, TextWriter output)
        {
            var boxes = ModelPartBoxes(visiblePartIds, output);
            var result = new StageDrawResult();
            if (boxes.Count == 0)
            {
                return result;
            }

            var min = new[] { boxes.Min(item => item.Min.X), boxes.Min(item => item.Min.Y), boxes.Min(item => item.Min.Z) };
            var max = new[] { boxes.Max(item => item.Max.X), boxes.Max(item => item.Max.Y), boxes.Max(item => item.Max.Z) };
            var extents = new[] { max[0] - min[0], max[1] - min[1], max[2] - min[2] };
            var primary = 0;
            if (extents[1] > extents[primary]) primary = 1;
            if (extents[2] > extents[primary]) primary = 2;
            var secondary = Enumerable.Range(0, 3).Where(index => index != primary).OrderByDescending(index => extents[index]).First();
            var x0 = 40.0;
            var y0 = 85.0;
            var width = 430.0;
            var height = 170.0;
            var primarySpan = Math.Max(1.0, extents[primary]);
            var secondarySpan = Math.Max(1.0, extents[secondary]);

            foreach (var box in boxes)
            {
                var pMin = CoordinateAt(box.Min, primary);
                var pMax = CoordinateAt(box.Max, primary);
                var sMin = CoordinateAt(box.Min, secondary);
                var sMax = CoordinateAt(box.Max, secondary);
                var left = x0 + (pMin - min[primary]) / primarySpan * width;
                var right = x0 + (pMax - min[primary]) / primarySpan * width;
                var bottom = y0 + (sMin - min[secondary]) / secondarySpan * height;
                var top = y0 + (sMax - min[secondary]) / secondarySpan * height;
                if (Math.Abs(right - left) < 1.0)
                {
                    right = left + 1.0;
                }
                if (Math.Abs(top - bottom) < 1.0)
                {
                    top = bottom + 1.0;
                }

                InsertLine(sheet, left, bottom, right, bottom, result);
                InsertLine(sheet, right, bottom, right, top, result);
                InsertLine(sheet, right, top, left, top, result);
                InsertLine(sheet, left, top, left, bottom, result);
                result.Rectangles += 1;
                result.MinX = result.Rectangles == 1 ? left : Math.Min(result.MinX, left);
                result.MaxX = result.Rectangles == 1 ? right : Math.Max(result.MaxX, right);
                result.MinY = result.Rectangles == 1 ? bottom : Math.Min(result.MinY, bottom);
                result.MaxY = result.Rectangles == 1 ? top : Math.Max(result.MaxY, top);
            }

            output.WriteLine("Projected model AABB stage geometry boxes=" + boxes.Count + " primaryAxis=" + primary + " secondaryAxis=" + secondary + ".");
            return result;
        }

        private static List<ModelPartBox> ModelPartBoxes(List<string> visiblePartIds, TextWriter output)
        {
            var result = new List<ModelPartBox>();
            var model = new Tekla.Structures.Model.Model();
            if (!model.GetConnectionStatus())
            {
                output.WriteLine("Model API not connected for AABB geometry.");
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
                        continue;
                    }

                    var solid = part.GetSolid();
                    if (solid == null || solid.MinimumPoint == null || solid.MaximumPoint == null)
                    {
                        continue;
                    }

                    result.Add(new ModelPartBox
                    {
                        PartId = partId,
                        Name = ReportText(part, "NAME"),
                        Profile = ReportText(part, "PROFILE"),
                        Material = ReportText(part, "MATERIAL"),
                        PartPosition = ReportText(part, "PART_POS"),
                        AssemblyPosition = ReportText(part, "ASSEMBLY_POS"),
                        Min = CopyPoint(solid.MinimumPoint),
                        Max = CopyPoint(solid.MaximumPoint),
                    });
                }
                catch (Exception ex)
                {
                    output.WriteLine("AABB read failed for part " + partId + ": " + ExceptionText(ex));
                }
            }

            return result;
        }

        private static double CoordinateAt(Tekla.Structures.Geometry3d.Point point, int axis)
        {
            if (axis == 0) return point.X;
            if (axis == 1) return point.Y;
            return point.Z;
        }

        private static void InsertLine(ContainerView sheet, double x1, double y1, double x2, double y2, StageDrawResult result)
        {
            try
            {
                var line = new Line(
                    sheet,
                    new Tekla.Structures.Geometry3d.Point(x1, y1, 0),
                    new Tekla.Structures.Geometry3d.Point(x2, y2, 0));
                if (line.Insert())
                {
                    result.LinesInserted += 1;
                }
                else
                {
                    result.LinesFailed += 1;
                }
            }
            catch
            {
                result.LinesFailed += 1;
            }
        }

        private static DrawingAnnotationLayout BuildFixtureUStageAnnotationLayout(StageDrawResult result, FixtureFrame frame, string sourcePartLabel)
        {
            var layout = new DrawingAnnotationLayout();

            AddLayoutText(layout, "TITLE", "STAGE 1 BASE + 2 SIDE WALLS", 30, 50, "stage-title");
            AddLayoutText(layout, "TITLE", "FIXTURE U-STAGE TRUE PROJECTION", 30, 42, "projection-title");
            AddLayoutText(layout, "NOTE", "SOURCE Tekla solid edges", 30, 34, "projection-source");
            AddLayoutText(layout, "NOTE", "FIXTURE FACE " + (frame == null ? "<none>" : frame.FixtureFace), 30, 26, "fixture-face");
            AddLayoutText(layout, "NOTE", "MODE VIRTUAL BOX U-STAGE / TOP COVER OMITTED", 30, 18, "u-stage-mode");

            if (result == null || result.Rectangles == 0)
            {
                layout.LayoutStatus = "REVIEW_REQUIRED";
                layout.UnplacedItems.Add("overall-dimensions");
                layout.UnplacedItems.Add("source-part-mark");
                layout.CollisionCount = CountLayoutTextCollisions(layout.Texts);
                return layout;
            }

            var minX = result.MinX;
            var maxX = result.MaxX;
            var minY = result.MinY;
            var maxY = result.MaxY;
            var tick = 4.0;
            var lengthY = maxY + 18.0;
            var widthX = maxX + 18.0;

            AddLayoutLine(layout, "DIMENSION", minX, maxY + 2.0, minX, lengthY + 2.0, "overall-length");
            AddLayoutLine(layout, "DIMENSION", maxX, maxY + 2.0, maxX, lengthY + 2.0, "overall-length");
            AddLayoutLine(layout, "DIMENSION", minX, lengthY, maxX, lengthY, "overall-length");
            AddLayoutLine(layout, "DIMENSION", minX - tick, lengthY - tick, minX + tick, lengthY + tick, "overall-length");
            AddLayoutLine(layout, "DIMENSION", maxX - tick, lengthY - tick, maxX + tick, lengthY + tick, "overall-length");
            AddLayoutText(layout, "DIMENSION", DimensionText(result.ModelLength), (minX + maxX) / 2.0 - 12.0, lengthY + 5.0, "overall-length");

            AddLayoutLine(layout, "DIMENSION", maxX + 2.0, minY, widthX + 2.0, minY, "overall-width");
            AddLayoutLine(layout, "DIMENSION", maxX + 2.0, maxY, widthX + 2.0, maxY, "overall-width");
            AddLayoutLine(layout, "DIMENSION", widthX, minY, widthX, maxY, "overall-width");
            AddLayoutLine(layout, "DIMENSION", widthX - tick, minY - tick, widthX + tick, minY + tick, "overall-width");
            AddLayoutLine(layout, "DIMENSION", widthX - tick, maxY - tick, widthX + tick, maxY + tick, "overall-width");
            AddLayoutText(layout, "DIMENSION", DimensionText(result.ModelWidth), widthX + 5.0, (minY + maxY) / 2.0, "overall-width");

            AddLayoutLine(layout, "LEADER", minX + 25.0, minY + 4.0, minX + 30.0, minY - 15.0, "wall-thickness");
            AddLayoutText(layout, "THICKNESS_CALLOUT", "t=" + DimensionText(result.ModelThickness), minX + 34.0, minY - 18.0, "wall-thickness");

            AddFixtureUStageSourcePartMark(layout, result, sourcePartLabel);
            layout.CollisionCount = CountLayoutTextCollisions(layout.Texts);
            if (layout.CollisionCount > 0 && layout.LayoutStatus == "OK")
            {
                layout.LayoutStatus = "REVIEW_REQUIRED";
            }

            return layout;
        }

        private static int RenderAnnotationLayout(ContainerView sheet, DrawingAnnotationLayout layout, StageDrawResult result)
        {
            if (layout == null)
            {
                return 0;
            }

            var drawResult = result ?? new StageDrawResult();
            var beforeLinesInserted = drawResult.LinesInserted;
            var beforeLinesFailed = drawResult.LinesFailed;
            foreach (var line in layout.Lines)
            {
                InsertLine(sheet, line.X1, line.Y1, line.X2, line.Y2, drawResult);
            }

            var layoutLinesInserted = drawResult.LinesInserted - beforeLinesInserted;
            var layoutLinesFailed = drawResult.LinesFailed - beforeLinesFailed;
            if (layoutLinesFailed > 0 || layoutLinesInserted < layout.Lines.Count)
            {
                MarkAnnotationLayoutReviewRequired(layout, "annotation-lines-render-failed");
            }

            var textInserted = 0;
            foreach (var text in layout.Texts)
            {
                textInserted += InsertText(sheet, text.X, text.Y, text.Text);
            }

            if (textInserted < layout.Texts.Count)
            {
                MarkAnnotationLayoutReviewRequired(layout, "annotation-text-render-failed");
            }

            return textInserted;
        }

        private static void MarkAnnotationLayoutReviewRequired(DrawingAnnotationLayout layout, string unplacedItem)
        {
            if (layout == null)
            {
                return;
            }

            if (!string.IsNullOrWhiteSpace(unplacedItem) && !layout.UnplacedItems.Contains(unplacedItem))
            {
                layout.UnplacedItems.Add(unplacedItem);
            }

            if (layout.LayoutStatus == "OK")
            {
                layout.LayoutStatus = "REVIEW_REQUIRED";
            }
        }

        private static void AddLayoutLine(DrawingAnnotationLayout layout, string kind, double x1, double y1, double x2, double y2, string sourceIntentId)
        {
            if (layout == null)
            {
                return;
            }

            layout.Lines.Add(new DrawingAnnotationLine
            {
                Kind = kind,
                X1 = x1,
                Y1 = y1,
                X2 = x2,
                Y2 = y2,
                SourceIntentId = sourceIntentId,
            });
        }

        private static DrawingAnnotationText AddLayoutText(DrawingAnnotationLayout layout, string kind, string text, double x, double y, string sourceIntentId)
        {
            var value = text ?? "";
            var width = EstimateLayoutTextWidth(value);
            var height = 5.0;
            var item = new DrawingAnnotationText
            {
                Kind = kind,
                Text = value,
                X = x,
                Y = y,
                Left = x,
                Bottom = y,
                Right = x + width,
                Top = y + height,
                SourceIntentId = sourceIntentId,
            };

            if (layout != null)
            {
                layout.Texts.Add(item);
            }

            return item;
        }

        private static int CountLayoutTextCollisions(List<DrawingAnnotationText> texts)
        {
            if (texts == null)
            {
                return 0;
            }

            var collisions = 0;
            for (var index = 0; index < texts.Count; index++)
            {
                for (var otherIndex = index + 1; otherIndex < texts.Count; otherIndex++)
                {
                    if (LayoutTextBoxesOverlap(texts[index], texts[otherIndex]))
                    {
                        collisions += 1;
                    }
                }
            }

            return collisions;
        }

        private static bool LayoutTextBoxesOverlap(DrawingAnnotationText left, DrawingAnnotationText right)
        {
            if (left == null || right == null)
            {
                return false;
            }

            return left.Left < right.Right
                && left.Right > right.Left
                && left.Bottom < right.Top
                && left.Top > right.Bottom;
        }

        private static double EstimateLayoutTextWidth(string text)
        {
            return Math.Max(14.0, (text ?? "").Length * 2.6);
        }

        private static void AddFixtureUStageSourcePartMark(DrawingAnnotationLayout layout, StageDrawResult result, string sourcePartLabel)
        {
            if (layout == null || result == null || result.Rectangles == 0)
            {
                return;
            }

            var value = string.IsNullOrWhiteSpace(sourcePartLabel) ? "<source part>" : sourcePartLabel.Trim();
            var estimatedWidth = EstimateLayoutTextWidth(value);
            var sheetLeftLimit = 18.0;
            var sheetRightLimit = 581.0;
            var sideGap = 16.0;
            var centerX = (result.MinX + result.MaxX) / 2.0;
            var centerY = (result.MinY + result.MaxY) / 2.0;
            var labelY = centerY + 6.0;
            var rightLabelX = result.MaxX + sideGap;

            if (rightLabelX + estimatedWidth <= sheetRightLimit)
            {
                AddLayoutLine(layout, "LEADER", centerX, centerY, rightLabelX - 4.0, labelY + 1.5, "source-part-mark");
                AddLayoutText(layout, "PART_MARK", value, rightLabelX, labelY, "source-part-mark");
                return;
            }

            var leftLabelRight = result.MinX - sideGap;
            var leftLabelX = leftLabelRight - estimatedWidth;
            if (leftLabelX >= sheetLeftLimit)
            {
                AddLayoutLine(layout, "LEADER", centerX, centerY, leftLabelRight + 4.0, labelY + 1.5, "source-part-mark");
                AddLayoutText(layout, "PART_MARK", value, leftLabelX, labelY, "source-part-mark");
                return;
            }

            var topLabelY = result.MaxY + 38.0;
            var topLabelX = Math.Min(sheetRightLimit - estimatedWidth, Math.Max(result.MaxX - estimatedWidth, sheetLeftLimit));
            if (topLabelX >= sheetLeftLimit && topLabelX + estimatedWidth <= sheetRightLimit)
            {
                AddLayoutLine(layout, "LEADER", centerX, centerY, topLabelX - 4.0, topLabelY + 1.5, "source-part-mark");
                AddLayoutText(layout, "PART_MARK", value, topLabelX, topLabelY, "source-part-mark");
                return;
            }

            layout.UnplacedItems.Add("source-part-mark");
            layout.LayoutStatus = "NEEDS_DETAIL_VIEW";
        }

        private static string UStageSourcePartLabel(List<object> drawEvidence)
        {
            foreach (var evidence in drawEvidence ?? new List<object>())
            {
                var sourcePart = ReflectionValue<object>(evidence, "source_part");
                if (sourcePart == null)
                {
                    continue;
                }

                var values = new List<string>();
                var partPosition = SafeText(ReflectionValue<string>(sourcePart, "PartPosition"));
                var profile = SafeText(ReflectionValue<string>(sourcePart, "Profile"));
                var name = SafeText(ReflectionValue<string>(sourcePart, "Name"));
                if (!string.IsNullOrWhiteSpace(partPosition)) values.Add(partPosition);
                if (!string.IsNullOrWhiteSpace(profile)) values.Add(profile);
                if (!string.IsNullOrWhiteSpace(name)) values.Add(name);
                if (values.Count > 0)
                {
                    return string.Join(" / ", values);
                }
            }

            return "<source part>";
        }

        private static bool InsertManualOverallDimensions(ContainerView sheet, StageDrawResult result, out int textInserted)
        {
            textInserted = 0;
            if (result.Rectangles == 0)
            {
                return false;
            }

            var minX = result.MinX;
            var maxX = result.MaxX;
            var minY = result.MinY;
            var maxY = result.MaxY;
            var tick = 4.0;
            var lengthY = maxY + 18.0;
            var widthX = maxX + 18.0;

            InsertLine(sheet, minX, maxY + 2.0, minX, lengthY + 2.0, result);
            InsertLine(sheet, maxX, maxY + 2.0, maxX, lengthY + 2.0, result);
            InsertLine(sheet, minX, lengthY, maxX, lengthY, result);
            InsertLine(sheet, minX - tick, lengthY - tick, minX + tick, lengthY + tick, result);
            InsertLine(sheet, maxX - tick, lengthY - tick, maxX + tick, lengthY + tick, result);
            textInserted += InsertText(sheet, (minX + maxX) / 2.0 - 12.0, lengthY + 5.0, DimensionText(result.ModelLength));

            InsertLine(sheet, maxX + 2.0, minY, widthX + 2.0, minY, result);
            InsertLine(sheet, maxX + 2.0, maxY, widthX + 2.0, maxY, result);
            InsertLine(sheet, widthX, minY, widthX, maxY, result);
            InsertLine(sheet, widthX - tick, minY - tick, widthX + tick, minY + tick, result);
            InsertLine(sheet, widthX - tick, maxY - tick, widthX + tick, maxY + tick, result);
            textInserted += InsertText(sheet, widthX + 5.0, (minY + maxY) / 2.0, DimensionText(result.ModelWidth));
            return true;
        }

        private static string DimensionText(double value)
        {
            if (value <= 0.0)
            {
                return "";
            }

            return Math.Round(value).ToString("0", System.Globalization.CultureInfo.InvariantCulture);
        }

        private static bool InsertProbeOverallDimension(ContainerView sheet, StageDrawResult result)
        {
            if (result.Rectangles == 0)
            {
                return false;
            }

            var points = new PointList();
            points.Add(new Tekla.Structures.Geometry3d.Point(result.MinX, result.MaxY + 12.0, 0));
            points.Add(new Tekla.Structures.Geometry3d.Point(result.MaxX, result.MaxY + 12.0, 0));
            var dimension = new StraightDimensionSetHandler().CreateDimensionSet(
                sheet,
                points,
                new Tekla.Structures.Geometry3d.Vector(0, 1, 0),
                8.0);
            return dimension != null;
        }

        private static bool InsertProbeOverallWidthDimension(ContainerView sheet, StageDrawResult result)
        {
            if (result.Rectangles == 0)
            {
                return false;
            }

            var points = new PointList();
            points.Add(new Tekla.Structures.Geometry3d.Point(result.MaxX + 12.0, result.MinY, 0));
            points.Add(new Tekla.Structures.Geometry3d.Point(result.MaxX + 12.0, result.MaxY, 0));
            var dimension = new StraightDimensionSetHandler().CreateDimensionSet(
                sheet,
                points,
                new Tekla.Structures.Geometry3d.Vector(1, 0, 0),
                8.0);
            return dimension != null;
        }

        private static PrimitiveSheetStats CountPrimitiveSheetStats(Drawing drawing, ContainerView sheet)
        {
            return new PrimitiveSheetStats
            {
                Mark = drawing == null ? "" : SafeText(drawing.Mark),
                Name = drawing == null ? "" : SafeText(drawing.Name),
                Lines = CountDrawingObjects(sheet, typeof(Line)),
                Polylines = CountDrawingObjects(sheet, typeof(Polyline)),
                Texts = CountDrawingObjects(sheet, typeof(Text)),
                StraightDimensions = CountDrawingObjects(sheet, typeof(StraightDimension)),
                StraightDimensionSets = CountDrawingObjects(sheet, typeof(StraightDimensionSet)),
                Parts = CountDrawingObjects(sheet, typeof(Part)),
                Marks = CountDrawingObjects(sheet, typeof(Mark)),
                Views = CountDrawingObjects(sheet, typeof(View)),
            };
        }

        private static PrimitiveSheetStats TryReadPrimitiveDrawingStats(DrawingHandler handler, Drawing drawing, TextWriter output)
        {
            try
            {
                if (!handler.SetActiveDrawing(drawing, true))
                {
                    output.WriteLine("Could not reopen primitive drawing.");
                    return null;
                }

                var active = handler.GetActiveDrawing() ?? drawing;
                var stats = CountPrimitiveSheetStats(active, active.GetSheet());
                handler.CloseActiveDrawing(false);
                return stats;
            }
            catch (Exception ex)
            {
                output.WriteLine("Primitive drawing reopen failed: " + ExceptionText(ex));
                try { handler.CloseActiveDrawing(false); } catch { }
                return null;
            }
        }

        private static string PrimitiveStatsText(PrimitiveSheetStats stats)
        {
            if (stats == null)
            {
                return "<null>";
            }

            return "lines=" + stats.Lines
                + " texts=" + stats.Texts
                + " dims=" + stats.Dimensions
                + " parts=" + stats.Parts
                + " marks=" + stats.Marks
                + " views=" + stats.Views;
        }

        private static List<ViewBase> DrawingViews(ContainerView sheet)
        {
            var result = new List<ViewBase>();
            var views = sheet.GetAllViews();
            while (views.MoveNext())
            {
                var view = views.Current as ViewBase;
                if (view != null)
                {
                    result.Add(view);
                }
            }

            return result;
        }

        private static List<TextCopy> CaptureTexts(ContainerView sheet, List<ViewBase> sourceViews)
        {
            var result = new List<TextCopy>();
            var objects = sheet.GetAllObjects(new[] { typeof(Text) });
            while (objects.MoveNext())
            {
                var text = objects.Current as Text;
                if (text == null)
                {
                    continue;
                }

                result.Add(
                    new TextCopy
                    {
                        ViewIndex = ViewIndexOf(sourceViews, DrawingObjectView(text)),
                        InsertionPoint = CopyPoint(text.InsertionPoint),
                        TextString = text.TextString,
                        Attributes = text.Attributes,
                    });
            }

            return result;
        }

        private static List<StraightDimensionSetCopy> CaptureStraightDimensionSets(ContainerView sheet, List<ViewBase> sourceViews)
        {
            var result = new List<StraightDimensionSetCopy>();
            var objects = sheet.GetAllObjects(new[] { typeof(StraightDimensionSet) });
            while (objects.MoveNext())
            {
                var dimensionSet = objects.Current as StraightDimensionSet;
                if (dimensionSet == null)
                {
                    continue;
                }

                result.Add(
                    new StraightDimensionSetCopy
                    {
                        ViewIndex = ViewIndexOf(sourceViews, DrawingObjectView(dimensionSet)),
                        DimensionPoints = CopyPointList(ReflectionValue<PointList>(dimensionSet, "DimensionPoints")),
                        UpDirection = CopyVector(ReflectionValue<Tekla.Structures.Geometry3d.Vector>(dimensionSet, "UpDirection")),
                        Distance = dimensionSet.Distance,
                        LeftTagLineOffset = dimensionSet.LeftTagLineOffset,
                        RightTagLineOffset = dimensionSet.RightTagLineOffset,
                        Attributes = dimensionSet.Attributes,
                    });
            }

            return result;
        }

        private static ViewBase DrawingObjectView(DrawingObject drawingObject)
        {
            if (drawingObject == null)
            {
                return null;
            }

            try
            {
                return drawingObject.GetView();
            }
            catch
            {
                return null;
            }
        }

        private static int ViewIndexOf(List<ViewBase> views, ViewBase view)
        {
            if (view == null)
            {
                return -1;
            }

            for (var index = 0; index < views.Count; index++)
            {
                if (ReferenceEquals(views[index], view))
                {
                    return index;
                }
            }

            for (var index = 0; index < views.Count; index++)
            {
                if (SameViewGeometry(views[index], view))
                {
                    return index;
                }
            }

            return -1;
        }

        private static bool SameViewGeometry(ViewBase left, ViewBase right)
        {
            if (left == null || right == null)
            {
                return false;
            }

            return SamePoint(left.Origin, right.Origin)
                && SamePoint(left.ExtremaCenter, right.ExtremaCenter)
                && Math.Abs(left.Width - right.Width) < 0.001
                && Math.Abs(left.Height - right.Height) < 0.001;
        }

        private static bool SamePoint(Tekla.Structures.Geometry3d.Point left, Tekla.Structures.Geometry3d.Point right)
        {
            if (left == null || right == null)
            {
                return left == right;
            }

            return Math.Abs(left.X - right.X) < 0.001
                && Math.Abs(left.Y - right.Y) < 0.001
                && Math.Abs(left.Z - right.Z) < 0.001;
        }

        private static T ReflectionValue<T>(object instance, string propertyName)
        {
            if (instance == null)
            {
                return default(T);
            }

            var property = instance.GetType().GetProperty(
                propertyName,
                System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic);
            if (property == null)
            {
                return default(T);
            }

            return (T)property.GetValue(instance, null);
        }

        private static void SetReflectionValue(object instance, string propertyName, object value)
        {
            if (instance == null)
            {
                return;
            }

            var property = instance.GetType().GetProperty(
                propertyName,
                System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic);
            if (property == null)
            {
                return;
            }

            property.SetValue(instance, value, null);
        }

        private static ViewBase ResolveTargetView(ContainerView targetSheet, List<ViewBase> targetViews, int sourceViewIndex)
        {
            if (sourceViewIndex >= 0 && sourceViewIndex < targetViews.Count)
            {
                return targetViews[sourceViewIndex];
            }

            if (targetViews.Count > 0)
            {
                return targetViews[0];
            }

            return targetSheet;
        }

        private static Tekla.Structures.Geometry3d.Point CopyPoint(Tekla.Structures.Geometry3d.Point point)
        {
            if (point == null)
            {
                return null;
            }

            return new Tekla.Structures.Geometry3d.Point(point.X, point.Y, point.Z);
        }

        private static Tekla.Structures.Geometry3d.Vector CopyVector(Tekla.Structures.Geometry3d.Vector vector)
        {
            if (vector == null)
            {
                return null;
            }

            return new Tekla.Structures.Geometry3d.Vector(vector.X, vector.Y, vector.Z);
        }

        private static PointList CopyPointList(PointList points)
        {
            var copy = new PointList();
            if (points == null)
            {
                return copy;
            }

            foreach (Tekla.Structures.Geometry3d.Point point in points)
            {
                copy.Add(CopyPoint(point));
            }

            return copy;
        }

        private static IntList ToIntList(List<string> partIds)
        {
            var result = new IntList();
            if (partIds == null)
            {
                return result;
            }

            foreach (var partId in partIds)
            {
                int value;
                if (int.TryParse(partId, out value))
                {
                    result.Add(value);
                }
            }

            return result;
        }

        private static List<string> OrderAssemblyPartIds(string assemblyId, List<string> drawingPartIds, TextWriter output)
        {
            var ordered = new List<string>();
            var seen = new HashSet<string>();
            var model = new Tekla.Structures.Model.Model();
            if (!model.GetConnectionStatus())
            {
                output.WriteLine("Model API not connected. Falling back to drawing order.");
                return drawingPartIds;
            }

            int id;
            if (!int.TryParse(assemblyId, out id))
            {
                return drawingPartIds;
            }

            var assembly = model.SelectModelObject(new Identifier(id)) as Tekla.Structures.Model.Assembly;
            if (assembly == null)
            {
                output.WriteLine("Assembly " + assemblyId + " was not selectable through Model API. Falling back to drawing order.");
                return drawingPartIds;
            }

            AddPartIfInDrawing(assembly.GetMainPart() as Tekla.Structures.Model.Part, drawingPartIds, ordered, seen);
            AddParts(assembly.GetSecondaries(), drawingPartIds, ordered, seen);
            AddSubAssemblyParts(assembly.GetSubAssemblies(), drawingPartIds, ordered, seen);
            foreach (var partId in drawingPartIds)
            {
                if (seen.Add(partId))
                {
                    ordered.Add(partId);
                }
            }

            output.WriteLine("Ordered assembly part ids: " + ordered.Count);
            return ordered;
        }

        private static void AddSubAssemblyParts(ArrayList subAssemblies, List<string> drawingPartIds, List<string> ordered, HashSet<string> seen)
        {
            if (subAssemblies == null)
            {
                return;
            }

            foreach (var item in subAssemblies)
            {
                var assembly = item as Tekla.Structures.Model.Assembly;
                if (assembly == null)
                {
                    continue;
                }

                AddPartIfInDrawing(assembly.GetMainPart() as Tekla.Structures.Model.Part, drawingPartIds, ordered, seen);
                AddParts(assembly.GetSecondaries(), drawingPartIds, ordered, seen);
                AddSubAssemblyParts(assembly.GetSubAssemblies(), drawingPartIds, ordered, seen);
            }
        }

        private static void AddParts(ArrayList parts, List<string> drawingPartIds, List<string> ordered, HashSet<string> seen)
        {
            if (parts == null)
            {
                return;
            }

            foreach (var item in parts)
            {
                AddPartIfInDrawing(item as Tekla.Structures.Model.Part, drawingPartIds, ordered, seen);
            }
        }

        private static void AddPartIfInDrawing(Tekla.Structures.Model.Part part, List<string> drawingPartIds, List<string> ordered, HashSet<string> seen)
        {
            if (part == null || part.Identifier == null)
            {
                return;
            }

            var partId = part.Identifier.ID.ToString();
            if (drawingPartIds.Contains(partId) && seen.Add(partId))
            {
                ordered.Add(partId);
            }
        }

        private static List<DrawingStep> BuildSimpleProcessSteps(List<string> orderedPartIds, int stepCount)
        {
            var result = new List<DrawingStep>();
            var previous = new HashSet<string>();
            stepCount = Math.Max(1, Math.Min(stepCount, orderedPartIds.Count));
            for (var index = 1; index <= stepCount; index++)
            {
                var visibleCount = (int)Math.Ceiling(orderedPartIds.Count * index / (double)stepCount);
                var visible = orderedPartIds.Take(visibleCount).ToList();
                var current = new HashSet<string>(visible);
                var newlyAdded = visible.Where(partId => !previous.Contains(partId)).ToList();
                result.Add(
                    new DrawingStep
                    {
                        StepNo = index,
                        StepType = "TEKLA_NATIVE_HIDE_STEP_" + index,
                        VisiblePartIds = visible,
                        NewPartIds = newlyAdded,
                    }
                );
                previous = current;
            }

            return result;
        }

        private static HashSet<int> ExistingSheetNumbers(DrawingHandler handler, string modelId)
        {
            var result = new HashSet<int>();
            var drawings = handler.GetDrawings();
            while (drawings.MoveNext())
            {
                var drawing = drawings.Current as AssemblyDrawing;
                if (drawing != null && DrawingModelIdentifier(drawing) == modelId)
                {
                    result.Add(drawing.SheetNumber);
                }
            }

            return result;
        }

        private static int NextAvailableSheetNumber(HashSet<int> existingSheets, int start)
        {
            var sheet = start;
            while (existingSheets.Contains(sheet))
            {
                sheet += 1;
            }

            return sheet;
        }

        private static void ApplyVisibilityOnly(ContainerView sheet, List<string> visiblePartIds, bool hideWholeDrawing, out int matched, out int hidden)
        {
            matched = 0;
            hidden = 0;
            var visible = new HashSet<string>(visiblePartIds);
            var objects = sheet.GetAllObjects(new[] { typeof(Part) });
            while (objects.MoveNext())
            {
                var part = objects.Current as Part;
                if (part == null || part.ModelIdentifier == null)
                {
                    continue;
                }

                var modelId = part.ModelIdentifier.ID.ToString();
                if (visible.Contains(modelId))
                {
                    if (hideWholeDrawing)
                    {
                        part.Hideable.ShowInDrawing();
                    }
                    else
                    {
                        part.Hideable.ShowInDrawingView();
                    }
                    matched += 1;
                }
                else
                {
                    if (hideWholeDrawing)
                    {
                        part.Hideable.HideFromDrawing();
                    }
                    else
                    {
                        part.Hideable.HideFromDrawingView();
                    }
                    hidden += 1;
                }
            }
        }

        private static void DeleteExtraDrawingParts(ContainerView sheet, List<string> visiblePartIds, out int kept, out int deleted, out int failed)
        {
            kept = 0;
            deleted = 0;
            failed = 0;
            var visible = new HashSet<string>(visiblePartIds ?? new List<string>());
            var toDelete = new List<Part>();
            var objects = sheet.GetAllObjects(new[] { typeof(Part) });
            while (objects.MoveNext())
            {
                var part = objects.Current as Part;
                if (part == null || part.ModelIdentifier == null)
                {
                    continue;
                }

                var modelId = part.ModelIdentifier.ID.ToString();
                if (visible.Contains(modelId))
                {
                    kept += 1;
                }
                else
                {
                    toDelete.Add(part);
                }
            }

            foreach (var part in toDelete)
            {
                try
                {
                    if (part.Delete())
                    {
                        deleted += 1;
                    }
                    else
                    {
                        failed += 1;
                    }
                }
                catch
                {
                    failed += 1;
                }
            }
        }

        private static string SafeText(string value)
        {
            return string.IsNullOrWhiteSpace(value) ? "" : value.Replace("\r", " ").Replace("\n", " ").Trim();
        }

        private static string ExceptionText(Exception ex)
        {
            if (ex == null)
            {
                return "";
            }

            var message = ex.Message;
            if (string.IsNullOrWhiteSpace(message))
            {
                message = ex.GetType().FullName;
            }

            return ex.GetType().FullName + ": " + message;
        }

        private static string ModelObjectSummary(Tekla.Structures.Model.ModelObject modelObject)
        {
            var part = modelObject as Tekla.Structures.Model.Part;
            if (part != null)
            {
                var assembly = part.GetAssembly();
                var assemblyId = assembly != null && assembly.Identifier != null ? assembly.Identifier.ID.ToString() : "";
                return string.Join(
                    " | ",
                    new[]
                    {
                        "Part",
                        "id=" + modelObject.Identifier.ID,
                        "assemblyId=" + assemblyId,
                        "partPos=" + ReportText(modelObject, "PART_POS"),
                        "assemblyPos=" + ReportText(modelObject, "ASSEMBLY_POS"),
                        "name=" + ReportText(modelObject, "NAME"),
                        "profile=" + ReportText(modelObject, "PROFILE"),
                        "guid=" + ReportText(modelObject, "GUID"),
                    }
                );
            }

            var assemblyObject = modelObject as Tekla.Structures.Model.Assembly;
            if (assemblyObject != null)
            {
                var mainPart = assemblyObject.GetMainPart() as Tekla.Structures.Model.Part;
                return string.Join(
                    " | ",
                    new[]
                    {
                        "Assembly",
                        "id=" + modelObject.Identifier.ID,
                        "mainPartId=" + (mainPart != null && mainPart.Identifier != null ? mainPart.Identifier.ID.ToString() : ""),
                        "assemblyPos=" + ReportText(modelObject, "ASSEMBLY_POS"),
                        "name=" + ReportText(modelObject, "NAME"),
                        "guid=" + ReportText(modelObject, "GUID"),
                    }
                );
            }

            return modelObject.GetType().Name + " | id=" + modelObject.Identifier.ID + " | guid=" + ReportText(modelObject, "GUID");
        }

        private static string ReportText(Tekla.Structures.Model.ModelObject modelObject, string propertyName)
        {
            var value = "";
            return modelObject.GetReportProperty(propertyName, ref value) ? SafeText(value) : "";
        }

        private static List<Identifier> ResolveDrawingAssemblyIdentifiers(StepPayload payload, DrawingStep step, TextWriter output)
        {
            var identifiers = new List<Identifier>();
            int assemblyId;
            if (int.TryParse(payload.AssemblyId, out assemblyId))
            {
                identifiers.Add(new Identifier(assemblyId));
            }

            Identifier resolvedIdentifier;
            string message;
            if (TryResolveAssemblyIdentifierFromParts(step.VisiblePartIds.Concat(step.NewPartIds), out resolvedIdentifier, out message))
            {
                output.WriteLine(message);
                if (identifiers.All(identifier => identifier.ID != resolvedIdentifier.ID))
                {
                    identifiers.Add(resolvedIdentifier);
                }
            }
            else if (!string.IsNullOrWhiteSpace(message))
            {
                output.WriteLine(message);
            }

            return identifiers;
        }

        private static bool TryResolveAssemblyIdentifierFromParts(IEnumerable<string> partIds, out Identifier assemblyIdentifier, out string message)
        {
            assemblyIdentifier = null;
            message = "";

            var model = new Tekla.Structures.Model.Model();
            if (!model.GetConnectionStatus())
            {
                message = "Model API was not connected while resolving drawing assembly identifier from part ids.";
                return false;
            }

            foreach (var partIdText in partIds)
            {
                int partId;
                if (!int.TryParse(partIdText, out partId))
                {
                    continue;
                }

                var modelObject = model.SelectModelObject(new Identifier(partId));
                var part = modelObject as Tekla.Structures.Model.Part;
                if (part == null)
                {
                    continue;
                }

                var assembly = part.GetAssembly();
                if (assembly == null || assembly.Identifier == null)
                {
                    continue;
                }

                assemblyIdentifier = assembly.Identifier;
                message = "Resolved drawing assembly identifier " + assemblyIdentifier.ID + " from part " + partId + ".";
                return true;
            }

            message = "Could not resolve drawing assembly identifier from step part ids.";
            return false;
        }

        private static Drawing OpenOrCreateAssemblyDrawing(DrawingHandler handler, Identifier assemblyIdentifier, TextWriter output)
        {
            output.WriteLine("Creating assembly drawing for assembly identifier " + assemblyIdentifier.ID + ".");
            var assemblyDrawing = new AssemblyDrawing(assemblyIdentifier);
            if (!assemblyDrawing.Insert())
            {
                output.WriteLine("AssemblyDrawing.Insert() returned false for assembly identifier " + assemblyIdentifier.ID + ".");
                if (!TryCreateDrawingWithAutoDrawingRule(assemblyIdentifier, output))
                {
                    return null;
                }

                assemblyDrawing = new AssemblyDrawing(assemblyIdentifier);
                output.WriteLine("AssemblyDrawing.Select() after AutoDrawing returned " + assemblyDrawing.Select() + ".");
            }

            if (!handler.SetActiveDrawing(assemblyDrawing, true))
            {
                output.WriteLine("Drawing was created or already present, but SetActiveDrawing returned false for assembly identifier " + assemblyIdentifier.ID + ".");
                return TryOpenSelectedAssemblyDrawingViaTeklaUi(handler, assemblyIdentifier, output);
            }

            return handler.GetActiveDrawing() ?? assemblyDrawing;
        }

        private static bool TryCreateDrawingWithAutoDrawingRule(Identifier assemblyIdentifier, TextWriter output)
        {
            foreach (var ruleName in AutoDrawingRuleCandidates())
            {
                AutoDrawingsStatusEnum status;
                output.WriteLine("Trying AutoDrawing rule " + ruleName + " for assembly identifier " + assemblyIdentifier.ID + ".");
                try
                {
                    var ok = DrawingCreator.CreateDrawings(new AutoDrawingRule(ruleName), assemblyIdentifier, out status);
                    output.WriteLine("AutoDrawing result rule=" + ruleName + " ok=" + ok + " status=" + status);
                    if (ok && status == AutoDrawingsStatusEnum.OPERATION_OK)
                    {
                        return true;
                    }
                }
                catch (Exception ex)
                {
                    output.WriteLine("AutoDrawing rule " + ruleName + " failed: " + ex.Message);
                }
            }

            return false;
        }

        private static IEnumerable<string> AutoDrawingRuleCandidates()
        {
            yield return "ch_column";
            yield return "ch_column.xdproc";
            yield return @"D:\Program Files\Tekla Structures\2017\Environments\china\system\ch_column.xdproc";
            yield return "Tekla Drawing Wizard - Column";
            yield return "Tekla Drawing Wizard - Column.xdproc";
        }

        private static Drawing TryOpenSelectedAssemblyDrawingViaTeklaUi(DrawingHandler handler, Identifier assemblyIdentifier, TextWriter output)
        {
            output.WriteLine("Trying Tekla UI drawing list route for assembly identifier " + assemblyIdentifier.ID + ".");
            if (!SelectAssemblyMainPartInModel(assemblyIdentifier, output))
            {
                return null;
            }

            if (!RunMacroAndWait(@"FabricationInspectionDrawings\OpenDrawingList.cs", output))
            {
                return null;
            }

            if (!RunMacroAndWait(@"FabricationInspectionDrawings\SelectAssemblyDrawing.cs", output))
            {
                return null;
            }

            var selectedDrawings = handler.GetDrawingSelector().GetSelected();
            while (selectedDrawings.MoveNext())
            {
                var drawing = selectedDrawings.Current;
                if (drawing == null)
                {
                    continue;
                }

                output.WriteLine("Trying selected drawing mark=" + drawing.Mark + " title1=" + drawing.Title1 + ".");
                if (handler.SetActiveDrawing(drawing, true))
                {
                    return handler.GetActiveDrawing() ?? drawing;
                }
            }

            output.WriteLine("No selected drawing could be opened from Drawing List.");
            return null;
        }

        private static bool SelectAssemblyMainPartInModel(Identifier assemblyIdentifier, TextWriter output)
        {
            var model = new Tekla.Structures.Model.Model();
            if (!model.GetConnectionStatus())
            {
                output.WriteLine("Model API was not connected while selecting assembly main part.");
                return false;
            }

            var modelObject = model.SelectModelObject(assemblyIdentifier);
            var assembly = modelObject as Tekla.Structures.Model.Assembly;
            if (assembly == null)
            {
                output.WriteLine("Model object " + assemblyIdentifier.ID + " is not a model Assembly.");
                return false;
            }

            var mainPart = assembly.GetMainPart();
            if (mainPart == null)
            {
                output.WriteLine("Assembly " + assemblyIdentifier.ID + " has no main part.");
                return false;
            }

            var selected = new ArrayList { mainPart };
            var selector = new Tekla.Structures.Model.UI.ModelObjectSelector();
            var ok = selector.Select(selected, true);
            output.WriteLine("ModelObjectSelector.Select(mainPart) returned " + ok + ".");
            return ok;
        }

        private static bool RunMacroAndWait(string macroName, TextWriter output)
        {
            output.WriteLine("Running Tekla macro " + macroName + ".");
            try
            {
                if (!Operation.RunMacro(macroName))
                {
                    output.WriteLine("Operation.RunMacro returned false for " + macroName + ".");
                    return false;
                }
            }
            catch (Exception ex)
            {
                output.WriteLine("Operation.RunMacro failed for " + macroName + ": " + ex.Message);
                return false;
            }

            for (var index = 0; index < 100; index++)
            {
                if (!Operation.IsMacroRunning())
                {
                    return true;
                }
                Thread.Sleep(100);
            }

            output.WriteLine("Timed out waiting for macro " + macroName + ".");
            return false;
        }

        private static string EnsureDrawingFilterOptionMacro(int option)
        {
            var relativeName = @"FabricationInspectionDrawings\CodexSelectDrawingFilterOption" + option + ".cs";
            var macroDirectory = @"D:\Program Files\Tekla Structures\2017\environments\common\macros\modeling\FabricationInspectionDrawings";
            Directory.CreateDirectory(macroDirectory);
            var path = Path.Combine(macroDirectory, "CodexSelectDrawingFilterOption" + option + ".cs");
            var text =
                "// Generated for Codex Tekla drawing filter probing.\r\n\r\n"
                + "namespace Tekla.Technology.Akit.UserScript\r\n"
                + "{\r\n"
                + "    public class Script\r\n"
                + "    {\r\n"
                + "        public static void Run(Tekla.Technology.Akit.IScript akit)\r\n"
                + "        {\r\n"
                + "            akit.ValueChange(\"Drawing_selection\", \"diaSavedSearchOptionMenu\", \"" + option + "\");\r\n"
                + "            akit.PushButton(\"dia_draw_filter_by_parts\", \"Drawing_selection\");\r\n"
                + "            akit.TableSelect(\"Drawing_selection\", \"dia_draw_select_list\", 1);\r\n"
                + "        }\r\n"
                + "    }\r\n"
                + "}\r\n";
            File.WriteAllText(path, text);
            return relativeName;
        }
    }

    internal static class TeklaMacroLauncher
    {
        public static int Run(Options options)
        {
            var assemblyPath = typeof(Program).Assembly.Location;
            var configPath = Path.Combine(Path.GetTempPath(), "BoxProgressiveDrawingPoc.macro.config");
            File.WriteAllLines(
                configPath,
                new[]
                {
                    "assemblyPath=" + assemblyPath,
                    "stepsPath=" + Path.GetFullPath(options.StepsPath),
                    "stepNumber=" + options.StepNumber,
                    "createDrawing=" + options.CreateDrawing,
                }
            );

            var model = new Tekla.Structures.Model.Model();
            if (!model.GetConnectionStatus())
            {
                Console.Error.WriteLine("Tekla Model API is not connected. Open Tekla Structures 2017 and the model, then rerun.");
                return 20;
            }

            Console.WriteLine("Macro config: " + configPath);
            Console.WriteLine("Macro log: " + Path.Combine(Path.GetTempPath(), "BoxProgressiveDrawingPoc.macro.log"));
            if (!Operation.RunMacro("BoxProgressiveDrawingPocMacro.cs"))
            {
                Console.Error.WriteLine("Operation.RunMacro returned false for BoxProgressiveDrawingPocMacro.cs.");
                return 21;
            }

            Console.WriteLine("Macro started. Check the Tekla UI and macro log for drawing results.");
            return 0;
        }
    }

    public sealed class Options
    {
        public string StepsPath { get; private set; }
        public int StepNumber { get; private set; }
        public bool DryRun { get; private set; }
        public bool CreateDrawing { get; private set; }
        public bool RunMacro { get; private set; }
        public bool ListDrawings { get; private set; }
        public bool SelectedModel { get; private set; }
        public bool CloseActiveDrawing { get; private set; }
        public string InspectDrawingModelId { get; private set; }
        public string GenerateProcessDrawingsModelId { get; private set; }
        public string InspectProcessSheetsModelId { get; private set; }
        public string ProbeNativeProcessDrawingModelId { get; private set; }
        public string ProbeCloneDrawingModelId { get; private set; }
        public string ProbeDrawingFilterOptionsModelId { get; private set; }
        public string ProbeCopyAnnotationsModelId { get; private set; }
        public string ProbePrunePartsModelId { get; private set; }
        public string ProbeRestrictViewPartsModelId { get; private set; }
        public string ProbeRelatedObjectsModelId { get; private set; }
        public string ProbeGaStageModelId { get; private set; }
        public string ProbeGaFixtureProjectionModelId { get; private set; }
        public string ProbeGaFixtureUStageModelId { get; private set; }
        public int SourceSheetNumber { get; private set; } = 0;
        public int TargetSheetNumber { get; private set; } = 1;
        public string DeleteDrawingModelId { get; private set; }
        public int DeleteSheetNumber { get; private set; } = -1;
        public string OpenCloseDrawingModelId { get; private set; }
        public int DrawingSheetNumber { get; private set; } = -1;
        public string OutputDirectory { get; private set; }

        public static Options Parse(string[] args)
        {
            var options = new Options { StepNumber = 1 };
            for (var index = 0; index < args.Length; index++)
            {
                var arg = args[index];
                if (arg == "--steps" && index + 1 < args.Length)
                {
                    options.StepsPath = args[++index];
                }
                else if (arg == "--step" && index + 1 < args.Length)
                {
                    int value;
                    if (int.TryParse(args[++index], out value))
                    {
                        options.StepNumber = value;
                    }
                }
                else if (arg == "--dry-run")
                {
                    options.DryRun = true;
                }
                else if (arg == "--create-drawing")
                {
                    options.CreateDrawing = true;
                }
                else if (arg == "--run-macro")
                {
                    options.RunMacro = true;
                }
                else if (arg == "--list-drawings")
                {
                    options.ListDrawings = true;
                }
                else if (arg == "--selected-model")
                {
                    options.SelectedModel = true;
                }
                else if (arg == "--close-active-drawing")
                {
                    options.CloseActiveDrawing = true;
                }
                else if (arg == "--inspect-drawing-model-id" && index + 1 < args.Length)
                {
                    options.InspectDrawingModelId = args[++index];
                }
                else if (arg == "--generate-process-drawings-model-id" && index + 1 < args.Length)
                {
                    options.GenerateProcessDrawingsModelId = args[++index];
                }
                else if (arg == "--inspect-process-sheets-model-id" && index + 1 < args.Length)
                {
                    options.InspectProcessSheetsModelId = args[++index];
                }
                else if (arg == "--probe-native-process-drawing-model-id" && index + 1 < args.Length)
                {
                    options.ProbeNativeProcessDrawingModelId = args[++index];
                }
                else if (arg == "--probe-clone-drawing-model-id" && index + 1 < args.Length)
                {
                    options.ProbeCloneDrawingModelId = args[++index];
                }
                else if (arg == "--probe-drawing-filter-options-model-id" && index + 1 < args.Length)
                {
                    options.ProbeDrawingFilterOptionsModelId = args[++index];
                }
                else if (arg == "--probe-copy-annotations-model-id" && index + 1 < args.Length)
                {
                    options.ProbeCopyAnnotationsModelId = args[++index];
                }
                else if (arg == "--probe-prune-parts-model-id" && index + 1 < args.Length)
                {
                    options.ProbePrunePartsModelId = args[++index];
                }
                else if (arg == "--probe-restrict-view-parts-model-id" && index + 1 < args.Length)
                {
                    options.ProbeRestrictViewPartsModelId = args[++index];
                }
                else if (arg == "--probe-related-objects-model-id" && index + 1 < args.Length)
                {
                    options.ProbeRelatedObjectsModelId = args[++index];
                }
                else if (arg == "--probe-ga-stage-model-id" && index + 1 < args.Length)
                {
                    options.ProbeGaStageModelId = args[++index];
                }
                else if (arg == "--probe-ga-fixture-projection-model-id" && index + 1 < args.Length)
                {
                    options.ProbeGaFixtureProjectionModelId = args[++index];
                }
                else if (arg == "--probe-ga-fixture-u-stage-model-id" && index + 1 < args.Length)
                {
                    options.ProbeGaFixtureUStageModelId = args[++index];
                }
                else if (arg == "--source-sheet" && index + 1 < args.Length)
                {
                    int value;
                    if (int.TryParse(args[++index], out value))
                    {
                        options.SourceSheetNumber = value;
                    }
                }
                else if (arg == "--target-sheet" && index + 1 < args.Length)
                {
                    int value;
                    if (int.TryParse(args[++index], out value))
                    {
                        options.TargetSheetNumber = value;
                    }
                }
                else if (arg == "--delete-drawing-model-id" && index + 1 < args.Length)
                {
                    options.DeleteDrawingModelId = args[++index];
                }
                else if (arg == "--delete-sheet" && index + 1 < args.Length)
                {
                    int value;
                    if (int.TryParse(args[++index], out value))
                    {
                        options.DeleteSheetNumber = value;
                    }
                }
                else if (arg == "--open-close-drawing-model-id" && index + 1 < args.Length)
                {
                    options.OpenCloseDrawingModelId = args[++index];
                }
                else if (arg == "--drawing-sheet" && index + 1 < args.Length)
                {
                    int value;
                    if (int.TryParse(args[++index], out value))
                    {
                        options.DrawingSheetNumber = value;
                    }
                }
                else if (arg == "--out" && index + 1 < args.Length)
                {
                    options.OutputDirectory = args[++index];
                }
            }
            return options;
        }

        public static Options LoadConfig(string path)
        {
            var options = new Options { StepNumber = 1 };
            foreach (var line in File.ReadAllLines(path))
            {
                var index = line.IndexOf('=');
                if (index <= 0)
                {
                    continue;
                }
                var key = line.Substring(0, index).Trim();
                var value = line.Substring(index + 1).Trim();
                if (key == "stepsPath")
                {
                    options.StepsPath = value;
                }
                else if (key == "stepNumber")
                {
                    int parsed;
                    if (int.TryParse(value, out parsed))
                    {
                        options.StepNumber = parsed;
                    }
                }
                else if (key == "createDrawing")
                {
                    bool parsed;
                    options.CreateDrawing = bool.TryParse(value, out parsed) && parsed;
                }
            }
            return options;
        }
    }

    public sealed class StepPayload
    {
        public string AssemblyId { get; private set; }
        public string MemberId { get; private set; }
        public List<DrawingStep> Steps { get; private set; }

        public static StepPayload Load(string path)
        {
            var serializer = new JavaScriptSerializer();
            var root = serializer.DeserializeObject(File.ReadAllText(path)) as Dictionary<string, object>;
            if (root == null)
            {
                throw new InvalidDataException("Root JSON object is missing.");
            }

            var payload = new StepPayload
            {
                AssemblyId = Value(root, "assembly_id"),
                MemberId = Value(root, "member_id"),
                Steps = new List<DrawingStep>(),
            };

            var rawSteps = root.ContainsKey("steps") ? root["steps"] as IEnumerable : null;
            if (rawSteps == null)
            {
                return payload;
            }

            foreach (var item in rawSteps)
            {
                var step = item as Dictionary<string, object>;
                if (step == null)
                {
                    continue;
                }
                payload.Steps.Add(
                    new DrawingStep
                    {
                        StepNo = IntValue(step, "step_no"),
                        StepType = Value(step, "step_type"),
                        VisiblePartIds = StringList(step, "visible_part_ids"),
                        NewPartIds = StringList(step, "new_part_ids"),
                    }
                );
            }

            return payload;
        }

        public DrawingStep StepByNumber(int stepNumber)
        {
            return Steps.FirstOrDefault(step => step.StepNo == stepNumber);
        }

        private static string Value(Dictionary<string, object> row, string key)
        {
            return row.ContainsKey(key) && row[key] != null ? row[key].ToString() : "";
        }

        private static int IntValue(Dictionary<string, object> row, string key)
        {
            int value;
            return int.TryParse(Value(row, key), out value) ? value : 0;
        }

        private static List<string> StringList(Dictionary<string, object> row, string key)
        {
            var result = new List<string>();
            var values = row.ContainsKey(key) ? row[key] as IEnumerable : null;
            if (values == null)
            {
                return result;
            }
            foreach (var value in values)
            {
                if (value != null && !string.IsNullOrWhiteSpace(value.ToString()))
                {
                    result.Add(value.ToString());
                }
            }
            return result;
        }
    }

    public sealed class DrawingStep
    {
        public int StepNo { get; set; }
        public string StepType { get; set; }
        public List<string> VisiblePartIds { get; set; }
        public List<string> NewPartIds { get; set; }
    }

    internal sealed class TextCopy
    {
        public int ViewIndex { get; set; }
        public Tekla.Structures.Geometry3d.Point InsertionPoint { get; set; }
        public string TextString { get; set; }
        public Text.TextAttributes Attributes { get; set; }
    }

    internal sealed class StraightDimensionSetCopy
    {
        public int ViewIndex { get; set; }
        public PointList DimensionPoints { get; set; }
        public Tekla.Structures.Geometry3d.Vector UpDirection { get; set; }
        public double Distance { get; set; }
        public double LeftTagLineOffset { get; set; }
        public double RightTagLineOffset { get; set; }
        public StraightDimensionSet.StraightDimensionSetAttributes Attributes { get; set; }
    }

    internal sealed class ModelPartBox
    {
        public string PartId { get; set; }
        public string Name { get; set; }
        public string Profile { get; set; }
        public string Material { get; set; }
        public string PartPosition { get; set; }
        public string AssemblyPosition { get; set; }
        public Tekla.Structures.Geometry3d.Point Min { get; set; }
        public Tekla.Structures.Geometry3d.Point Max { get; set; }
    }

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

    internal sealed class FixturePartSnapshot
    {
        public string PartId { get; set; }
        public string Name { get; set; }
        public string Profile { get; set; }
        public string Material { get; set; }
        public string PartPosition { get; set; }
        public string AssemblyPosition { get; set; }
        public double AxisMin { get; set; }
        public double AxisMax { get; set; }
        public double WidthMin { get; set; }
        public double WidthMax { get; set; }
        public double HeightMin { get; set; }
        public double HeightMax { get; set; }
        public double AxisSpan { get; set; }
        public double WidthSpan { get; set; }
        public double HeightSpan { get; set; }
        public double AxisCenter { get; set; }
        public double WidthCenter { get; set; }
        public double HeightCenter { get; set; }
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
    internal sealed class StageDrawResult
    {
        public int Rectangles { get; set; }
        public int LinesInserted { get; set; }
        public int LinesFailed { get; set; }
        public double MinX { get; set; }
        public double MaxX { get; set; }
        public double MinY { get; set; }
        public double MaxY { get; set; }
        public double ModelLength { get; set; }
        public double ModelWidth { get; set; }
        public double ModelThickness { get; set; }
    }

    internal sealed class DrawingAnnotationLayout
    {
        public string LayoutStatus { get; set; } = "OK";
        public int CollisionCount { get; set; }
        public List<DrawingAnnotationLine> Lines { get; set; } = new List<DrawingAnnotationLine>();
        public List<DrawingAnnotationText> Texts { get; set; } = new List<DrawingAnnotationText>();
        public List<string> UnplacedItems { get; set; } = new List<string>();
    }

    internal sealed class DrawingAnnotationLine
    {
        public string Kind { get; set; }
        public double X1 { get; set; }
        public double Y1 { get; set; }
        public double X2 { get; set; }
        public double Y2 { get; set; }
        public string SourceIntentId { get; set; }
    }

    internal sealed class DrawingAnnotationText
    {
        public string Kind { get; set; }
        public string Text { get; set; }
        public double X { get; set; }
        public double Y { get; set; }
        public double Left { get; set; }
        public double Bottom { get; set; }
        public double Right { get; set; }
        public double Top { get; set; }
        public string SourceIntentId { get; set; }
    }

    public sealed class PrimitiveSheetStats
    {
        public string Mark { get; set; }
        public string Name { get; set; }
        public int Lines { get; set; }
        public int Polylines { get; set; }
        public int Texts { get; set; }
        public int StraightDimensions { get; set; }
        public int StraightDimensionSets { get; set; }
        public int Parts { get; set; }
        public int Marks { get; set; }
        public int Views { get; set; }

        public int Dimensions
        {
            get { return StraightDimensions + StraightDimensionSets; }
        }
    }

    public sealed class SheetStats
    {
        public int Sheet { get; set; }
        public string Mark { get; set; }
        public string Name { get; set; }
        public string Title1 { get; set; }
        public int Parts { get; set; }
        public int VisibleParts { get; set; }
        public int HiddenParts { get; set; }
        public int UniquePartIds { get; set; }
        public int Marks { get; set; }
        public int MarkSets { get; set; }
        public int StraightDimensions { get; set; }
        public int StraightDimensionSets { get; set; }
        public int AngleDimensions { get; set; }
        public int RadiusDimensions { get; set; }
        public int CurvedDimensions { get; set; }
        public int Texts { get; set; }
        public int Welds { get; set; }
        public int WeldMarks { get; set; }
        public int Bolts { get; set; }
        public int SectionMarks { get; set; }
        public int Views { get; set; }

        public int Dimensions
        {
            get { return StraightDimensions + StraightDimensionSets + AngleDimensions + RadiusDimensions + CurvedDimensions; }
        }
    }
}
