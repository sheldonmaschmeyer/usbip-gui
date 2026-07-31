@echo off
cd /d "%~dp0\.."
:: Ensure pixi is in the PATH, especially right after installation before Explorer restarts
set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%LOCALAPPDATA%\pixi\bin;%USERPROFILE%\.pixi\bin;%PATH%"
pixi run usbip
