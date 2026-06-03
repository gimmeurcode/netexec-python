' install.vbs -- NETEXEC Windows Installer
'
' Double-click this file to build and install NETEXEC.
' No terminal window required.
' Administrator rights are requested automatically.
'
' What this script does:
'   1. Finds Python and rebuilds NETEXEC.exe from the latest source code.
'   2. Requests administrator rights via UAC (required to write to Program Files).
'   3. Copies the fresh exe + assets to %PROGRAMFILES%\NetExecutive\.
'   4. Creates a Desktop shortcut and a Start Menu entry.
'   5. Launches the game immediately.
'
' The installed game is fully self-contained -- players need no extra software.
Option Explicit

Dim WshShell, FSO
Set WshShell = CreateObject("WScript.Shell")
Set FSO      = CreateObject("Scripting.FileSystemObject")

' ── Paths ─────────────────────────────────────────────────────────────────────
' ScriptDir = installers\windows\ — two levels deep, so repo root is ..\..
Dim ScriptDir, RepoRoot, GameSrc, BuildScript, InstallDir
ScriptDir   = FSO.GetParentFolderName(WScript.ScriptFullName)
RepoRoot    = FSO.GetAbsolutePathName(ScriptDir & "\..\..")
GameSrc     = RepoRoot & "\src"
BuildScript = RepoRoot & "\dev\build\build_game.py"
InstallDir  = WshShell.ExpandEnvironmentStrings("%PROGRAMFILES%") & "\NetExecutive"
Dim ExePath : ExePath = RepoRoot & "\dist\NETEXEC.exe"

' =============================================================================
' PHASE 1  (non-elevated, first run)
'   Build the exe from source, then re-launch elevated for the install step.
' =============================================================================
If WScript.Arguments.Count = 0 Then

    ' ── Verify source folder ──────────────────────────────────────────────────
    If Not FSO.FolderExists(GameSrc) Then
        MsgBox "ERROR: Game source folder not found." & vbCrLf & _
               "Expected: " & GameSrc, vbCritical, "NETEXEC Installer"
        WScript.Quit 1
    End If

    ' ── Build from source (repo workflow) or use pre-built exe (zip workflow) ─
    ' If build_game.py is present, always rebuild so the install is up-to-date.
    ' If it is absent (player zip), use the pre-built NETEXEC.exe in netexec-main/.
    If FSO.FileExists(BuildScript) Then
        Dim PyExe : PyExe = FindPython()
        If PyExe = "" Then
            MsgBox "ERROR: Python 3 not found on this machine." & vbCrLf & vbCrLf & _
                   "Install Python 3.11+ from https://python.org" & vbCrLf & _
                   "and make sure it is added to PATH.", _
                   vbCritical, "NETEXEC Installer"
            WScript.Quit 1
        End If

        ' Run in a visible window so the user can see build progress.
        Dim BuildCmd : BuildCmd = PyExe & " """ & BuildScript & """"
        Dim BuildRet : BuildRet = WshShell.Run(BuildCmd, 1, True)
        If BuildRet <> 0 Then
            MsgBox "Build failed (exit code " & BuildRet & ")." & vbCrLf & _
                   "See the build window for details.", _
                   vbCritical, "NETEXEC Installer"
            WScript.Quit 1
        End If
    ElseIf Not FSO.FileExists(ExePath) Then
        MsgBox "ERROR: NETEXEC.exe not found and build script is missing." & vbCrLf & _
               "Expected pre-built exe at: " & ExePath, vbCritical, "NETEXEC Installer"
        WScript.Quit 1
    End If

    ' ── Request elevation for the install step ────────────────────────────────
    Dim ElevShell
    Set ElevShell = CreateObject("Shell.Application")
    
    On Error Resume Next ' Prevent crash if UAC is declined
    ElevShell.ShellExecute "wscript.exe", _
        Chr(34) & WScript.ScriptFullName & Chr(34) & " ELEVATED", _
        "", "runas", 1
        
    ' Handle potential cancellation gracefully
    If Err.Number <> 0 Then
        If Err.Number = &H800704C7 Or Err.Number = -2147023673 Then
            MsgBox "Installation canceled: Administrator permissions are required to install the game to your Program Files.", vbInformation, "NETEXEC Installer"
        Else
            MsgBox "An unexpected error occurred while requesting permissions: " & Err.Description, vbCritical, "NETEXEC Installer"
        End If
    End If
    On Error GoTo 0 ' Resume normal error handling
   
    WScript.Quit

End If

' =============================================================================
' PHASE 2  (elevated)
'   Verify the freshly built exe, copy files, create shortcuts, launch game.
' =============================================================================

' ── Verify exe produced by the build ─────────────────────────────────────────
If Not FSO.FileExists(ExePath) Then
    MsgBox "ERROR: NETEXEC.exe was not produced by the build." & vbCrLf & _
           "Expected: " & ExePath, vbCritical, "NETEXEC Installer"
    WScript.Quit 1
End If

Dim ExeDate : ExeDate = FSO.GetFile(ExePath).DateLastModified

' ── Confirm ───────────────────────────────────────────────────────────────────
Dim Ans
Ans = MsgBox("Install NETEXEC: Network Executive Simulator?" & vbCrLf & vbCrLf & _
             "Built  : " & ExeDate & vbCrLf & _
             "To     : " & InstallDir, _
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
FSO.CopyFolder RepoRoot & "\dist", InstallDir, True
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

    Dim DesktopPath : DesktopPath = WshShell.SpecialFolders("Desktop")
    Set SC = WshShell.CreateShortcut(DesktopPath & "\NetExecutive.lnk")
    SC.TargetPath       = InstalledExe
    SC.WorkingDirectory = InstallDir
    SC.Description      = "NETEXEC: Network Executive Simulator"
    SC.Save

    Dim StartPath
    StartPath = WshShell.ExpandEnvironmentStrings("%APPDATA%") & _
                "\Microsoft\Windows\Start Menu\Programs\NetExecutive.lnk"
    Set SC = WshShell.CreateShortcut(StartPath)
    SC.TargetPath       = InstalledExe
    SC.WorkingDirectory = InstallDir
    SC.Description      = "NETEXEC: Network Executive Simulator"
    SC.Save
End If

' ── Launch ────────────────────────────────────────────────────────────────────
WshShell.Run Chr(34) & InstalledExe & Chr(34), 1, False

Set WshShell = Nothing
Set FSO      = Nothing
WScript.Quit 0


' =============================================================================
' FindPython  —  returns "py", "python", or "python3", whichever responds first.
'               Returns "" if none found.
' =============================================================================
Function FindPython()
    FindPython = ""
    Dim c
    For Each c In Array("py", "python", "python3")
        On Error Resume Next
        Dim r : r = WshShell.Run("cmd /c " & c & " --version > nul 2>&1", 0, True)
        If Err.Number = 0 And r = 0 Then
            FindPython = c
            On Error GoTo 0
            Exit For
        End If
        Err.Clear
        On Error GoTo 0
    Next
End Function