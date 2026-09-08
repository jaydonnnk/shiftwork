using System.Diagnostics;
using Windows.Graphics.Capture;
using Windows.Graphics.DirectX;
using Windows.Graphics.DirectX.Direct3D11;
using Windows.Security.Authorization.AppCapabilityAccess;

namespace CaptureHarness;

/// <summary>
/// Six probes. Each asks Windows one question and writes down the answer.
/// Nothing here ships. The deliverable is harness-log.txt.
/// </summary>
internal static class Program
{
    private static readonly string LogPath =
        Path.Combine(AppContext.BaseDirectory, "harness-log.txt");

    // ---- observed frame state, written by the FrameArrived handler ----------
    private static long _frameCount;
    private static DateTime _lastFrameUtc = DateTime.MinValue;
    private static Windows.Graphics.SizeInt32 _lastSize;
    private static bool _sawSizeChangeAfterMinimize;
    private static bool _minimizePhaseActive;
    private static long _baselineFrames;
    private static readonly List<string> _minimizeObservations = new();

    private static async Task<int> Main(string[] args)
    {
        if (args.Length < 1)
        {
            Console.WriteLine("usage: CaptureHarness.exe \"<part of the target window title>\"");
            Console.WriteLine("example: CaptureHarness.exe \"Notepad\"");
            return 2;
        }

        File.AppendAllText(LogPath,
            $"{Environment.NewLine}==================== RUN {DateTime.Now:yyyy-MM-dd HH:mm:ss} ===================={Environment.NewLine}");

        Log($"OS: {Environment.OSVersion.VersionString}");
        Log($"Process: {(Environment.Is64BitProcess ? "x64" : "x86")}");

        try
        {
            Probe0_PackageIdentity();
            Probe0b_OcrIdentity();
            var consent = await Probe1_RequestBorderlessConsentAsync();

            var (hwnd, title) = Interop.FindWindowByTitleSubstring(args[0]);
            if (hwnd == 0)
            {
                Log($"FATAL: no visible window whose title contains \"{args[0]}\". Open it first.");
                return 1;
            }
            Log($"Target window: \"{title}\"  hwnd=0x{hwnd:X}");

            await RunCaptureProbesAsync(hwnd, consent);
        }
        catch (Exception ex)
        {
            Log($"FATAL: {ex.GetType().Name}: {ex.Message}");
            Log(ex.ToString());
            return 1;
        }

        Console.WriteLine();
        Console.WriteLine($"Log written to: {LogPath}");
        Console.WriteLine("Copy the answers into the RESULTS LOG in ../PRE_V3_CHECKLIST.md");
        return 0;
    }

    // =====================================================================
    // PROBE 0 - does this process have package identity?
    // =====================================================================
    private static void Probe0_PackageIdentity()
    {
        Section("PROBE 0", "Does this process have package identity?");

        string pkg = Interop.GetPackageFullNameOrNull();
        if (pkg is null)
        {
            Log("RESULT: NO package identity.");
            Log("        The sparse package is not registered, or the exe was launched");
            Log("        from a path other than the registered external location.");
            Log("        Probes 1-3 will be meaningless. Re-run register.ps1.");
        }
        else
        {
            Log($"RESULT: YES. PackageFullName = {pkg}");
        }

        // Unambiguous verdict: also log the RAW return code of the two-pass
        // GetCurrentPackageFullName call with its constant name resolved, so a
        // null above cannot silently hide an unexpected failure code.
        int rc = Interop.GetPackageFullNameResult();
        string rcName = rc switch
        {
            0 => "ERROR_SUCCESS (packaged)",
            122 => "ERROR_INSUFFICIENT_BUFFER (packaged; buffer sized on 2nd pass)",
            15700 => "APPMODEL_ERROR_NO_PACKAGE 0x80073D54 (NOT packaged)",
            _ => $"unexpected code {rc}"
        };
        Log($"        GetCurrentPackageFullName raw return code = {rc} => {rcName}");
    }

    // =====================================================================
    // PROBE 0b - Windows OCR is package-identity-only, so a working engine
    // is POSITIVE proof of identity. A null engine is ambiguous, so it is
    // cross-checked against PROBE 0.
    // =====================================================================
    private static void Probe0b_OcrIdentity()
    {
        Section("PROBE 0b", "Windows OCR (identity-gated)");

        try
        {
            var engine = Windows.Media.Ocr.OcrEngine.TryCreateFromUserProfileLanguages();
            if (engine != null)
            {
                Log($"RESULT: OCR engine created. This is POSITIVE proof of package identity " +
                    $"(Windows.Media.Ocr is package-identity-only) AND OCR is available. " +
                    $"Language = {engine.RecognizerLanguage}");

                var langs = Windows.Media.Ocr.OcrEngine.AvailableRecognizerLanguages;
                if (langs != null && langs.Count > 0)
                {
                    string joined = string.Join(", ", langs.Select(l => l.LanguageTag));
                    Log($"        AvailableRecognizerLanguages: {joined}");
                }
                else
                {
                    Log("        AvailableRecognizerLanguages: no OCR language packs installed");
                }
            }
            else
            {
                Log("RESULT: OCR engine is null. AMBIGUOUS - means EITHER no package identity " +
                    "OR no OCR language pack installed. Cross-check PROBE 0 to disambiguate.");
            }
        }
        catch (Exception ex)
        {
            Log($"OCR probe THREW: {ex}");
        }
    }

    // =====================================================================
    // PROBE 1 - what does Windows ACTUALLY return for borderless consent?
    // =====================================================================
    private static async Task<AppCapabilityAccessStatus> Probe1_RequestBorderlessConsentAsync()
    {
        Section("PROBE 1", "Borderless consent - the returned status, not the setter");

        Log("Calling GraphicsCaptureAccess.RequestAccessAsync(Borderless)...");
        Log("(A consent prompt may appear. Answer it.)");

        AppCapabilityAccessStatus status;
        try
        {
            status = await GraphicsCaptureAccess.RequestAccessAsync(GraphicsCaptureAccessKind.Borderless);
        }
        catch (Exception ex)
        {
            Log($"RESULT: THREW - {ex.GetType().Name}: {ex.Message}");
            Log("        Most likely cause: graphicsCaptureWithoutBorder not declared,");
            Log("        or the process has no package identity (see probe 0).");
            return AppCapabilityAccessStatus.DeniedBySystem;
        }

        Log($"RESULT: AppCapabilityAccessStatus = {status}");
        Log("NOTE:   Docs are explicit that IsBorderRequired=false SUCCEEDS even when");
        Log("        consent was denied - the value is silently ignored.");
        Log("MEASURED 2026-09-07: this call returned Allowed from a process with NO");
        Log("        package identity and therefore no graphicsCaptureWithoutBorder");
        Log("        capability. So the returned status is NOT proof the app holds the");
        Log("        capability - it appears to report the machine-wide Screenshot");
        Log("        borders setting. Neither the setter NOR this status is ground");
        Log("        truth. The only ground truth is whether the border is drawn.");
        return status;
    }

    // =====================================================================
    // PROBES 2-6
    // =====================================================================
    private static async Task RunCaptureProbesAsync(nint hwnd, AppCapabilityAccessStatus consent)
    {
        var device = Interop.CreateDirect3DDevice();
        var item = Interop.CreateItemForWindow(hwnd);

        Log($"Item created. Initial size: {item.Size.Width}x{item.Size.Height}");

        var pool = Direct3D11CaptureFramePool.CreateFreeThreaded(
            device, DirectXPixelFormat.B8G8R8A8UIntNormalized, 2, item.Size);

        bool closedFired = false;
        item.Closed += (_, _) =>
        {
            closedFired = true;
            Observe("!! GraphicsCaptureItem.Closed FIRED");
        };

        pool.FrameArrived += OnFrameArrived;

        var session = pool.CreateCaptureSession(item);

        // --------------------------------------------------------- PROBE 2
        Section("PROBE 2", "Is the yellow border actually gone?");

        session.IsBorderRequired = false;
        Log("Set session.IsBorderRequired = false (setter does not throw either way).");

        session.StartCapture();
        Log("Capture started.");
        await Task.Delay(1500);
        Log($"Frames so far: {_frameCount}, last size {_lastSize.Width}x{_lastSize.Height}");

        // BASELINE. WGC is change-driven, not fixed-rate: an idle window produces
        // no frames at all. Without this control, probes 4 and 5 cannot tell
        // "capture stopped" apart from "nothing on screen moved".
        Log("Measuring baseline frame rate over 5s - leave the window VISIBLE and CHANGING...");
        long b0 = _frameCount;
        await Task.Delay(5000);
        _baselineFrames = _frameCount - b0;
        Log($"BASELINE: {_baselineFrames} frames in 5s ({_baselineFrames / 5.0:F1}/s)");

        if (_baselineFrames < 3)
        {
            Log("!! WARNING: baseline is near zero.");
            Log("!! Probes 4 and 5 will be INCONCLUSIVE - an idle window looks identical");
            Log("!! to a stopped capture. Re-run against a window with continuously");
            Log("!! changing content: a video, an animation, or a terminal running");
            Log("!!   while($true){ Get-Date; Start-Sleep -Milliseconds 200 }");
        }

        Console.WriteLine();
        Console.WriteLine("  >> LOOK AT THE TARGET WINDOW NOW.");
        Ask("Is the yellow capture border VISIBLE?  (y = still there / n = gone)", "PROBE 2 border visible");

        if (consent != AppCapabilityAccessStatus.Allowed)
        {
            Log("NOTE: consent was NOT Allowed, so a visible border here is the expected");
            Log("      documented behavior - this run is doubling as PROBE 3.");
        }

        // --------------------------------------------------------- PROBE 3
        Section("PROBE 3", "The denied path");
        Log("To test the denied path: Settings > Privacy & security > Screenshot borders");
        Log("  > 'Let desktop apps turn off the screenshot border' -> Deny, then re-run");
        Log("  this harness and compare PROBE 1 status + PROBE 2 answer.");
        Log("REMEMBER to set it back to Allow afterwards.");
        Ask("Is this run the DENIED-path run?  (y/n)", "PROBE 3 is denied run");

        // --------------------------------------------------------- PROBE 4
        Section("PROBE 4", "Occlusion - do frames continue when the window is covered?");

        Console.WriteLine("  >> COVER the target window with another window (do NOT minimize).");
        Pause("Press ENTER once it is fully covered.");

        long before = _frameCount;
        var sizeBefore = _lastSize;
        await Task.Delay(3000);
        long after = _frameCount;

        Log($"Frames while occluded: {after - before} over 3s");
        Log($"Size before {sizeBefore.Width}x{sizeBefore.Height}, after {_lastSize.Width}x{_lastSize.Height}");
        Log(after > before
            ? "RESULT: frames CONTINUE while occluded (expected - DWM composites hidden windows)."
            : "RESULT: frames STOPPED while occluded (UNEXPECTED - record this).");

        Pause("Bring the target window back to the front, then press ENTER.");

        // --------------------------------------------------------- PROBE 5
        Section("PROBE 5", "MINIMIZE - the one that matters");

        Log("Expectation (undocumented by Microsoft, inferred from OBS source + bug reports):");
        Log("  no event fires, one trailing frame arrives at iconic size, then silence,");
        Log("  leaving a STALE last frame that still looks current.");

        Console.WriteLine();
        Console.WriteLine("  >> MINIMIZE the target window now. Then leave it alone for 15 seconds.");
        Pause("Press ENTER the moment AFTER you have minimized it.");

        _minimizePhaseActive = true;
        var minimizeStart = DateTime.UtcNow;
        long framesAtMinimize = _frameCount;
        var sizeAtMinimize = _lastSize;

        var sw = Stopwatch.StartNew();
        while (sw.Elapsed < TimeSpan.FromSeconds(15))
        {
            await Task.Delay(1000);
            double silence = _lastFrameUtc == DateTime.MinValue
                ? -1
                : (DateTime.UtcNow - _lastFrameUtc).TotalSeconds;
            Console.WriteLine(
                $"    t+{sw.Elapsed.TotalSeconds,4:F0}s  frames={_frameCount}  " +
                $"size={_lastSize.Width}x{_lastSize.Height}  silent_for={silence:F1}s  " +
                $"IsIconic={Interop.IsIconic(hwnd)}");
        }
        _minimizePhaseActive = false;

        long framesDuringMinimize = _frameCount - framesAtMinimize;
        double finalSilence = (DateTime.UtcNow - _lastFrameUtc).TotalSeconds;

        Log("--- PROBE 5 RESULT ---");
        Log($"IsIconic(hwnd) at end                : {Interop.IsIconic(hwnd)}");
        Log($"Frames delivered after minimize      : {framesDuringMinimize}");
        Log($"Size at minimize                     : {sizeAtMinimize.Width}x{sizeAtMinimize.Height}");
        Log($"Size at end                          : {_lastSize.Width}x{_lastSize.Height}");
        Log($"Iconic-size frame observed           : {_sawSizeChangeAfterMinimize}");
        Log($"GraphicsCaptureItem.Closed fired     : {closedFired}");
        Log($"Seconds since last frame at end      : {finalSilence:F1}");
        Log($"Baseline frames per 5s (control)     : {_baselineFrames}");

        string verdict;
        if (_baselineFrames < 3)
            verdict = "INCONCLUSIVE - baseline was ~0, an idle window is indistinguishable "
                    + "from a stopped capture. Re-run against changing content.";
        else if (framesDuringMinimize == 0 && !closedFired)
            verdict = "YES - stale frame risk CONFIRMED. Content was flowing before minimize, "
                    + "stopped after, and NO event fired to tell you.";
        else if (framesDuringMinimize > 0)
            verdict = "NO - frames kept arriving while minimized. Record this, it is unexpected.";
        else
            verdict = "Closed event fired - the stream announced its own end.";

        Log($"Stream went silent (no event)        : {verdict}");
        foreach (var o in _minimizeObservations) Log($"  observed: {o}");

        // --------------------------------------------------------- PROBE 6
        Section("PROBE 6", "Can a NEW session start on an already-minimized window?");
        Log("Leaving the window minimized and trying a fresh CreateForWindow + session...");

        try
        {
            var item2 = Interop.CreateItemForWindow(hwnd);
            var pool2 = Direct3D11CaptureFramePool.CreateFreeThreaded(
                device, DirectXPixelFormat.B8G8R8A8UIntNormalized, 2, item2.Size);
            long p2Frames = 0;
            pool2.FrameArrived += (s, _) => { using var f = s.TryGetNextFrame(); if (f != null) Interlocked.Increment(ref p2Frames); };
            var session2 = pool2.CreateCaptureSession(item2);
            session2.StartCapture();
            await Task.Delay(3000);

            Log($"RESULT: creation did NOT throw. item2.Size = {item2.Size.Width}x{item2.Size.Height}, frames in 3s = {p2Frames}");
            Log(p2Frames == 0
                ? "        ...but zero frames arrived. Effectively unusable on a minimized window."
                : "        ...and frames DID arrive. UNEXPECTED - record this carefully.");

            session2.Dispose(); pool2.Dispose();
        }
        catch (Exception ex)
        {
            Log($"RESULT: THREW as expected - {ex.GetType().Name}: {ex.Message}");
        }

        Pause("Restore the target window, then press ENTER to finish.");

        session.Dispose();
        pool.Dispose();
    }

    // =====================================================================
    private static void OnFrameArrived(Direct3D11CaptureFramePool sender, object _)
    {
        using var frame = sender.TryGetNextFrame();
        if (frame is null) return;

        Interlocked.Increment(ref _frameCount);
        _lastFrameUtc = DateTime.UtcNow;

        var size = frame.ContentSize;
        if (size.Width != _lastSize.Width || size.Height != _lastSize.Height)
        {
            string msg = $"frame size changed {_lastSize.Width}x{_lastSize.Height} -> {size.Width}x{size.Height}";
            if (_minimizePhaseActive)
            {
                _sawSizeChangeAfterMinimize = true;
                Observe("ICONIC-SIZE FRAME: " + msg);
            }
            _lastSize = size;
        }
    }

    // =====================================================================
    private static void Observe(string s)
    {
        lock (_minimizeObservations) _minimizeObservations.Add(s);
        Log(s);
    }

    private static void Section(string tag, string question)
    {
        Log("");
        Log(new string('-', 70));
        Log($"{tag}: {question}");
        Log(new string('-', 70));
    }

    private static void Ask(string question, string label)
    {
        Console.Write($"    {question} ");
        string a = Console.ReadLine()?.Trim().ToLowerInvariant();
        Log($"ANSWER [{label}]: {a}");
    }

    private static void Pause(string msg)
    {
        Console.Write($"    {msg} ");
        Console.ReadLine();
    }

    private static void Log(string line)
    {
        string stamped = line.Length == 0 ? "" : $"[{DateTime.Now:HH:mm:ss.fff}] {line}";
        Console.WriteLine(stamped);
        File.AppendAllText(LogPath, stamped + Environment.NewLine);
    }
}
