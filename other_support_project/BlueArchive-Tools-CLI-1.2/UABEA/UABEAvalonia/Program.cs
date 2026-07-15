using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;

namespace UABEAvalonia
{
    public class Program
    {
        //https://stackoverflow.com/a/37146916
        [DllImport("kernel32.dll", SetLastError = true)]
        static extern bool AttachConsole(int dwProcessId);

        // Initialization code. Don't use any Avalonia, third-party APIs or any
        // SynchronizationContext-reliant code before AppMain is called: things aren't initialized
        // yet and stuff might break.
        [STAThread]
        public static void Main(string[] args)
        {
            bool usesConsole = false;
            if (Environment.OSVersion.Platform == PlatformID.Win32NT)
            {
                usesConsole = AttachConsole(-1);

                if (usesConsole)
                {
                    (int Left, int Top) = Console.GetCursorPosition();
                    Console.SetCursorPosition(0, Top);
                    Console.Write(new string(' ', Left));
                    Console.SetCursorPosition(0, Top);
                }
            }
            else if (Environment.OSVersion.Platform == PlatformID.Unix)
            {
                //outputs fine to console already with dotnet in my testing
                usesConsole = true;
            }

            AppDomain currentDomain = AppDomain.CurrentDomain;
            currentDomain.UnhandledException += new UnhandledExceptionEventHandler(UABEAExceptionHandler);

            if (args.Length > 0)
            {
                CommandLineHandler.CLHMain(args);
            }
            else
            {
                bool isHeadless = Environment.GetEnvironmentVariable("DISPLAY") == null && Environment.GetEnvironmentVariable("WAYLAND_DISPLAY") == null;
                if (usesConsole && isHeadless)
                {
                    CommandLineHandler.PrintHelp();
                    return;
                }
                
                try
                {
                    BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
                }
                catch (Exception ex)
                {
                    if (usesConsole)
                    {
                        Console.WriteLine("Failed to launch GUI (X11/Wayland display not found or invalid).");
                        Console.WriteLine("If you intended to use the CLI, please provide arguments.");
                         Console.WriteLine();
                        CommandLineHandler.PrintHelp();
                    }
                    else
                    {
                        throw; 
                    }
                }
            }
        }

        public static void UABEAExceptionHandler(object sender, UnhandledExceptionEventArgs args)
        {
            if (args.ExceptionObject is Exception ex)
            {
                File.WriteAllText("uabeacrash.log", ex.ToString());
                if (Environment.OSVersion.Platform == PlatformID.Win32NT)
                {
                    // can't trust the process to be stable enough
                    // to even show an avalonia messagebox, do hacky
                    // vbscript instead
                    string mshtaArgs = "vbscript:Execute(\"CreateObject(\"\"WScript.Shell\"\").Popup CreateObject(\"\"Scripting.FileSystemObject\"\").OpenTextFile(\"\"uabeacrash.log\"\", 1).ReadAll,,\"\"uabea crash exception (please report this crash with uabeacrash.log)\"\" :close\")";
                    Process.Start(new ProcessStartInfo("mshta", mshtaArgs));
                }
                else
                {
                    Console.WriteLine("uabea crash exception (please report this crash with uabeacrash.log)");
                    Console.WriteLine(ex.ToString());
                }
            }
        }

        // Avalonia configuration, don't remove; also used by visual designer.
        public static AppBuilder BuildAvaloniaApp()
            => AppBuilder.Configure<App>()
                .UsePlatformDetect()
                .LogToTrace();
    }
}
