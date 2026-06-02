@echo off
setlocal EnableExtensions

echo ==============================================================
echo   NETEXEC -- Windows Application Installer
echo ==============================================================
echo.

:: Require administrator rights (needed to write to Program Files)
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: This installer must be run as Administrator.
    echo Right-click install_windows.bat and choose "Run as administrator".
    echo.
    pause
    exit /b 1
)

set "SETUP_DIR=%~dp0"
set "GAME_SRC=%SETUP_DIR%..\netexec-main"
set "INSTALL_DIR=%PROGRAMFILES%\NetExecutive"

:: Verify netexec-main/ exists
if not exist "%GAME_SRC%\" (
    echo ERROR: netexec-main\ folder not found.
    echo Make sure netexec-setup\ and netexec-main\ are in the same folder.
    echo.
    pause
    exit /b 1
)

:: Resolve absolute path to avoid nested-copy issues
pushd "%GAME_SRC%" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Could not access netexec-main\ folder.
    pause
    exit /b 1
)
set "GAME_SRC=%CD%"
popd

echo [1/3]  Installing game files...
echo   Source      : %GAME_SRC%
echo   Destination : %INSTALL_DIR%
echo.

:: Remove previous install for a clean copy
if exist "%INSTALL_DIR%\" (
    echo   Removing previous install...
    rmdir /s /q "%INSTALL_DIR%" >nul 2>&1
)

:: Copy game files
where robocopy >nul 2>&1
if %ERRORLEVEL%==0 (
    echo   Copying files with robocopy...
    robocopy "%GAME_SRC%" "%INSTALL_DIR%" /MIR /XD "__pycache__" /XF "*.pyc" "*.pyo" /NFL /NDL /NJH /NJS /R:3 /W:1 >nul
    if errorlevel 8 (
        echo   ERROR: robocopy reported failure.
        pause
        exit /b 1
    )
) else (
    echo   Copying files with xcopy...
    xcopy /e /i /q /y "%GAME_SRC%\*" "%INSTALL_DIR%\" >nul
    if errorlevel 1 (
        echo   ERROR: file copy failed.
        pause
        exit /b 1
    )
)
echo   Game files installed.

:: Back up and clear old user settings so new defaults take effect
echo.
echo [2/3]  Backing up and clearing old user settings...
set "USER_SETTINGS=%APPDATA%\NETEXEC"
if exist "%USER_SETTINGS%\" (
    set "BACKUP_DIR=%INSTALL_DIR%\settings-backups"
    if not exist "%BACKUP_DIR%\" mkdir "%BACKUP_DIR%"
    for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd-HHmmss'"`) do set "TS=%%T"
    set "ZIPPATH=%BACKUP_DIR%\NETEXEC-settings-%TS%.zip"
    powershell -NoProfile -Command "try { Compress-Archive -Path (Join-Path '%USER_SETTINGS%' '*') -DestinationPath '%ZIPPATH%' -Force; exit 0 } catch { exit 1 }"
    if errorlevel 1 (
        robocopy "%USER_SETTINGS%" "%BACKUP_DIR%\NETEXEC-settings-%TS%" /MIR /NFL /NDL /NJH /NJS /R:1 /W:1 >nul
        echo   Settings copied to backup folder.
    ) else (
        echo   Settings backed up to: %ZIPPATH%
    )
    rmdir /s /q "%USER_SETTINGS%" >nul 2>&1
    echo   Old settings cleared. Game will start with fresh defaults.
) else (
    echo   No previous settings found.
)

:: Create Desktop and Start Menu shortcuts
echo.
echo [3/3]  Creating shortcuts...

:: Resolve Desktop path (handles OneDrive-relocated Desktop)
for /f "usebackq delims=" %%D in (
    `powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`
) do set "DESKTOP=%%D"

set "EXE=%INSTALL_DIR%\NETEXEC.exe"
set "DESKTOP_LNK=%DESKTOP%\NetExecutive.lnk"
set "START_LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\NetExecutive.lnk"

if not exist "%EXE%" (
    echo   WARNING: NETEXEC.exe not found in install dir -- shortcuts skipped.
    goto done
)

:: Desktop shortcut
powershell -NoProfile -NonInteractive -Command "$ws=New-Object -ComObject WScript.Shell; $sc=$ws.CreateShortcut('%DESKTOP_LNK%'); $sc.TargetPath='%EXE%'; $sc.WorkingDirectory='%INSTALL_DIR%'; $sc.Description='NETEXEC: Network Executive Simulator'; $sc.Save()"
if exist "%DESKTOP_LNK%" (
    echo   Desktop shortcut  : %DESKTOP_LNK%
) else (
    echo   WARNING: Desktop shortcut could not be created.
)

:: Start Menu shortcut
powershell -NoProfile -NonInteractive -Command "$ws=New-Object -ComObject WScript.Shell; $sc=$ws.CreateShortcut('%START_LNK%'); $sc.TargetPath='%EXE%'; $sc.WorkingDirectory='%INSTALL_DIR%'; $sc.Description='NETEXEC: Network Executive Simulator'; $sc.Save()"
if exist "%START_LNK%" (
    echo   Start Menu        : %START_LNK%
) else (
    echo   WARNING: Start Menu shortcut could not be created.
)

:done
echo.
echo   Installation complete!
echo   Launch NetExecutive from your Desktop or Start Menu.
echo   Game files : %INSTALL_DIR%\NETEXEC.exe
echo   Saves      : %%APPDATA%%\NETEXEC\
echo ==============================================================
echo.
pause
