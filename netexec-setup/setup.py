"""
setup.py — NETEXEC Installer (cross-platform)
===============================================
Installs NETEXEC to the system application directory and creates a
desktop shortcut. Run from the netexec-setup/ folder (or any directory):

    python setup.py

The script locates netexec-main/ as a sibling of the netexec-setup/ folder.

Destination
-----------
  Windows : %PROGRAMFILES%\\NetExecutive\\    ← system Applications (requires admin)
  macOS   : /Applications/NETEXEC.app         ← system Applications
  Linux   : ~/.local/share/netexec/

Desktop shortcut
----------------
  Windows : NetExecutive.lnk → points to NETEXEC.exe (the single game executable)
  macOS   : NetExecutive.app → symlink to /Applications/NETEXEC.app (the single game app)
  Linux   : NETEXEC.desktop in ~/Desktop/

NOTE: On Windows, run this script as Administrator so it can write to Program Files.
      Alternatively, use install_windows.bat which handles the admin elevation prompt.
      On macOS, use install_macos.sh for the same /Applications install with Desktop alias.

Saves are always written to the user-data area (not the install dir):
  Windows : %APPDATA%\\NETEXEC\\
  macOS   : ~/.config/NETEXEC/
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path


# ─── paths ────────────────────────────────────────────────────────────────────

def _game_dir() -> Path:
    # netexec-setup/ is a sibling of netexec-main/
    here = Path(__file__).parent
    gp = here.parent / "netexec-main"
    if not gp.is_dir():
        sys.exit(f"ERROR: netexec-main/ not found at {gp}\n"
                 "Make sure netexec-setup/ and netexec-main/ are in the same folder.")
    return gp


def _install_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        return base / "NetExecutive"
    if sys.platform == "darwin":
        return Path("/Applications/NETEXEC.app")
    return Path.home() / ".local" / "share" / "netexec"


def _desktop_dir() -> Path:
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
            ) as key:
                val, _ = winreg.QueryValueEx(key, "Desktop")
                return Path(val)
        except Exception:
            pass
        return Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"
    return Path.home() / "Desktop"


# ─── install ──────────────────────────────────────────────────────────────────

def _copy_files(src: Path, dst: Path) -> None:
    print(f"  Source      : {src}")
    print(f"  Destination : {dst}")
    if dst.exists():
        print("  Removing previous install...")
        try:
            shutil.rmtree(dst)
        except Exception as e:
            print(f"  WARNING: First removal attempt failed ({e}), retrying...")
            import time
            time.sleep(0.5)
            try:
                shutil.rmtree(dst)
            except Exception as e2:
                sys.exit(f"ERROR: Failed to remove old install: {e2}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.copytree(
            src, dst,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
    except Exception as e:
        sys.exit(f"ERROR: Failed to copy new files: {e}")
    print("  Files installed.")


# ─── shortcuts ────────────────────────────────────────────────────────────────

def _shortcut_windows(install_dir: Path) -> None:
    exe = install_dir / "NETEXEC.exe"
    if not exe.exists():
        print(f"  WARNING: NETEXEC.exe not found -- shortcut skipped.")
        return
    desktop = _desktop_dir()
    lnk = desktop / "NetExecutive.lnk"
    start_lnk = (Path(os.environ.get("APPDATA", "")) /
                 "Microsoft" / "Windows" / "Start Menu" / "Programs" / "NetExecutive.lnk")
    ps = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f'$sc = $ws.CreateShortcut("{lnk}"); '
        f'$sc.TargetPath = "{exe}"; '
        f'$sc.WorkingDirectory = "{install_dir}"; '
        '$sc.Description = "NETEXEC: Network Executive Simulator"; '
        "$sc.Save(); "
        f'$sc2 = $ws.CreateShortcut("{start_lnk}"); '
        f'$sc2.TargetPath = "{exe}"; '
        f'$sc2.WorkingDirectory = "{install_dir}"; '
        '$sc2.Description = "NETEXEC: Network Executive Simulator"; '
        "$sc2.Save()"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        if lnk.exists():
            print(f"  Desktop shortcut  : {lnk}")
        if start_lnk.exists():
            print(f"  Start Menu        : {start_lnk}")
    else:
        print(f"  WARNING: could not create shortcuts -- {result.stderr.strip() or 'unknown error'}")


def _shortcut_macos(install_dir: Path) -> None:
    desktop = _desktop_dir()
    if not desktop.exists():
        print("  WARNING: Desktop not found -- shortcut skipped.")
        return
    # install_dir IS the .app bundle on macOS
    link = desktop / "NetExecutive.app"
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(install_dir)
    print(f"  Desktop shortcut : {link}  ->  {install_dir}")


def _shortcut_linux(install_dir: Path) -> None:
    desktop = _desktop_dir()
    if not desktop.exists():
        print("  No Desktop directory found -- shortcut skipped.")
        return
    launcher = install_dir / "run_game.sh"
    entry = desktop / "NETEXEC.desktop"
    entry.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=NETEXEC\n"
        "Comment=Network Executive Simulator\n"
        f"Exec=bash {launcher}\n"
        f"Path={install_dir}\n"
        "Terminal=false\n"
        "Categories=Game;\n",
        encoding="utf-8",
    )
    entry.chmod(0o755)
    print(f"  Desktop shortcut : {entry}")


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 62)
    print("  NETEXEC -- Setup Installer")
    print("=" * 62)

    if sys.platform == "win32":
        print("\n  NOTE: Run as Administrator to install to Program Files.")

    src = _game_dir()
    dst = _install_dir()

    # On macOS the install target IS NETEXEC.app, so copy the .app bundle
    if sys.platform == "darwin":
        src = src / "NETEXEC.app"
        if not src.exists():
            sys.exit(f"ERROR: NETEXEC.app not found at {src}")

    print("\n[1/2]  Installing game files...")
    _copy_files(src, dst)

    print("\n[2/2]  Creating desktop shortcut...")
    if sys.platform == "win32":
        _shortcut_windows(dst)
    elif sys.platform == "darwin":
        _shortcut_macos(dst)
    else:
        _shortcut_linux(dst)

    print("\n  Installation complete!")
    if sys.platform == "win32":
        print(f"  Executable   : {dst}\\NETEXEC.exe")
        print(r"  Saves stored : %APPDATA%\NETEXEC\ ")
    elif sys.platform == "darwin":
        print(f"  App          : {dst}")
        print("  Saves stored : ~/.config/NETEXEC/")
    else:
        print(f"  Run game     : bash {dst}/run_game.sh")
        print("  Saves stored : ~/.config/NETEXEC/")
    print("=" * 62)


if __name__ == "__main__":
    main()
