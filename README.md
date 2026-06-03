# NETEXEC — Network Executive Simulator

A turn-based strategy game where you manage a television network — schedule shows, sign stars,
sell ads, and grow your viewership over 12 seasons. Hit the ratings quotas or get iced.

Built in Python 3.11 + pygame-ce.

---

## Development Status

| Track | Status |
|-------|--------|
| Python game source (`src/`) | Active development |
| Dev tooling (`dev/`) | Active — 1149 tests, ~93% coverage |

See [STATUS.md](STATUS.md) for the full task sequence and [PromptR.md](PromptR.md) to resume
a Claude Code session.

---

## Repository layout

```
netexecutive/
├── src/                             ← Python game source
│   ├── engine/                      ← constants, network/GameState, cards, effects,
│   │                                   difficulty, requirements, seasonal
│   ├── content/                     ← card pools: shows, stars, ads, upgrades, events
│   ├── saves.py                     ← persistence layer (save/settings/achievements)
│   ├── ui/screens/                  ← playing, header, schedule, shop, summary, menu
│   ├── ui/                          ← bezel, layout, theme, assets, tutorial, ui.py
│   ├── data/                        ← shows.json, stars.json, ads.json, upgrades.json
│   └── version.py
├── dev/                             ← Dev tooling (tests, build scripts)
│   ├── tests/                       ← 1149 tests, ~93% coverage
│   ├── build/                       ← PyInstaller builder (build_game.py)
│   ├── devgame/                     ← Dev game (F12 panel, autopilot, console)
│   └── scripts/                     ← release packager + dev scripts
├── installers/
│   ├── windows/                     ← Windows installer (install.vbs)
│   └── macos/                       ← macOS installer (install.command)
├── PromptR.md                       ← Paste into Claude Code to resume development
├── STATUS.md                        ← Master task sequence and progress tracker
└── REVIEW.md                        ← Architecture reference
```

---

## Install and run

### Requirements

- Python 3.11+
- pygame-ce

### Install dependencies

```bash
pip install pygame-ce
```

### Play the game (direct terminal launch)

```bash
cd src
python main.py
```

### Play the game (dev mode — F12 debug panel + autopilot console)

```bash
python dev/devgame/dev_main.py
```

### Build a standalone executable

Produces `dist/NETEXEC.exe` (Windows) or `dist/NETEXEC.app` (macOS).
Python 3.11+ required; PyInstaller is auto-installed if missing.

```bash
python dev/build/build_game.py
```

---

## Development tasks

### Run the test suite

Must run from `dev/`, not the repo root (`.coveragerc` paths are relative to `dev/`):

```bash
pip install pygame-ce pytest pytest-cov jsonschema
cd dev
python -m pytest tests/ -q
```

1149 tests, ~93% coverage. Run before and after any Python change.

### Validate JSON content files

```bash
python dev/scripts/devscripts/validate_content.py
```

### Regenerate the player compendium in src/README.md

```bash
python dev/scripts/devscripts/gen_compendium.py
```

### Run balance simulation

```bash
cd dev
python tests/sim/run_batch.py --games 200
```

---

## Resuming development

Open [PromptR.md](PromptR.md) and paste the content after the `===` line into a new
Claude Code session. Claude will read STATUS.md + REVIEW.md, verify the last commit,
and plan the next task.
