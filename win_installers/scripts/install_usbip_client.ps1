$ProgressPreference = 'SilentlyContinue'
$repo = 'vadimgrn/usbip-win2'
$release = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases/latest"
$asset = $release.assets | Where-Object { $_.name -match 'x64\.exe$' }
$url = $asset.browser_download_url
$tempFile = "$env:TEMP\usbip-win2.exe"
Invoke-WebRequest -Uri $url -OutFile $tempFile
Start-Process -FilePath $tempFile -Wait -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
Remove-Item $tempFile -ErrorAction SilentlyContinue
