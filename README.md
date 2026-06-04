# NETEXEC — Network Executive Simulator

A turn-based strategy game where you run a television network. Schedule shows, sign stars, sell ads, and grow your viewership over 12 seasons. Hit the ratings quotas or get iced.

---

## Download and Install

### Windows

1. Click the green **Code** button on this page → **Download ZIP**.
2. Extract the ZIP to any folder (e.g. `Documents\NETEXEC`).
3. Open `installers\windows\` and double-click **`install.vbs`**.
4. Click **Yes** when Windows asks for administrator permission.
5. Click **Yes** to confirm install.
6. Launch **NetExecutive** from your Desktop or Start Menu.

> Saves are stored at `%APPDATA%\NETEXEC\`. No Python required.

---

### macOS

1. Click the green **Code** button on this page → **Download ZIP**.
2. Extract the ZIP to any folder.
3. Open `installers/macos/` and double-click **`install.command`**.
   - macOS opens a Terminal window, runs the install, and closes it automatically.
   - If macOS blocks it ("unidentified developer"): right-click the file → **Open** → **Open**.
4. Launch **NetExecutive** from `/Applications` or your Desktop.

> Saves are stored at `~/.config/NETEXEC/`. No Python required.

---

### Run from source (Python)

Requires **Python 3.11+**:

```bash
pip install pygame-ce numpy moderngl glcontext
cd src
python main.py
```

---

## How to Play

1. **Select a difficulty** — Easy / Normal / Hard / Brutal.
2. **Buy items from the shop** (right panel): Shows, Stars, Ads, Upgrades, and Events.
3. **Schedule 4 shows** into the time slots on the left panel.
4. **Attach Stars and Ads** to shows to boost views and income.
5. **Click AIR SEASON** to simulate the season.
6. **Hit the view quota** every 3 seasons (Seasons 3, 6, 9, 12) to stay on air.
7. **Win** by completing all 12 seasons without missing a quota.

For full rules, card stats, and strategy tips, see [src/README.md](src/README.md).

---

## Tips

- Place shows in their recommended time slot — wrong-slot shows take a **×0.70 view penalty**.
- Fill all 4 slots with the same genre to unlock a **genre monopoly bonus**.
- Morning slot gives **+20% ad income** — stack ads on morning shows for a budget snowball.
- Syndicate a show at age 2 (its peak) before it starts to decay.
- You get **2 bailouts** per run if your budget hits zero — use them wisely.
