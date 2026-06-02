# NETEXEC — Network Executive Simulator

A turn-based strategy game where you manage a television network — schedule shows, sign stars,
sell ads, and grow your viewership over 12 seasons. Hit the ratings quotas or get iced.

> **Primary platform: Godot 4.x (in active development)**
> The Python version in this repo serves as the working game spec. Godot is being built
> from it. After GODOT-QA1 the Python source will be archived.

---

## Development Status

| Track | Status |
|-------|--------|
| Python source (`netexec-main/`) | Stable. Serves as the Godot spec. |
| Godot deliverable (`../netexec/`) | In development — GODOT-SETUP is next |
| Godot dev version (`../netexec-dev/`) | Awaiting implementation |
| Godot tester (`../netexec-tester/`) | Awaiting implementation |

See [STATUS.md](STATUS.md) for the full task sequence and [PromptR.md](PromptR.md) to resume
a Claude Code session.

---

## Repository layout

```
netexecutive/                        ← this repo (github.com/gimmeurcode/netexecutive)
├── netexec-main/                    ← Python game source (spec for Godot port)
│   ├── scripts/engine/              ← constants, network/GameState, cards, effects,
│   │                                   difficulty, requirements, seasonal
│   ├── scripts/content/             ← card pools: shows, stars, ads, upgrades, events
│   ├── scripts/platform.py          ← Steam abstraction layer (save/achievements)
│   ├── ui/screens/                  ← playing, header, schedule, shop, summary, menu
│   ├── ui/                          ← bezel, layout, theme, assets, tutorial, ui.py
│   ├── data/                        ← shows.json, stars.json, ads.json, upgrades.json
│   └── version.py
├── netexec-dev/                     ← Python dev tooling (tests, build scripts)
│   ├── tests/                       ← 667 tests, ≥ 60% coverage
│   └── build/                       ← PyInstaller builder
├── netexec-setup/                   ← Windows + macOS installers
├── PromptR.md                       ← Paste into Claude Code to resume development
├── STATUS.md                        ← Master task sequence and progress tracker
└── REVIEW.md                        ← Architecture findings and task rationale

../netexec/                          ← Godot deliverable (github.com/gimmeurcode/netexec)
../netexec-dev/                      ← Godot dev version (F12 panel + console)
../netexec-tester/                   ← Godot tester (always-on state inspector)
```

---

## Godot architecture

```
Engine:    Godot 4.x | GDScript | NOT C# | Steam: GodotSteam plugin
MCP:       godot-mcp (tugcantopaloglu/godot-mcp) — configured after GODOT-SETUP

res://
├── autoloads/     Constants.gd  GameState.gd  ContentManager.gd  Platform.gd
├── resources/     ShowData  StarData  AdData  UpgradeData  EventData  ContractData
├── scenes/        main_menu/  playing/(hud/ schedule/ shop/)  summary/
├── data/          shows.json  stars.json  ads.json  upgrades.json
└── assets/        art  fonts  audio
```

**Engine ↔ UI contract:** All game logic in autoloads; scenes connect to signals only.
`Platform.gd` is the Steam/offline boundary — save/load/achievements route through it.

---

## Running the Python version (for reference / spec verification)

Requires Python 3.11+ and pygame-ce.

```bash
pip install pygame-ce
python netexec-main/main.py
```

```bash
# Tests — must run from netexec-dev/, not the repo root
pip install pygame-ce pytest pytest-cov
cd netexec-dev
python -m pytest tests/ -q
```

667 tests, ≥ 60% coverage required. Run before and after any Python change.

---

## Resuming development

Open [PromptR.md](PromptR.md) and paste the content after the `===` line into a new
Claude Code session. Claude will read STATUS.md + REVIEW.md, verify the last commit,
and plan the next task.
