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
            if (string.IsNullOrWhiteSpace(options.StepsPath))
            {
                Console.Error.WriteLine("Usage: BoxProgressiveDrawingPoc --steps <steps.json> [--step 1] [--dry-run] [--create-drawing] [--run-macro]");
                return 2;
            }

            EnsureTeklaSessionName();

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
}
