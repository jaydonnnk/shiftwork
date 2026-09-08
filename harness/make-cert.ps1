# make-cert.ps1 — creates a self-signed cert and trusts it on THIS machine.
# Run as Administrator. Once.
#
# Plain English: the sparse package needs a signature, and Windows only accepts
# signatures it trusts. Here you sign your own name tag and then tell your own PC
# to believe you. That is fine for a local harness; it is also why a judge cloning
# the repo would hit the same wall (README note in the v3 plan).

$ErrorActionPreference = 'Stop'

$Subject  = 'CN=CelesteDev'
$PfxPath  = Join-Path $PSScriptRoot 'celeste-harness.pfx'
$Password = 'harness'

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
        ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error 'Run this script as Administrator. It writes to the machine certificate store.'
}

Write-Host '[1/3] Creating self-signed code-signing certificate...' -ForegroundColor Cyan

$cert = New-SelfSignedCertificate `
    -Type Custom `
    -Subject $Subject `
    -KeyUsage DigitalSignature `
    -FriendlyName 'Celeste Capture Harness (dev)' `
    -CertStoreLocation 'Cert:\CurrentUser\My' `
    -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3', '2.5.29.19={text}')

Write-Host ("      Thumbprint: {0}" -f $cert.Thumbprint)

Write-Host '[2/3] Exporting PFX...' -ForegroundColor Cyan

$securePw = ConvertTo-SecureString -String $Password -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath $PfxPath -Password $securePw | Out-Null

Write-Host ("      Wrote {0}" -f $PfxPath)

Write-Host '[3/3] Installing into Trusted People and Trusted Root (LocalMachine)...' -ForegroundColor Cyan

Import-PfxCertificate -FilePath $PfxPath -CertStoreLocation 'Cert:\LocalMachine\TrustedPeople' -Password $securePw | Out-Null
Import-PfxCertificate -FilePath $PfxPath -CertStoreLocation 'Cert:\LocalMachine\Root'          -Password $securePw | Out-Null

Write-Host ''
Write-Host 'DONE. Certificate created and trusted.' -ForegroundColor Green
Write-Host 'Next: run register.ps1 from a NORMAL (non-admin) PowerShell.'
