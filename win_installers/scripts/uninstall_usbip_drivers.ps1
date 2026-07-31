$ProgressPreference = 'SilentlyContinue'

Write-Host "Uninstalling usbipd-win Server..."
winget uninstall --id dorssel.usbipd-win --silent

Write-Host "Uninstalling usbip client tools..."
$paths = @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall', 'HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall', 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall', 'HKCU:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall')
$apps = Get-ChildItem -Path $paths -ErrorAction SilentlyContinue | Get-ItemProperty -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -match 'usbip-win2|USBip' -or $_.InstallLocation -like '*\USBip*' }

foreach ($app in $apps) {
    if ($app.QuietUninstallString) {
        Start-Process cmd.exe -Wait -ArgumentList "/c $($app.QuietUninstallString)"
        continue
    }
    if (-not $app.UninstallString) { continue }
    if ($app.UninstallString -match 'msiexec') {
        if ($app.UninstallString -match '{[0-9A-Fa-f-]+}') {
            $productCode = $Matches[0]
            Start-Process msiexec.exe -Wait -ArgumentList "/x $productCode /quiet /norestart"
        } else {
            Start-Process cmd.exe -Wait -ArgumentList "/c $($app.UninstallString) /quiet /norestart"
        }
    } else {
        Start-Process cmd.exe -Wait -ArgumentList "/c $($app.UninstallString) /VERYSILENT /SUPPRESSMSGBOXES /NORESTART"
    }
}

$legacyAppPath = Join-Path $env:ProgramFiles 'USBip\wusbip.exe'
if (Test-Path $legacyAppPath) {
    Write-Host 'Legacy USBip client still detected. Running direct cleanup...'
    Get-Process -Name 'wusbip' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    $legacyDir = Split-Path -Path $legacyAppPath -Parent
    $inno = Get-ChildItem -Path $legacyDir -Filter 'unins*.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($inno) {
        Start-Process -FilePath $inno.FullName -Wait -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
    }
    if (Test-Path $legacyAppPath) {
        Remove-Item -Path $legacyDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Driver uninstallation phase complete."
