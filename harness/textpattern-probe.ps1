# textpattern-probe.ps1 — checklist step 4, without the GUI fumbling.
#
# Run it, then click into the app you want to test and put your text cursor
# in the middle of a sentence. After the countdown it reports:
#
#   - which element had focus (app, control type, name)
#   - whether TextPattern is supported
#   - the actual selection / caret text it can read back
#
# Answers land in textpattern-results.txt next to this script.
#
# Run in WINDOWS POWERSHELL 5.1 (the blue one, "powershell.exe"), NOT admin.
# Admin matters: UI Automation is blocked across privilege levels, so an
# elevated probe cannot see a normal app and would report a false negative.

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$ResultsPath = Join-Path $PSScriptRoot 'textpattern-results.txt'
$TextPatternId = [System.Windows.Automation.TextPattern]::Pattern

if (([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host ''
    Write-Host 'WARNING: this PowerShell is ELEVATED.' -ForegroundColor Red
    Write-Host 'UI Automation is blocked across privilege levels. Every normal app will'
    Write-Host 'look like it has no TextPattern. Close this and use a NON-admin window.'
    Write-Host ''
    Read-Host 'Press ENTER to continue anyway, or Ctrl+C to quit'
}

function Get-ProcessNameSafe($processId) {
    try { (Get-Process -Id $processId -ErrorAction Stop).ProcessName } catch { "pid:$processId" }
}

function Test-Element($el, $label) {
    $supported = $el.GetSupportedPatterns() | ForEach-Object { $_.ProgrammaticName }
    $hasText = $supported -contains $TextPatternId.ProgrammaticName

    $line = "  {0,-10} ControlType={1,-28} Name='{2}'" -f `
        $label,
        ($el.Current.ControlType.ProgrammaticName -replace 'ControlType\.', ''),
        $el.Current.Name

    if (-not $hasText) {
        return @{ Found = $false; Report = "$line  TextPattern=NO" }
    }

    $detail = 'TextPattern=YES'
    try {
        $tp = $el.GetCurrentPattern($TextPatternId)

        try {
            $sel = $tp.GetSelection()
            if ($sel -and $sel.Count -gt 0) {
                $t = $sel[0].GetText(120)
                $detail += "  caret=OK  selected='" + ($t -replace '\s+', ' ') + "'"

                # A collapsed caret selects zero characters, so GetText is empty and
                # proves nothing. The feature needs the text AROUND the caret, so
                # expand the range and see what comes back. This is the real test.
                foreach ($unit in @('Sentence', 'Line', 'Paragraph')) {
                    try {
                        $r = $sel[0].Clone()
                        $r.ExpandToEnclosingUnit([System.Windows.Automation.Text.TextUnit]::$unit)
                        $x = $r.GetText(200)
                        if ([string]::IsNullOrWhiteSpace($x)) {
                            $detail += "  $unit=EMPTY"
                        } else {
                            $detail += "  $unit='" + ($x -replace '\s+', ' ').Trim() + "'"
                        }
                    } catch {
                        $detail += "  $unit=THREW"
                    }
                }

                # Bounding rect proves the provider knows WHERE the caret is,
                # not just that a range object exists.
                try {
                    $rects = $sel[0].GetBoundingRectangles()
                    $detail += '  caretRects=' + $(if ($rects) { $rects.Count } else { 0 })
                } catch {
                    $detail += '  caretRects=THREW'
                }
            } else {
                $detail += '  selection=EMPTY ARRAY'
            }
        } catch {
            $detail += '  selection=THREW (' + $_.Exception.GetType().Name + ')'
        }

        try {
            $doc = $tp.DocumentRange.GetText(80)
            $detail += "  doc='" + ($doc -replace '\s+', ' ') + "'"
        } catch {
            $detail += '  doc=THREW'
        }
    } catch {
        $detail += '  pattern fetch THREW: ' + $_.Exception.Message
    }

    return @{ Found = $true; Report = "$line  $detail" }
}

function Probe-Focused($tag) {
    $el = [System.Windows.Automation.AutomationElement]::FocusedElement
    if ($null -eq $el) { return "[$tag] no focused element." }

    $proc = Get-ProcessNameSafe $el.Current.ProcessId
    $out = New-Object System.Collections.Generic.List[string]
    $out.Add("[$tag]  process=$proc")

    # The focused element itself.
    $r = Test-Element $el 'FOCUSED'
    $out.Add($r.Report)
    $verdict = $r.Found

    # If the focused element has no TextPattern, walk up - editors often put it
    # on an ancestor (the document) rather than the focused control.
    if (-not $r.Found) {
        $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
        $cur = $el
        for ($i = 1; $i -le 5; $i++) {
            try { $cur = $walker.GetParent($cur) } catch { break }
            if ($null -eq $cur) { break }
            $r2 = Test-Element $cur "ANCESTOR$i"
            $out.Add($r2.Report)
            if ($r2.Found) { $verdict = $true; break }
        }
    }

    $out.Add("  ==> VERDICT: " + $(if ($verdict) { 'TEXTPATTERN AVAILABLE' } else { 'NO TEXTPATTERN' }))
    return ($out -join [Environment]::NewLine)
}

# ---------------------------------------------------------------- main loop

Write-Host ''
Write-Host '=== TextPattern probe - pre-v3 checklist step 4 ===' -ForegroundColor Cyan
Write-Host ''
Write-Host 'For each app: type a sentence, put the CARET IN THE MIDDLE of it, then'
Write-Host 'come back here, enter a label, and click into the app during the countdown.'
Write-Host ''
Write-Host 'Suggested labels, in order:'
Write-Host '  word / notepad / chrome-page / chrome-addressbar / vscode-default /'
Write-Host '  vscode-a11y-on / electron2 / daily1 / daily2 / daily3'
Write-Host ''
Write-Host 'Type "q" as the label to quit.'
Write-Host ''

"==== RUN $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ====" | Add-Content $ResultsPath

while ($true) {
    $tag = Read-Host 'Label for this test (or q)'
    if ([string]::IsNullOrWhiteSpace($tag)) { continue }
    if ($tag.Trim().ToLower() -eq 'q') { break }

    Write-Host '  Click into the target app and place your caret NOW...' -ForegroundColor Yellow
    for ($i = 5; $i -ge 1; $i--) {
        Write-Host "    $i..." -NoNewline
        Start-Sleep -Seconds 1
    }
    Write-Host ''

    $report = Probe-Focused $tag.Trim()

    Write-Host ''
    Write-Host $report -ForegroundColor Green
    Write-Host ''

    $report | Add-Content $ResultsPath
    '' | Add-Content $ResultsPath
}

Write-Host ''
Write-Host "Results appended to: $ResultsPath" -ForegroundColor Cyan
Write-Host 'Copy the verdict lines into the RESULTS LOG in ../PRE_V3_CHECKLIST.md'
