using System;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

namespace Tekla.Technology.Akit.UserScript
{
    public class Script
    {
        public static void Run(Tekla.Technology.Akit.IScript akit)
        {
            string configPath = Path.Combine(Path.GetTempPath(), "BoxProgressiveDrawingPoc.macro.config");
            string logPath = Path.Combine(Path.GetTempPath(), "BoxProgressiveDrawingPoc.macro.log");

            try
            {
                File.AppendAllText(logPath, "[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "] Macro shim start\r\n");

                if (!File.Exists(configPath))
                {
                    MessageBox.Show("未找到宏配置文件: " + configPath, "BOX progressive drawing POC", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }

                string assemblyPath = ReadConfigValue(configPath, "assemblyPath");
                if (string.IsNullOrWhiteSpace(assemblyPath) || !File.Exists(assemblyPath))
                {
                    MessageBox.Show("未找到 POC 程序集: " + assemblyPath, "BOX progressive drawing POC", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }

                Assembly assembly = Assembly.LoadFrom(assemblyPath);
                Type entryType = assembly.GetType("ZijinhuaTekla.ProgressiveDrawingPoc.MacroEntry", true);
                MethodInfo runMethod = entryType.GetMethod("Run", BindingFlags.Public | BindingFlags.Static);
                int exitCode = (int)runMethod.Invoke(null, new object[] { configPath });

                File.AppendAllText(logPath, "MacroEntry exitCode=" + exitCode + "\r\n");
                MessageBox.Show("BOX 渐进式构件图 POC 已执行，结果日志: " + logPath, "BOX progressive drawing POC", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (Exception ex)
            {
                try
                {
                    File.AppendAllText(logPath, ex.ToString() + "\r\n");
                }
                catch
                {
                }
                MessageBox.Show(ex.ToString(), "BOX progressive drawing POC", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private static string ReadConfigValue(string path, string key)
        {
            foreach (string line in File.ReadAllLines(path))
            {
                int index = line.IndexOf('=');
                if (index <= 0)
                {
                    continue;
                }

                if (string.Equals(line.Substring(0, index).Trim(), key, StringComparison.OrdinalIgnoreCase))
                {
                    return line.Substring(index + 1).Trim();
                }
            }

            return "";
        }
    }
}
