Set objShell = WScript.CreateObject("WScript.Shell")
Dim FSO
Set FSO = CreateObject("Scripting.FileSystemObject")
Dim strPath
strPath = FSO.GetParentFolderName(WScript.ScriptFullName)

' Check if --debug was passed
Dim isDebug, args, arg
isDebug = False
Set args = WScript.Arguments
For Each arg In args
    If LCase(arg) = "--debug" Then
        isDebug = True
    End If
Next

Dim windowStyle
If isDebug Then
    windowStyle = 1 ' Normal window
Else
    windowStyle = 0 ' Hidden window
End If

objShell.Run Chr(34) & strPath & "\launch.bat" & Chr(34), windowStyle, False
