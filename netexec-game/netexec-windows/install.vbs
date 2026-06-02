' install.vbs -- NETEXEC Windows Installer
'
' Double-click this file to install NETEXEC: Network Executive Simulator.
' No terminal window required. Administrator rights are requested automatically.
'
' What this installer does:
'   1. Requests administrator rights via UAC prompt (required for Program Files)
'   2. Copies the game from netexec-main\ to %PROGRAMFILES%\NetExecutive\
'   3. Creates a Desktop shortcut and Start Menu entry
'
' NETEXEC.exe must already be present in ..\netexec-main\ before running this.
' Run build_game.py first if the exe is missing.

Option Explicit

Dim WshShell, FSO
Set WshShell = CreateObject("WScript.Shell")
Set FSO      = CreateObject("Scripting.FileSystemObject")

' ── Admin elevation ───────────────────────────────────────────────────────────
' On first run (no argument) request elevation and re-launch.
' On second run (argument = "ELEVATED") proceed as admin.
If WScript.Arguments.Count = 0 Then
    Dim Shell
    Set Shell = CreateObject("Shell.Application")
    Shell.ShellExecute "wscript.exe", _
        Chr(34) & WScript.ScriptFullName & Chr(34) & " ELEVATED", _
        "", "runas", 1
    WScript.Quit
End If

' ── Paths ─────────────────────────────────────────────────────────────────────
' ScriptDir = netexec-windows\
' GameSrc   = netexec-main\   (..\netexec-main from ScriptDir = repo root)
Dim ScriptDir, GameSrc, InstallDir
ScriptDir  = FSO.GetParentFolderName(WScript.ScriptFullName)
GameSrc    = FSO.GetAbsolutePathName(ScriptDir & "\..\netexec-main")
InstallDir = WshShell.ExpandEnvironmentStrings("%PROGRAMFILES%") & "\NetExecutive"

' ── Verify source folder ──────────────────────────────────────────────────────
If Not FSO.FolderExists(GameSrc) Then
    MsgBox "ERROR: Game folder not found." & vbCrLf & _
           "Expected: " & GameSrc & vbCrLf & vbCrLf & _
           "Make sure netexec-main\ is in the same parent folder as netexec-windows\.", _
           vbCritical, "NETEXEC Installer"
    WScript.Quit 1
End If

Dim ExePath : ExePath = GameSrc & "\NETEXEC.exe"
If Not FSO.FileExists(ExePath) Then
    MsgBox "ERROR: NETEXEC.exe not found." & vbCrLf & _
           "Expected: " & ExePath & vbCrLf & vbCrLf & _
           "Run build_game.py first to produce the game executable.", _
           vbCritical, "NETEXEC Installer"
    WScript.Quit 1
End If

' ── Confirm install ───────────────────────────────────────────────────────────
Dim Ans
Ans = MsgBox("Install NETEXEC: Network Executive Simulator?" & vbCrLf & vbCrLf & _
             "Install location:" & vbCrLf & "   " & InstallDir, _
             vbYesNo + vbQuestion, "NETEXEC Installer")
If Ans <> vbYes Then WScript.Quit 0

' ── Remove previous install ───────────────────────────────────────────────────
If FSO.FolderExists(InstallDir) Then
    On Error Resume Next
    FSO.DeleteFolder InstallDir, True
    If Err.Number <> 0 Then
        MsgBox "ERROR: Could not remove the previous install." & vbCrLf & _
               Err.Description & vbCrLf & vbCrLf & _
               "Close any running NETEXEC windows and try again.", _
               vbCritical, "NETEXEC Installer"
        WScript.Quit 1
    End If
    On Error GoTo 0
End If

' ── Copy game files ───────────────────────────────────────────────────────────
On Error Resume Next
FSO.CopyFolder GameSrc, InstallDir, True
If Err.Number <> 0 Then
    MsgBox "ERROR: Could not copy game files." & vbCrLf & _
           Err.Description, vbCritical, "NETEXEC Installer"
    WScript.Quit 1
End If
On Error GoTo 0

' ── Create shortcuts ──────────────────────────────────────────────────────────
Dim InstalledExe : InstalledExe = InstallDir & "\NETEXEC.exe"

If FSO.FileExists(InstalledExe) Then
    Dim SC

    ' Desktop shortcut
    Dim DesktopPath : DesktopPath = WshShell.SpecialFolders("Desktop")
    Set SC = WshShell.CreateShortcut(DesktopPath & "\NetExecutive.lnk")
    SC.TargetPath       = InstalledExe
    SC.WorkingDirectory = InstallDir
    SC.Description      = "NETEXEC: Network Executive Simulator"
    SC.Save

    ' Start Menu shortcut
    Dim StartPath
    StartPath = WshShell.ExpandEnvironmentStrings("%APPDATA%") & _
                "\Microsoft\Windows\Start Menu\Programs\NetExecutive.lnk"
    Set SC = WshShell.CreateShortcut(StartPath)
    SC.TargetPath       = InstalledExe
    SC.WorkingDirectory = InstallDir
    SC.Description      = "NETEXEC: Network Executive Simulator"
    SC.Save
End If

' ── Done ──────────────────────────────────────────────────────────────────────
MsgBox "NETEXEC installed successfully!" & vbCrLf & vbCrLf & _
       "Launch the game from your Desktop or Start Menu.", _
       vbInformation, "NETEXEC Installer"

WshShell  = Nothing
FSO       = Nothing
