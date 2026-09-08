using System.Runtime.InteropServices;
using System.Text;
using Windows.Graphics.Capture;
using Windows.Graphics.DirectX.Direct3D11;

namespace CaptureHarness;

/// <summary>
/// Hand-rolled native interop so the harness needs zero NuGet packages.
/// If anything fails to compile, it will be in this file.
/// </summary>
internal static class Interop
{
    // ---------------------------------------------------------------- user32

    public delegate bool EnumWindowsProc(nint hWnd, nint lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc callback, nint lParam);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(nint hWnd);

    /// <summary>True when the window is minimized. Win32 calls this "iconic".</summary>
    [DllImport("user32.dll")]
    public static extern bool IsIconic(nint hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetWindowTextW(nint hWnd, StringBuilder text, int count);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetWindowTextLengthW(nint hWnd);

    // -------------------------------------------------------------- kernel32

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetCurrentPackageFullName(ref int length, StringBuilder fullName);

    private const int APPMODEL_ERROR_NO_PACKAGE = 15700;

    /// <summary>Probe 0: does this process have package identity?</summary>
    public static string GetPackageFullNameOrNull()
    {
        int len = 0;
        int rc = GetCurrentPackageFullName(ref len, null);
        if (rc == APPMODEL_ERROR_NO_PACKAGE) return null;

        var sb = new StringBuilder(len);
        rc = GetCurrentPackageFullName(ref len, sb);
        return rc == 0 ? sb.ToString() : null;
    }

    /// <summary>
    /// Probe 0 support: same two-pass GetCurrentPackageFullName call, but returns
    /// the RAW int return code so the caller can log the exact constant
    /// (0 / 122 / 15700 / other) rather than only a YES/NO verdict. This removes
    /// the ambiguity where a null from GetPackageFullNameOrNull could hide an
    /// unexpected failure code. Purely additive - GetPackageFullNameOrNull and its
    /// existing callers are untouched.
    /// </summary>
    public static int GetPackageFullNameResult()
    {
        int len = 0;
        int rc = GetCurrentPackageFullName(ref len, null);
        if (rc == APPMODEL_ERROR_NO_PACKAGE) return rc;

        var sb = new StringBuilder(len);
        rc = GetCurrentPackageFullName(ref len, sb);
        return rc;
    }

    // ------------------------------------------------------------------ d3d11

    private const int D3D_DRIVER_TYPE_HARDWARE = 1;
    private const uint D3D11_CREATE_DEVICE_BGRA_SUPPORT = 0x20;
    private const uint D3D11_SDK_VERSION = 7;

    [DllImport("d3d11.dll")]
    private static extern int D3D11CreateDevice(
        nint pAdapter, int driverType, nint software, uint flags,
        nint pFeatureLevels, uint featureLevels, uint sdkVersion,
        out nint ppDevice, out int pFeatureLevel, out nint ppImmediateContext);

    [DllImport("d3d11.dll")]
    private static extern int CreateDirect3D11DeviceFromDXGIDevice(nint dxgiDevice, out nint graphicsDevice);

    private static readonly Guid IID_IDXGIDevice = new("54ec77fa-1377-44e6-8c32-88fd5f44c84c");

    /// <summary>
    /// WGC needs a graphics device to hand frames back on. We never draw anything;
    /// this exists only because the API refuses to start without one.
    /// </summary>
    public static IDirect3DDevice CreateDirect3DDevice()
    {
        int hr = D3D11CreateDevice(
            0, D3D_DRIVER_TYPE_HARDWARE, 0, D3D11_CREATE_DEVICE_BGRA_SUPPORT,
            0, 0, D3D11_SDK_VERSION,
            out nint d3dDevice, out _, out nint context);

        if (hr != 0) throw new InvalidOperationException($"D3D11CreateDevice failed: 0x{hr:X8}");
        if (context != 0) Marshal.Release(context);

        Guid dxgiIid = IID_IDXGIDevice;
        hr = Marshal.QueryInterface(d3dDevice, ref dxgiIid, out nint dxgiDevice);
        if (hr != 0) throw new InvalidOperationException($"QueryInterface(IDXGIDevice) failed: 0x{hr:X8}");

        hr = CreateDirect3D11DeviceFromDXGIDevice(dxgiDevice, out nint inspectable);
        Marshal.Release(dxgiDevice);
        Marshal.Release(d3dDevice);
        if (hr != 0) throw new InvalidOperationException($"CreateDirect3D11DeviceFromDXGIDevice failed: 0x{hr:X8}");

        var device = WinRT.MarshalInspectable<IDirect3DDevice>.FromAbi(inspectable);
        Marshal.Release(inspectable);
        return device;
    }

    // --------------------------------------------- GraphicsCaptureItem interop

    [ComImport]
    [Guid("3628E81B-3CAC-4C60-B7F4-23CE0E0C3356")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IGraphicsCaptureItemInterop
    {
        nint CreateForWindow([In] nint window, [In] ref Guid iid);
        nint CreateForMonitor([In] nint monitor, [In] ref Guid iid);
    }

    private static readonly Guid IID_GraphicsCaptureItem = new("79C3F95B-31F7-4EC2-A464-632EF5D30760");
    private static readonly Guid IID_IGraphicsCaptureItemInterop = new("3628E81B-3CAC-4C60-B7F4-23CE0E0C3356");

    // Going through combase directly instead of CsWinRT's activation helpers.
    // CsWinRT has changed the shape of those helpers between versions
    // (WinRT.ActivationFactory<T> was generic, then wasn't); RoGetActivationFactory
    // is the underlying OS entry point and does not move.
    [DllImport("combase.dll", CharSet = CharSet.Unicode)]
    private static extern int WindowsCreateString(
        [MarshalAs(UnmanagedType.LPWStr)] string sourceString, uint length, out nint hstring);

    [DllImport("combase.dll")]
    private static extern int WindowsDeleteString(nint hstring);

    [DllImport("combase.dll")]
    private static extern int RoGetActivationFactory(nint activatableClassId, ref Guid iid, out nint factory);

    /// <summary>
    /// There is no managed way to say "capture THIS window" - you have to go through
    /// a COM interop interface on the class's activation factory. This is that.
    /// Throws if the HWND is not capturable (probe 6 relies on this).
    /// </summary>
    public static GraphicsCaptureItem CreateItemForWindow(nint hwnd)
    {
        const string className = "Windows.Graphics.Capture.GraphicsCaptureItem";

        int hr = WindowsCreateString(className, (uint)className.Length, out nint hstr);
        if (hr != 0) throw new InvalidOperationException($"WindowsCreateString failed: 0x{hr:X8}");

        nint factoryPtr = 0;
        try
        {
            Guid factoryIid = IID_IGraphicsCaptureItemInterop;
            hr = RoGetActivationFactory(hstr, ref factoryIid, out factoryPtr);
            if (hr != 0)
                throw new InvalidOperationException($"RoGetActivationFactory(GraphicsCaptureItem) failed: 0x{hr:X8}");

            var interop = (IGraphicsCaptureItemInterop)Marshal.GetObjectForIUnknown(factoryPtr);

            Guid itemIid = IID_GraphicsCaptureItem;
            nint abi = interop.CreateForWindow(hwnd, ref itemIid);

            var item = WinRT.MarshalInspectable<GraphicsCaptureItem>.FromAbi(abi);
            Marshal.Release(abi);
            return item;
        }
        finally
        {
            if (factoryPtr != 0) Marshal.Release(factoryPtr);
            WindowsDeleteString(hstr);
        }
    }

    // ------------------------------------------------------------ window find

    public static (nint Handle, string Title) FindWindowByTitleSubstring(string needle)
    {
        nint found = 0;
        string foundTitle = null;

        EnumWindows((hWnd, _) =>
        {
            if (!IsWindowVisible(hWnd)) return true;

            int len = GetWindowTextLengthW(hWnd);
            if (len == 0) return true;

            var sb = new StringBuilder(len + 1);
            GetWindowTextW(hWnd, sb, sb.Capacity);
            string title = sb.ToString();

            if (title.Contains(needle, StringComparison.OrdinalIgnoreCase))
            {
                found = hWnd;
                foundTitle = title;
                return false; // stop enumerating
            }
            return true;
        }, 0);

        return (found, foundTitle);
    }
}
