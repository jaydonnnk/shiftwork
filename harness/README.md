# Windows Capture Research Harness

This folder contains the reusable source from Celeste's pre-v3 Windows feasibility
tests. It is reference code, not the v3 application.

The retained harness demonstrated:

- Sparse package identity and Windows.Media.Ocr activation.
- Windows.Graphics.Capture behavior while occluded and minimized.
- The stale-frame risk when a minimized capture stream stops without a close event.
- UI Automation and OCR capability differences across native, Chromium, and Electron
  applications.

Authoritative findings and v3 consequences are summarized in
`../PRE_V3_CHECKLIST.md`. Raw logs were deleted because they contained captured
personal desktop text. Generated binaries, packages, certificates, staging folders,
and the failed Probe 3 copy were also deleted.

## Retained files

- `src/` — C# capture prototype and interop source.
- `AppxManifest.xml` and `src/app.manifest` — sparse identity reference.
- `make-cert.ps1` — regenerates a local development certificate when explicitly run.
- `register.ps1` — builds, packages, signs, and registers the local prototype.
- `textpattern-probe.ps1` — UIA capability probe; its output is ignored.

Do not commit generated `.pfx`, `.msix`, `bin/`, `obj/`, `stage/`, probe working
copies, or probe output. Never run the probe against real personal data intended for a
public artifact.
