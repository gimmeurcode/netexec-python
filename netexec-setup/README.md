# NETEXEC — Installer

| Platform | Game executable | Installer                                       |
|----------|-----------------|-------------------------------------------------|
| Windows  | `NETEXEC.exe`   | `install_windows.bat` (run as Administrator)    |
| macOS    | `NETEXEC.app`   | `install_macos.sh`                              |

Both executables live in the sibling `netexec-main/` folder. The installers copy them to
the system Applications directory and create a clickable desktop shortcut.

---

## Windows

**Right-click `install_windows.bat` → Run as administrator**

What it does:
1. Copies game files to `C:\Program Files\NetExecutive\`
2. Backs up and clears any old user settings so the latest defaults apply
3. Creates `NetExecutive.lnk` on your Desktop → `NETEXEC.exe`
4. Creates `NetExecutive.lnk` in Start Menu → Programs

> **Saves** are stored in `%APPDATA%\NETEXEC\` — separate from the install folder.

---

## macOS

Open Terminal in this folder and run:

```bash
bash install_macos.sh
```

What it does:
1. Copies `NETEXEC.app` to `/Applications/`
2. Backs up and clears any old user settings
3. Creates `NetExecutive.app` on your Desktop → `/Applications/NETEXEC.app`

After installation, double-click the Desktop icon or open NETEXEC from Applications.

> **Saves** are stored in `~/.config/NETEXEC/` — separate from the install folder.

---

## Alternative: Python installer (all platforms including Linux)

If you have Python 3.9+ installed:

```bash
python setup.py
```

Installs to the same location as the platform-specific scripts above.
On Windows, run from an Administrator command prompt.

---

## Uninstall

**Windows:** Delete `C:\Program Files\NetExecutive\` and the Desktop/Start Menu shortcuts.

**macOS:** Delete `/Applications/NETEXEC.app` and the Desktop symlink.

Saves are in `%APPDATA%\NETEXEC\` (Windows) or `~/.config/NETEXEC/` (macOS/Linux). Delete
that folder to remove save data.

---

## Troubleshooting

- **"netexec-main folder not found"**: Keep `netexec-setup/` and `netexec-main/` in the same parent folder.
- **Windows "Access is denied"**: Right-click `install_windows.bat` → Run as administrator.
- **macOS Gatekeeper warning on NETEXEC.app**: Right-click → Open → Open. One-time only.
