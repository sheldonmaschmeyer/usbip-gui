$ProgressPreference = 'SilentlyContinue'

# Check and install Server Drivers
if (-not (winget list --exact --id dorssel.usbipd-win 2>$null)) {
    Write-Host "Installing usbipd-win (Server)..."
    winget install --id dorssel.usbipd-win --accept-package-agreements --accept-source-agreements --silent
}

# Check and install Client Drivers
if (-not (Get-Command usbip.exe -ErrorAction SilentlyContinue)) {
    Write-Host "Installing usbip-win2 (Client)..."
    $repo = 'vadimgrn/usbip-win2'
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases/latest"
    $asset = $release.assets | Where-Object { $_.name -match '\.msi$' }
    $url = $asset.browser_download_url
    $tempMsi = "$env:TEMP\usbip-win2.msi"
    Invoke-WebRequest -Uri $url -OutFile $tempMsi
    Start-Process msiexec.exe -Wait -ArgumentList "/i `"$tempMsi`" /quiet /norestart"
    Remove-Item $tempMsi -ErrorAction SilentlyContinue
}
