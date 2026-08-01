; ==============================================================================
; USB/IP Manager Windows Installer Script
; ==============================================================================
; Publisher: Sheldon Maschmeyer
; Target OS: Windows 11
; Description:
;   This script packages the USB/IP Manager GUI application, including installing
;   all system-level driver dependencies (usbipd-win, usbip-win2) and user-level
;   runtime requirements (Python, Pixi). It leverages native winget commands
;   and bundled PowerShell scripts to ensure a smooth, AV-friendly installation.
; ==============================================================================

[Setup]
; ------------------------------------------------------------------------------
; Application Metadata
; ------------------------------------------------------------------------------
AppName=USB/IP Manager
AppVersion=1.7.0
AppPublisher=Sheldon Maschmeyer
AppPublisherURL=https://maschmeyer.ca
AppSupportURL=https://github.com/sheldonmaschmeyer/usbip-gui
AppUpdatesURL=https://github.com/sheldonmaschmeyer/usbip-gui

; ------------------------------------------------------------------------------
; Installation Directories and Settings
; ------------------------------------------------------------------------------
; {autopf} resolves to Program Files (x86) or Program Files depending on architecture
DefaultDirName={autopf}\USBIP Manager
DefaultGroupName=USB/IP Manager

; Output configurations for the generated executable
OutputDir=.
OutputBaseFilename=USBIP_Manager_Setup
Compression=lzma
SolidCompression=yes

; Requires Administrative privileges to install system USB drivers (usbipd-win)
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64os
WizardStyle=modern
UninstallDisplayIcon={app}\icon\usbip-logo.ico

[Types]
; ------------------------------------------------------------------------------
; Installation Types
; ------------------------------------------------------------------------------
Name: "full"; Description: "Full installation (Recommended)"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
; ------------------------------------------------------------------------------
; Selectable Components
; These are dynamically checked/unchecked via the [Code] section based on what
; the user already has installed on their machine.
; ------------------------------------------------------------------------------
Name: "core"; Description: "USB/IP Manager App Files (Required)"; Types: full custom; Flags: fixed
Name: "server"; Description: "USBIP Server Driver (usbipd-win)"; Types: full custom
Name: "client"; Description: "USBIP Client Driver (usbip-win2)"; Types: full custom
Name: "python"; Description: "Python 3 Runtime"; Types: full custom
Name: "pixi"; Description: "Pixi Package Manager"; Types: full custom

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; ------------------------------------------------------------------------------
; Files to Package
; ------------------------------------------------------------------------------
; Application Files (Excludes dev and temporary files)
Source: "..\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".git\*,.github\*,.vscode\*,win_installers\*,htmlcov\*,.pytest_cache\*,.mypy_cache\*,.pixi\*,*__pycache__*"

; Bundled Helper Scripts
; The client installation script is deleted immediately after the setup completes
Source: "scripts\install_usbip_client.ps1"; DestDir: "{tmp}"; Flags: deleteafterinstall
; Launchers and uninstaller scripts persist in the app directory
Source: "scripts\uninstall_usbip_drivers.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\launch.bat"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\launch.vbs"; DestDir: "{app}\scripts"; Flags: ignoreversion

[Dirs]
; ------------------------------------------------------------------------------
; Directory Permissions
; ------------------------------------------------------------------------------
; Grants standard users write access to the {app} directory. 
; Required because `pixi run` modifies the local `.pixi` cache directory.
Name: "{app}"; Permissions: users-modify

[Icons]
; ------------------------------------------------------------------------------
; Shortcuts
; Targets the VBScript wrapper to launch the application completely hidden,
; avoiding any lingering or flashing command prompt windows.
; ------------------------------------------------------------------------------
Name: "{autodesktop}\USBIP Manager"; Filename: "{app}\scripts\launch.vbs"; WorkingDir: "{app}"; IconFilename: "{app}\icon\usbip-logo.ico"; Tasks: desktopicon
Name: "{group}\USBIP Manager"; Filename: "{app}\scripts\launch.vbs"; WorkingDir: "{app}"; IconFilename: "{app}\icon\usbip-logo.ico"

[Run]
; ------------------------------------------------------------------------------
; Execution Phase (Run after files are extracted)
; ------------------------------------------------------------------------------
; Install usbipd-win Server Driver
Filename: "winget"; Parameters: "install --id dorssel.usbipd-win --accept-package-agreements --accept-source-agreements --silent"; Components: server; Flags: waituntilterminated runhidden; StatusMsg: "Installing USBIP Server Driver (usbipd-win)..."

; Install usbip-win2 Client Driver
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -WindowStyle Hidden -File ""{tmp}\install_usbip_client.ps1"""; Components: client; Flags: waituntilterminated runhidden; StatusMsg: "Installing USBIP Client Driver (usbip-win2)..."

; Install Python 3
Filename: "winget"; Parameters: "install --id Python.Python.3 --accept-package-agreements --accept-source-agreements --silent"; Components: python; Flags: waituntilterminated runhidden; StatusMsg: "Installing Python 3..."

; Install Pixi
Filename: "winget"; Parameters: "install --id prefix-dev.pixi --accept-source-agreements --accept-package-agreements --silent"; Components: pixi; Flags: waituntilterminated runhidden; StatusMsg: "Installing Pixi Package Manager..."

; Install App Dependencies
; Runs as the original un-elevated user to ensure pixi installs local packages correctly
Filename: "cmd.exe"; Parameters: "/c ""set PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%LOCALAPPDATA%\pixi\bin;%USERPROFILE%\.pixi\bin;%PATH% && pixi install"""; WorkingDir: "{app}"; Flags: waituntilterminated runhidden runasoriginaluser; StatusMsg: "Installing Python App Dependencies via Pixi..."

[UninstallDelete]
; ------------------------------------------------------------------------------
; Uninstallation Cleanups
; ------------------------------------------------------------------------------
; Removes the local pixi environment cache created during runtime
Type: filesandordirs; Name: "{app}\.pixi"

[Code]
// ==============================================================================
// Pascal Script Logic
// Handles dynamic component checking and custom uninstallation prompts.
// ==============================================================================

var
  ComponentsChecked: Boolean;

{
  CurPageChanged
  Fires when the installer moves to a new page.
  Used here to inspect the user's system and automatically uncheck dependencies
  if they are already installed, preventing redundant installations.
}
procedure CurPageChanged(CurPageID: Integer);
var
  ResultCode: Integer;
begin
  if (CurPageID = wpSelectComponents) and not ComponentsChecked then
  begin
    ComponentsChecked := True;
    
    // Check if usbipd.exe (server) is installed
    if Exec('cmd.exe', '/c winget list --exact --id dorssel.usbipd-win --accept-source-agreements', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      if ResultCode = 0 then
        WizardForm.ComponentsList.Checked[1] := False; // Server installed, uncheck
    end;
    
    // Check if usbip.exe (client) is installed
    if Exec('cmd.exe', '/c where usbip.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      if ResultCode = 0 then
        WizardForm.ComponentsList.Checked[2] := False; // Client installed, uncheck
    end;

    // Check if python is installed
    if Exec('cmd.exe', '/c where python', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      if ResultCode = 0 then
        WizardForm.ComponentsList.Checked[3] := False // Python installed, uncheck
      else
      begin
        // Fallback check for 'py' launcher
        if Exec('cmd.exe', '/c where py', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
        begin
          if ResultCode = 0 then
            WizardForm.ComponentsList.Checked[3] := False; // Py installed, uncheck
        end;
      end;
    end;

    // Check if pixi is installed
    if Exec('cmd.exe', '/c where pixi', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      if ResultCode = 0 then
        WizardForm.ComponentsList.Checked[4] := False; // Pixi installed, uncheck
    end;
  end;
end;

{
  CurUninstallStepChanged
  Fires during the uninstallation lifecycle.
  Prompts the user to remove the system-level USB/IP drivers. If approved,
  it executes the bundled PowerShell cleanup script.
}
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    if MsgBox('The system USB/IP drivers (usbipd-win and usbip-win2) might be in use by other applications.' + #13#10 + #13#10 + 'Do you want to completely uninstall them?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec('powershell.exe', '-ExecutionPolicy Bypass -WindowStyle Hidden -File "' + ExpandConstant('{app}\scripts\uninstall_usbip_drivers.ps1') + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;
