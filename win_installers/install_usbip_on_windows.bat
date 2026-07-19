@echo off
setlocal EnableDelayedExpansion

echo =========================================
echo  USB/IP Manager Windows Installer
echo  Tested and recommended for Windows 11.
echo  No Warranty of any kind. Use at your own risk.
echo =========================================
echo.

cd /d "%~dp0\.."

echo [1/4] Checking System Drivers (usbipd-win and usbip-win2)...
where usbip.exe >nul 2>&1
set CLIENT_INSTALLED=%errorLevel%
winget list --exact --id dorssel.usbipd-win --accept-source-agreements >nul 2>&1
set SERVER_INSTALLED=%errorLevel%

if %CLIENT_INSTALLED% NEQ 0 set NEED_ELEVATION=1
if %SERVER_INSTALLED% NEQ 0 set NEED_ELEVATION=1

if defined NEED_ELEVATION (
    echo Missing drivers detected. Requesting Administrator rights to install them...

    :: Generate PS1 file for elevated tasks
    set "PS1_FILE=%TEMP%\usbip_install.ps1"
    echo $ProgressPreference = 'SilentlyContinue' > "!PS1_FILE!"

    if %SERVER_INSTALLED% NEQ 0 (
        echo Write-Host "Installing usbipd-win (Server)..." >> "!PS1_FILE!"
        echo winget install --id dorssel.usbipd-win --accept-package-agreements --accept-source-agreements --silent >> "!PS1_FILE!"
    )

    if %CLIENT_INSTALLED% NEQ 0 (
        echo Write-Host "Installing usbip-win2 (Client)..." >> "!PS1_FILE!"
        echo $repo='vadimgrn/usbip-win2' >> "!PS1_FILE!"
        echo $release=Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases/latest" >> "!PS1_FILE!"
        echo $asset=$release.assets ^| Where-Object { $_.name -match 'x64\.exe$' } >> "!PS1_FILE!"
        echo $url=$asset.browser_download_url >> "!PS1_FILE!"
        echo Invoke-WebRequest -Uri $url -OutFile "$env:TEMP\usbip-win2.exe" >> "!PS1_FILE!"
        echo Start-Process -FilePath "$env:TEMP\usbip-win2.exe" -Wait -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART" >> "!PS1_FILE!"
        echo Remove-Item "$env:TEMP\usbip-win2.exe" -ErrorAction SilentlyContinue >> "!PS1_FILE!"
    )
    echo Write-Host "Driver installation phase complete." >> "!PS1_FILE!"
    echo Start-Sleep -Seconds 2 >> "!PS1_FILE!"

    powershell -Command "Start-Process powershell.exe -Wait -Verb RunAs -ArgumentList '-ExecutionPolicy Bypass -WindowStyle Normal -File \"!PS1_FILE!\"'"

    if exist "!PS1_FILE!" del "!PS1_FILE!"
) else (
    echo [OK] System drivers already installed.
)

:: Install pixi (Standard User)
echo.
echo [2/4] Checking Python/Qt Package Manager (pixi)...
where pixi >nul 2>&1
if %errorLevel% NEQ 0 (
    echo Installing pixi...
    winget install --id prefix-dev.pixi --accept-source-agreements --accept-package-agreements --silent
    :: Add typical install locations to current session PATH so it can be used immediately
    set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%LOCALAPPDATA%\pixi\bin;%USERPROFILE%\.pixi\bin;%PATH%"
) else (
    echo [OK] pixi is already installed.
)

echo.
echo [2.1/4] Checking Python runtime...
where python >nul 2>&1
set PY_FOUND=%errorLevel%
if %PY_FOUND% NEQ 0 (
    where py >nul 2>&1
    set PY_FOUND=%errorLevel%
)
if %PY_FOUND% NEQ 0 (
    echo Python not found. Installing the latest stable Python...
    winget install --id Python.Python.3 --accept-package-agreements --accept-source-agreements --silent
    if %errorLevel% NEQ 0 (
        echo [WARNING] Python installation failed. Please install Python manually and rerun this installer.
    ) else (
        echo [OK] Python installed.
    )
) else (
    echo [OK] Python is already installed.
)

echo [2.2/4] Refreshing Python path...
set "PYTHON_DIR="
for /f "delims=" %%i in ('where python 2^>nul') do (
    set "PYTHON_DIR=%%~dpi"
    goto PY_SET_DONE
)
for /f "delims=" %%i in ('where py 2^>nul') do (
    set "PYTHON_DIR=%%~dpi"
    goto PY_SET_DONE
)
:PY_SET_DONE
if defined PYTHON_DIR (
    set "PATH=%PYTHON_DIR%;%PATH%"
)

:: Install app dependencies
:: (this also installs the project's own OpenSSL, used for Secure/SSL
:: tunnel mode, so no host-wide OpenSSL install is needed)
echo.
echo [3/4] Installing App Dependencies...
call pixi install

:: Create Desktop Shortcut
echo.
echo [4/4] Creating Desktop Shortcut...
:: Resolve app directory path nicely
pushd "%~dp0.."
set "APP_DIR=%CD%"
popd

:: Simplified shortcut arguments since WorkingDirectory handles the path
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\USBIP Manager.lnk'); $Shortcut.TargetPath = 'cmd.exe'; $Shortcut.Arguments = '/c pixi run usbip'; $Shortcut.WorkingDirectory = '%APP_DIR%'; $Shortcut.WindowStyle = 7; $Shortcut.IconLocation = '%APP_DIR%\icon\usbip-logo.ico'; $Shortcut.Save()"

echo.
echo =========================================
echo  Installation Complete!
echo =========================================
echo.
echo USB/IP Manager is built upon several open-source projects.
echo Please check out their READMEs and documentation:
echo - Pixi: https://pixi.sh/
echo - Qt: https://riverbankcomputing.com/software/pyqt/
echo - dorssel/usbipd-win: https://github.com/dorssel/usbipd-win
echo - vadimgrn/usbip-win2: https://github.com/vadimgrn/usbip-win2
echo - Original usbip: https://usbip.sourceforge.net/
echo.
echo Note: If USB drivers were newly installed, you may need to restart your computer.
echo You can now launch the application using the "USBIP Manager" shortcut on your Desktop.
echo.
pause
