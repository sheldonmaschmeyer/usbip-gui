@echo off
setlocal EnableDelayedExpansion

echo =========================================
echo  USB/IP Manager Windows Uninstaller
echo  Tested and recommended for Windows 11.
echo  No Warranty of any kind. Use at your own risk.
echo =========================================
echo.

cd /d "%~dp0\.."

echo [1/3] Removing Desktop Shortcut...
if exist "%USERPROFILE%\Desktop\USBIP Manager.lnk" (
    del "%USERPROFILE%\Desktop\USBIP Manager.lnk"
    echo [OK] Shortcut removed.
) else (
    echo [INFO] Shortcut not found.
)

echo.
echo [2/3] Removing local application environment (.pixi folder)...
if exist ".pixi" (
    rmdir /s /q ".pixi"
    echo [OK] Local environment removed.
) else (
    echo [INFO] Local environment not found.
)

echo.
echo [3/3] System Drivers (usbipd-win and usbip-win2)
echo The system USB/IP drivers might be in use by other applications.
set /p REMOVE_DRIVERS="Do you want to uninstall them? (Y/N): "
if /i "%REMOVE_DRIVERS:~0,1%"=="Y" (
    echo.
    echo Requesting Administrator rights to uninstall drivers...

    set "PS1_FILE=%TEMP%\usbip_uninstall.ps1"
    echo $ProgressPreference = 'SilentlyContinue' > "!PS1_FILE!"

    echo Write-Host "Uninstalling usbipd-win Server..." >> "!PS1_FILE!"
    echo winget uninstall --id dorssel.usbipd-win --silent >> "!PS1_FILE!"

    echo Write-Host "Uninstalling usbip client tools..." >> "!PS1_FILE!"
    echo $paths = @^('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall', 'HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall', 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall', 'HKCU:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall'^) >> "!PS1_FILE!"
    echo $apps = Get-ChildItem -Path $paths -ErrorAction SilentlyContinue ^| Get-ItemProperty -ErrorAction SilentlyContinue ^| Where-Object { $_.DisplayName -match 'usbip-win2^|USBip' -or $_.InstallLocation -like '*\USBip*' } >> "!PS1_FILE!"
    echo foreach ^($app in $apps^) { >> "!PS1_FILE!"
    echo     if ^($app.QuietUninstallString^) { >> "!PS1_FILE!"
    echo         Start-Process cmd.exe -Wait -ArgumentList "/c $^($app.QuietUninstallString^)" >> "!PS1_FILE!"
    echo         continue >> "!PS1_FILE!"
    echo     } >> "!PS1_FILE!"
    echo     if ^(-not $app.UninstallString^) { continue } >> "!PS1_FILE!"
    echo     if ^($app.UninstallString -match 'msiexec'^) { >> "!PS1_FILE!"
    echo         if ^($app.UninstallString -match '{[0-9A-Fa-f-]+}'^) { >> "!PS1_FILE!"
    echo             $productCode = $Matches[0] >> "!PS1_FILE!"
    echo             Start-Process msiexec.exe -Wait -ArgumentList "/x $productCode /quiet /norestart" >> "!PS1_FILE!"
    echo         } else { >> "!PS1_FILE!"
    echo             Start-Process cmd.exe -Wait -ArgumentList "/c $^($app.UninstallString^) /quiet /norestart" >> "!PS1_FILE!"
    echo         } >> "!PS1_FILE!"
    echo     } else { >> "!PS1_FILE!"
    echo         Start-Process cmd.exe -Wait -ArgumentList "/c $^($app.UninstallString^) /VERYSILENT /SUPPRESSMSGBOXES /NORESTART" >> "!PS1_FILE!"
    echo     } >> "!PS1_FILE!"
    echo } >> "!PS1_FILE!"

    echo $legacyAppPath = Join-Path $env:ProgramFiles 'USBip\wusbip.exe' >> "!PS1_FILE!"
    echo if ^(Test-Path $legacyAppPath^) { >> "!PS1_FILE!"
    echo     Write-Host 'Legacy USBip client still detected. Running direct cleanup...' >> "!PS1_FILE!"
    echo     Get-Process -Name 'wusbip' -ErrorAction SilentlyContinue ^| Stop-Process -Force -ErrorAction SilentlyContinue >> "!PS1_FILE!"
    echo     $legacyDir = Split-Path -Path $legacyAppPath -Parent >> "!PS1_FILE!"
    echo     $inno = Get-ChildItem -Path $legacyDir -Filter 'unins*.exe' -ErrorAction SilentlyContinue ^| Select-Object -First 1 >> "!PS1_FILE!"
    echo     if ^($inno^) { >> "!PS1_FILE!"
    echo         Start-Process -FilePath $inno.FullName -Wait -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' >> "!PS1_FILE!"
    echo     } >> "!PS1_FILE!"
    echo     if ^(Test-Path $legacyAppPath^) { >> "!PS1_FILE!"
    echo         Remove-Item -Path $legacyDir -Recurse -Force -ErrorAction SilentlyContinue >> "!PS1_FILE!"
    echo     } >> "!PS1_FILE!"
    echo } >> "!PS1_FILE!"

    echo Write-Host "Driver uninstallation phase complete." >> "!PS1_FILE!"
    echo Start-Sleep -Seconds 2 >> "!PS1_FILE!"

    powershell -Command "Start-Process powershell.exe -Wait -Verb RunAs -ArgumentList '-ExecutionPolicy Bypass -WindowStyle Normal -File \"!PS1_FILE!\"'"

    if exist "!PS1_FILE!" del "!PS1_FILE!"
) else (
    echo [INFO] Skipping driver uninstallation.
)

echo.
echo Note: The global 'pixi' package manager and Python runtime were NOT uninstalled,
echo as it might be used by other tools on your system.
echo If you wish to remove them manually,
echo you can delete the %USERPROFILE%\.pixi folder,
echo uninstall Python from Windows Apps settings,
echo and remove them from your PATH if needed.
echo.
echo =========================================
echo  Uninstallation Complete!
echo =========================================
pause
