"""Tests for the Windows uninstaller batch script."""

from pathlib import Path


def _read_script(path: str) -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / path).read_text(encoding="utf-8")


def test_uninstall_removes_installed_local_artifacts():
    """Ensure local artifacts are removed by uninstaller."""
    script = _read_script("win_installers/uninstall_usbip_on_windows.bat")

    assert 'del "%USERPROFILE%\\Desktop\\USBIP Manager.lnk"' in script
    assert 'rmdir /s /q ".pixi"' in script
    assert "winget uninstall --id dorssel.usbipd-win --silent" in script


def test_uninstall_handles_usbip_win2_msi_and_exe_paths():
    """Ensure usbip-win2 uninstall supports MSI and EXE registry commands."""
    script = _read_script("win_installers/uninstall_usbip_on_windows.bat")

    assert "$app.QuietUninstallString" in script
    assert (
        "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"
        in script
    )
    assert "DisplayName -match 'usbip-win2^|USBip'" in script
    assert "InstallLocation -like '*\\USBip*'" in script
    assert "if ^($app.UninstallString -match 'msiexec'^)" in script
    assert "if ^($app.UninstallString -match '{[0-9A-Fa-f-]+}'^)" in script
    assert (
        'Start-Process msiexec.exe -Wait -ArgumentList "/x $productCode'
        in script
    )
    assert (
        'Start-Process cmd.exe -Wait -ArgumentList "/c '
        '$^($app.UninstallString^) /VERYSILENT /SUPPRESSMSGBOXES /NORESTART"'
        in script
    )


def test_uninstall_escapes_parentheses_in_echoed_ps_lines():
    """
    Ensure cmd parser-safe escaping is present in echoed PowerShell lines.
    """
    script = _read_script("win_installers/uninstall_usbip_on_windows.bat")

    assert "echo foreach ^($app in $apps^) {" in script
    assert "echo     if ^($app.QuietUninstallString^) {" in script
    assert (
        "echo         Start-Process cmd.exe -Wait -ArgumentList "
        '"/c $^($app.QuietUninstallString^)"' in script
    )


def test_uninstall_status_messages_are_clean_for_console_output():
    """Ensure user-facing status messages do not include caret escapes."""
    script = _read_script("win_installers/uninstall_usbip_on_windows.bat")

    assert 'Write-Host "Uninstalling usbipd-win Server..."' in script
    assert 'Write-Host "Uninstalling usbip client tools..."' in script


def test_uninstall_has_legacy_usbip_fallback_cleanup():
    """
    Ensure script removes legacy USBip app if registry uninstall misses it.
    """
    script = _read_script("win_installers/uninstall_usbip_on_windows.bat")

    assert (
        "$legacyAppPath = Join-Path $env:ProgramFiles 'USBip\\wusbip.exe'"
        in script
    )
    assert "Get-Process -Name 'wusbip'" in script
    assert "Get-ChildItem -Path $legacyDir -Filter 'unins*.exe'" in script
    assert "Start-Process -FilePath $inno.FullName -Wait" in script
    assert "Remove-Item -Path $legacyDir -Recurse -Force" in script


def test_uninstall_explicitly_keeps_shared_tools():
    """Ensure script warns that shared global dependencies are not removed."""
    script = _read_script("win_installers/uninstall_usbip_on_windows.bat")

    assert (
        "global 'pixi' package manager and Python runtime were NOT" in script
    )
    assert "uninstall Python from Windows Apps settings" in script
