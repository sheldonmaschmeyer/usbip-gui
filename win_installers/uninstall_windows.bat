@echo off
setlocal EnableDelayedExpansion

echo =========================================
echo  USB/IP Manager Windows Uninstaller
echo  This is not tested. Use at your own risk.
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
if /i "%REMOVE_DRIVERS%"=="Y" (
    echo.
    echo Requesting Administrator rights to uninstall drivers...

    set "PS1_FILE=%TEMP%\usbip_uninstall.ps1"
    echo $ProgressPreference = 'SilentlyContinue' > "!PS1_FILE!"

    echo Write-Host "Uninstalling usbipd-win (Server)..." >> "!PS1_FILE!"
    echo winget uninstall --id dorssel.usbipd-win --silent >> "!PS1_FILE!"

    echo Write-Host "Uninstalling usbip-win2 (Client)..." >> "!PS1_FILE!"
    echo $paths = @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall', 'HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall') >> "!PS1_FILE!"
    echo $apps = Get-ChildItem -Path $paths -ErrorAction SilentlyContinue ^| Get-ItemProperty -ErrorAction SilentlyContinue ^| Where-Object { $_.DisplayName -match 'usbip-win2' } >> "!PS1_FILE!"
    echo foreach ($app in $apps) { >> "!PS1_FILE!"
    echo     if ($app.UninstallString -match 'msiexec') { >> "!PS1_FILE!"
    echo         $productCode = $app.UninstallString -replace '.*({.*}).*', '$1' >> "!PS1_FILE!"
    echo         Start-Process msiexec.exe -Wait -ArgumentList "/x `$productCode /quiet /norestart" >> "!PS1_FILE!"
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
echo Note: The global 'pixi' package manager was NOT uninstalled,
echo as it might be used by other tools on your system.
echo If you wish to remove it manually,
echo you can delete the %USERPROFILE%\.pixi folder
echo or remove it from your PATH.
echo.
echo =========================================
echo  Uninstallation Complete!
echo =========================================
pause
