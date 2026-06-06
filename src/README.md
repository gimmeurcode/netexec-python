# NETEXEC — Network Executive Simulator

A TV network management roguelite. You are the executive. Hit the ratings quotas or get iced.

---

## Download, install, and play

### Windows (recommended — no terminal required)

1. Download **`NETEXEC-Windows.zip`** from the releases page.
2. Extract the zip — you get a folder containing `src\`, `dist\`, and `installers\`.
3. Open `installers\windows\` and double-click **`install.vbs`**.
4. Click **Yes** when Windows asks for administrator permission.
5. Click **Yes** to confirm the install location.
6. Launch **NetExecutive** from your Desktop or Start Menu.

Settings are saved to `%APPDATA%\NETEXEC\`. No terminal or Python required.

---

### macOS (no Python required)

1. Download **`NETEXEC-Mac.zip`** from the releases page.
2. Extract the zip — you get a folder containing `src/`, `dist/`, and `installers/`.
3. Open `installers/macos/` and double-click **`install.command`**.
   - macOS opens a Terminal window automatically; the install runs and the window closes.
   - If macOS warns about an unverified developer: right-click → Open → Open.
4. Launch **NetExecutive** from `/Applications` or your Desktop.

Settings are saved to `~/.config/NETEXEC/`. No manual terminal commands required.

---

### Developer — direct Python launch

Requires **Python 3.11+** and **pygame-ce**:

```bash
pip install pygame-ce
cd src
python main.py
```

---

### Developer — build the standalone executable

Requires Python 3.11+ (PyInstaller is auto-installed):

```bash
python dev/build/build_game.py
```

Output: `dist/NETEXEC.exe` (Windows) or `dist/NETEXEC.app` (macOS).

---

## How to Play

1. **Select difficulty** — Easy / Normal / Hard / Brutal.
2. **Buy items from the shop** (right panel): Shows, Stars, Ads, Upgrades, Events.
3. **Schedule shows** into the 4 time slots on the left panel.
4. **Attach Stars and Ads** to shows to boost views and income.
5. **Click AIR SEASON** to simulate one season and collect views and income.
6. **Hit the view quota** every 3 seasons (Seasons 3, 6, 9, 12) to survive.
7. **Win** by completing all 12 seasons without missing a quota.

---

## Folder Structure

```
src/                     ← game source root
│
├── main.py              Entry point — pygame init, game loop.
├── version.py           Single source of truth for VERSION string.
├── saves.py             Persistence layer (save/settings/achievements).
│
├── engine/
│   ├── constants.py     All tunable values (budget, targets, growth rates, etc.)
│   ├── network.py       GameState — all game logic and the 9-stage yield pipeline.
│   ├── cards.py         JSON loaders, condition evaluator, show instance factory.
│   ├── effects.py       Data-driven upgrade effect resolver.
│   ├── difficulty.py    Stateless difficulty and prestige scaling.
│   ├── requirements.py  Declarative requirement evaluator (contracts/mandates).
│   └── seasonal.py      Seasonal event roll, aggregation, reward/penalty.
│
├── content/
│   ├── cardpool.py      Generic lazy-loading shuffleable card pool.
│   ├── shows.py         Show pool + placement validation.
│   ├── stars.py         Star pool + attachment validation.
│   ├── ads.py           Ad pool + dual-income helpers.
│   ├── upgrades.py      Upgrade pool management.
│   └── events.py        Event pool + handler registry.
│
├── ui/
│   ├── ui.py            GameUI top-level controller.
│   ├── layout.py        Responsive layout engine.
│   ├── theme.py         Design tokens and font loading.
│   ├── assets.py        Procedural card art and genre badges.
│   ├── assets_loader.py SVG/PNG loader with procedural fallback.
│   ├── audio.py         Synthesized sound engine (no external audio files).
│   ├── bezel.py         CRT chrome frame renderer.
│   ├── ledger.py        Terminal ledger panel.
│   ├── tutorial.py      Step-by-step tutorial overlay.
│   ├── widgets.py       Shared pygame drawing helpers.
│   └── screens/         Per-screen modules (menu, playing, summary, etc.)
│
├── assets/              SVG icons, fonts.
│
└── data/
    ├── shows.json        Shows across 7 genres + wildcard template.
    ├── stars.json        Stars with JSON-encoded conditions.
    ├── ads.json          Ads including wildcard template.
    ├── upgrades.json     Global upgrades.
    ├── events.json       One-off events.
    ├── seasonal_events.json  Seasonal modifier/mandate/contract/instant events.
    ├── wildcards.json    Wildcard configuration options.
    └── bailouts.json     Insolvency bailout tiers.

dist/                    ← build outputs (gitignored)
    ├── NETEXEC.exe       Standalone Windows executable.
    └── NETEXEC.app       Standalone macOS app bundle.
```

---

## Adding New Content

All card content lives in `data/*.json`. No Python changes needed to add:

- **New shows**: Add an entry to `data/shows.json` under `"shows"`. Match the field names of existing entries.
- **New stars**: Add to `data/stars.json`. Use condition types: `always`, `genre` (with `genres` list), `size_min`, `ad_slots_min`, `age_min`.
- **New ads**: Add to `data/ads.json`. Same condition types as stars.
- **New upgrades**: Add an entry to `data/upgrades.json` with an `"effects"` list — no Python changes required.
- **New events**: Add to `data/events.json` with an `effect_type` string.
- **New genres**: Add a key to `genre_registry` in `shows.json`, add colour to `GENRE_COLORS` in `engine/constants.py`.
- **New wildcard options**: Add genre or slot options to `data/wildcards.json`.

---

## Balancing

All numeric values live in `engine/constants.py`:

| Constant               | Default | Effect                                  |
|------------------------|---------|----------------------------------------|
| `INITIAL_BUDGET`       | $75     | Starting budget before difficulty mod   |
| `BASE_VIEW_TARGET`     | 1000    | Season-3 view quota (Normal)            |
| `TARGET_GROWTH_RATE`   | 2.1     | Each milestone = previous × this        |
| `MILESTONE_REWARD`     | $50     | Bonus dollars on hitting a milestone    |
| `REROLL_COST`          | $5      | Cost to refresh the shop                |
| `SELL_REFUND_RATE`     | 0.5     | Fraction of cost refunded on cancel     |
| `MAX_ACTIVE_UPGRADES`  | 5       | Maximum simultaneous global upgrades    |
| `SLOT_PENALTY_MULT`    | 0.70    | Views × this when show is in wrong slot |
| `PRESTIGE_TARGET_SCALE`| 0.25    | +25% quota per prestige level           |
| `PRESTIGE_GROWTH_BONUS`| 0.10    | +0.10 growth rate per prestige level    |

---

## Gameplay Strategies

**Genre Monopoly (all 4 slots, same genre)**
Fill every slot with the same genre to unlock the monopoly bonus each season.
Drama monopoly (+$18/season) funds further talent acquisitions.
Sports monopoly (×1.30 views) can carry you through late milestones.

**Ad-Heavy (Reality + Morning slot)**
Reality shows have 3 ad slots and zero star slots. Stack triple ads on Morning
for +20% income scaling. Lizard Insurance + Local Car + Turbo Energy = serious cash.

**Star-Driven (Drama + Prime Time)**
Drama shows with 2 star slots in Prime Time scale star multipliers by ×1.5.
Ryan Branston (×1.5) becomes ×1.75. Add Kieran Royalty for +180 flat views on top.

**Syndication Preservation**
Syndicate a show at age 2 (×1.25 peak multiplier) before it decays.
The Syndication Deal upgrade doubles vault view share. DVR Revolution adds more.

**Prestige Runner**
Accept difficult conditions to unlock higher prestige. Each prestige level makes
the next run harder but also signals mastery. Brutal + high prestige = endgame.

---

## Complete Game Compendium

_Generated from data files. Re-run `python dev/scripts/devscripts/gen_compendium.py` after any content change._

<!-- COMPENDIUM:START -->
## Core Rules & Economy

**Goal:** Survive 12 seasons by hitting a cumulative view quota every 3 seasons (Seasons 3, 6, 9, 12). Miss any quota and the network folds.

| Setting | Value |
|---|---|
| Seasons per run | 12 |
| Milestone check every | 3 seasons |
| Season-3 view quota (Normal) | 1,000 |
| Milestone quota growth | ×2.4 each milestone (difficulty-adjusted) |
| Milestone reward | +$50 |
| Starting budget (Normal) | $75 |
| Reroll shop cost | $5 |
| Sell/cancel refund | 50% of cost |
| Max simultaneous upgrades | 5 |
| Slot penalty (wrong slot) | ×0.70 views |
| Prestige target scale | +25% quota per prestige level |
| Prestige growth bonus | +0.10 growth rate per prestige level |

**Win:** Complete Season 12 while meeting every milestone.

**Loss:** Miss any milestone quota.

## Difficulty Levels

| Difficulty | Starting Budget | Season-3 Quota | Growth Rate | Star Cost | Ad Income | Rival Pressure |
|---|---|---|---|---|---|---|
| **Easy** | $90 | 800 | ×2.20 | ×0.80 | ×1.15 | +0 |
| **Normal** | $75 | 1,000 | ×2.10 | ×1.00 | ×1.00 | +0 |
| **Hard** | $60 | 1,200 | ×2.25 | ×1.25 | ×0.90 | +100/milestone |
| **Brutal** | $50 | 1,500 | ×2.25 | ×1.50 | ×0.80 | +200/milestone |

## Genres & Time Slots

### Genre Monopoly Bonuses

Fill all 4 lineup slots with the same genre to activate the monopoly bonus each season.

| Genre | Monopoly Effect |
|---|---|
| **Sitcom** | All show upkeep ×0.5 & +$8 income/season per show |
| **Drama** | ×1.22 views & +$18 income/season per show |
| **Scifi** | Star bonuses amplified ×2.5 in all slots & ×1.1 views & +$10 income/season per show |
| **Reality** | Ad income ×1.5 & ×1.08 views & +$6 income/season per show |
| **Sports** | ×1.3 views & +$20 income/season per show |
| **News** | Milestone target ×0.88 & +$5 income/season per show |
| **Cooking** | +$22 direct budget/season & ×1.1 views |

### Time Slots

Shows placed outside their recommended slot(s) receive ×0.70 views.

| Slot | Label | Ability |
|---|---|---|
| 0 | Morning | Ad Income +20% |
| 1 | Afternoon | Base Views +10% |
| 2 | Prime Time | Star Bonus ×1.5 |
| 3 | Late Night | Upkeep −50% |

### Show Age / Lifecycle Decay

| Age (seasons aired) | View Multiplier |
|---|---|
| 1 | 1.00 — Debut |
| 2 | 1.25 — Sophomore surge (peak) |
| 3 | 1.05 — Still strong |
| 4 | 0.85 — Mid-run fatigue |
| 5 | 0.70 — Long-run sag |
| 6 | 0.58 — Audience restlessness |
| 7+ | 0.45 — Veteran burnout |

## Shows

All 4 lineup slots are filled by shows. Recommended slots are listed; placing a show elsewhere applies a ×0.70 view penalty.

### Cooking

| Name | Cost | Upkeep | Base Views | Size | Star/Ad Slots | Rec. Slots |
|---|---|---|---|---|---|---|
| The Cooling Zone | $11 | $2 | 82 | 1 | 0/3 | Morning |
| Fridge Wars | $14 | $3 | 105 | 1 | 0/2 | Morning, Afternoon |
| Burnt Offerings | $17 | $4 | 125 | 1 | 1/1 | Afternoon, Prime Time |
| The Midnight Diner | $22 | $5 | 140 | 1 | 1/2 | Late Night |
| Last Resort Restaurant | $20 | $5 | 148 | 1 | 1/2 | Afternoon, Prime Time |
| Celebrity Dry Run | $25 | $7 | 180 | 1 | 2/1 | Prime Time |
| The Culinary Games | $32 | $9 | 230 | 1 | 2/2 | Prime Time, Late Night |

### Drama

| Name | Cost | Upkeep | Base Views | Size | Star/Ad Slots | Rec. Slots |
|---|---|---|---|---|---|---|
| Rules & Regs | $20 | $6 | 135 | 1 | 1/2 | Afternoon, Late Night |
| Legal Eagle Loophole | $20 | $6 | 148 | 1 | 1/2 | Afternoon, Prime Time |
| Agents of S.H.A.M.P.O.O. | $22 | $6 | 150 | 1 | 2/2 | Late Night |
| Flatline & Fine | $23 | $7 | 168 | 1 | 1/2 | Prime Time |
| Midnight Court | $24 | $7 | 170 | 1 | 1/2 | Late Night |
| Boardroom Bloodlines | $26 | $8 | 185 | 1 | 2/1 | Prime Time |
| Cream Stone | $28 | $9 | 190 | 1 | 1/2 | Prime Time |
| Breaking Point | $29 | $9 | 200 | 1 | 1/2 | Prime Time, Late Night |
| The Long Farewell | $30 | $10 | 215 | 1 | 2/1 | Prime Time |
| Fixing Good | $30 | $10 | 220 | 1 | 2/1 | Prime Time |
| The Bear Trap | $32 | $11 | 230 | 1 | 2/1 | Prime Time, Late Night |
| Throne of Bones | $34 | $11 | 245 | 1 | 2/1 | Prime Time |
| The Successors | $35 | $12 | 250 | 1 | 2/1 | Prime Time, Late Night |
| Crown of Ash | $44 | $12 | 300 | 2 | 2/0 | Afternoon, Prime Time |
| Musical Chairs | $62 | $18 | 450 | 2 | 2/2 | Afternoon, Prime Time |

### News

| Name | Cost | Upkeep | Base Views | Size | Star/Ad Slots | Rec. Slots |
|---|---|---|---|---|---|---|
| Weather or Not | $12 | $2 | 85 | 1 | 0/3 | Morning |
| The Morning Panic | $13 | $3 | 98 | 1 | 0/3 | Morning |
| The Evening Briefing | $14 | $3 | 100 | 1 | 1/3 | Morning, Afternoon |
| Opinion Overdrive | $16 | $4 | 120 | 1 | 1/2 | Afternoon, Prime Time |
| Breaking Point | $16 | $6 | 120 | 1 | 1/2 | Morning, Late Night |
| Global Crisis Network | $18 | $4 | 135 | 1 | 1/2 | Morning, Afternoon, Prime Time |
| The Spin Zone | $20 | $5 | 140 | 1 | 1/2 | Prime Time, Late Night |
| The Anchor | $22 | $5 | 155 | 1 | 2/2 | Afternoon, Prime Time |

### Reality

| Name | Cost | Upkeep | Base Views | Size | Star/Ad Slots | Rec. Slots |
|---|---|---|---|---|---|---|
| Bargain Bin Bonanza | $10 | $2 | 70 | 1 | 0/3 | Morning, Late Night |
| The Outcaster | $10 | $2 | 90 | 1 | 0/3 | Afternoon, Prime Time |
| Breath Mints Around the Globe | $10 | $2 | 90 | 1 | 0/3 | Afternoon, Prime Time |
| Infinite Garage | $12 | $3 | 95 | 1 | 0/3 | Late Night |
| Survive My Family | $13 | $3 | 105 | 1 | 0/3 | Morning, Afternoon, Prime Time |
| Kitchen Yelling | $14 | $3 | 115 | 1 | 1/2 | Prime Time, Late Night |
| Sweeps Week House | $14 | $3 | 115 | 1 | 1/2 | Prime Time, Late Night |
| The Great Bake-Off-By-One | $16 | $4 | 120 | 1 | 1/2 | Afternoon |
| Influencer Island | $18 | $5 | 140 | 1 | 1/1 | Afternoon, Prime Time |
| Drag My Race | $20 | $5 | 155 | 1 | 1/2 | Afternoon, Prime Time |
| Squid League | $25 | $7 | 190 | 1 | 1/2 | Prime Time, Late Night |

### Sci-Fi

| Name | Cost | Upkeep | Base Views | Size | Star/Ad Slots | Rec. Slots |
|---|---|---|---|---|---|---|
| Space Carpool Karaoke | $20 | $6 | 150 | 1 | 1/2 | Morning, Afternoon |
| Cyberslug vs. Mecho Earthworm | $20 | $5 | 155 | 1 | 1/2 | Afternoon, Prime Time |
| Mecha Farm | $22 | $7 | 165 | 1 | 1/2 | Late Night |
| Algorithm & Blues | $22 | $6 | 168 | 1 | 1/2 | Afternoon, Prime Time |
| Signal Noise | $24 | $7 | 175 | 1 | 1/2 | Afternoon, Prime Time |
| Star Path | $25 | $8 | 180 | 1 | 2/1 | Prime Time, Late Night |
| Quantum Paradox | $30 | $9 | 185 | 1 | 1/0 | Prime Time |
| Android Blues | $28 | $9 | 195 | 1 | 2/2 | Afternoon, Prime Time |
| Moonbase Malfunction | $42 | $13 | 315 | 2 | 2/2 | Afternoon, Prime Time |
| Starfall Armada | $48 | $14 | 320 | 2 | 2/1 | Afternoon, Prime Time |
| Hero Complex | $55 | $16 | 410 | 2 | 2/2 | Afternoon, Prime Time |
| Quantum Telethon | $58 | $17 | 435 | 2 | 2/2 | Afternoon, Prime Time |

### Sitcom

| Name | Cost | Upkeep | Base Views | Size | Star/Ad Slots | Rec. Slots |
|---|---|---|---|---|---|---|
| North Lawn | $12 | $2 | 80 | 1 | 0/3 | Prime Time, Late Night |
| Golden Glitches | $12 | $3 | 88 | 1 | 0/3 | Morning, Afternoon |
| Smart Guys, Dumb Problems | $14 | $3 | 95 | 1 | 1/2 | Afternoon, Prime Time |
| Laugh Track 3000 | $12 | $3 | 95 | 1 | 0/3 | Morning, Afternoon, Prime Time |
| Laugh Riot Live | $12 | $3 | 95 | 1 | 2/1 | Afternoon, Prime Time |
| Server Down! | $14 | $3 | 100 | 1 | 1/2 | Afternoon, Prime Time |
| The Cubicle | $15 | $4 | 110 | 1 | 1/2 | Afternoon, Prime Time |
| Budget Buddies | $15 | $4 | 110 | 1 | 1/2 | Morning, Afternoon |
| Park Place | $16 | $4 | 115 | 1 | 1/2 | Afternoon, Prime Time |
| Suburban Spy Dad | $17 | $4 | 120 | 1 | 1/2 | Afternoon, Prime Time |
| The Bronze Gals | $18 | $5 | 125 | 1 | 2/1 | Morning, Afternoon |
| Elementary, My Dear | $19 | $5 | 130 | 1 | 1/2 | Afternoon, Prime Time |
| Nine-Nien! | $18 | $5 | 130 | 1 | 1/2 | Afternoon, Prime Time |
| Acquaintances | $20 | $6 | 140 | 1 | 2/1 | Prime Time |
| What's The Way? | $22 | $6 | 145 | 1 | 2/2 | Prime Time, Late Night |

### Sports

| Name | Cost | Upkeep | Base Views | Size | Star/Ad Slots | Rec. Slots |
|---|---|---|---|---|---|---|
| Esports at Noon | $15 | $3 | 115 | 1 | 1/2 | Morning, Afternoon |
| Armchair QB Supreme | $16 | $4 | 120 | 1 | 0/2 | Morning, Afternoon |
| Premier Kicking | $18 | $5 | 135 | 1 | 1/2 | Morning, Afternoon |
| Chessboxing Nights | $18 | $5 | 140 | 1 | 1/2 | Prime Time |
| Office Overtime Olympics | $20 | $6 | 155 | 1 | 1/2 | Morning, Afternoon |
| Steel Chair Spectacular | $22 | $6 | 160 | 1 | 2/2 | Prime Time, Late Night |
| GrappleMania | $22 | $6 | 160 | 1 | 2/2 | Late Night |
| Good Lad | $26 | $8 | 185 | 1 | 2/1 | Afternoon, Prime Time |
| Ultimate Fainting Championship | $45 | $13 | 300 | 2 | 1/3 | Morning, Afternoon |
| Sunday Concussions | $40 | $12 | 350 | 2 | 1/3 | Morning, Afternoon |
| Gridiron Sunday Primetime | $52 | $16 | 360 | 2 | 0/2 | Prime Time |
| Meteor Bowl XL | $55 | $16 | 420 | 2 | 2/2 | Prime Time, Late Night |

## Stars

Stars attach to shows (up to star_slots per show). Prime Time (slot 2) amplifies the *bonus* portion of a star's view multiplier by ×1.5.

| Name | Cost | Condition (fires effect) | Effect | Fallback |
|---|---|---|---|---|
| A-List Celeb | $20 | always | +100 views, +$5 upkeep | no effect |
| Ad Magnet | $20 | ad slots ≥ 2 | ×1.3 views, +$8 income | +60 views, +$4 upkeep |
| Bryan Cranston | $28 | genre: DRAMA | +160 views, ×1.2 views, +$8 upkeep | +60 views, +$4 upkeep |
| Card Shark Cameo | $20 | ad slots ≥ 2 | ×1.3 views, +$5 upkeep | +55 views, +$5 upkeep |
| Chef Gordon Rampsey | $15 | genre: REALITY | +80 views | +80 views, +$8 upkeep |
| Cici Bankroll | $28 | has_ads | ×1.1 views | +15 views |
| Controversy Machine | $12 | genre: REALITY/NEWS | +95 views, +$5 upkeep | +30 views, +$4 upkeep |
| Cosmo Captain | $24 | genre: SCIFI | ×1.5 views, +$7 upkeep | +70 views, +$5 upkeep |
| Crossover King | $22 | size ≥ 2 | ×1.5 views, +$8 upkeep | +65 views, +$5 upkeep |
| Dame Marguerite Vale | $34 | age ≥ 3 seasons | ×2.1 views | +30 views, +$3 upkeep |
| Dashiell Crowe | $33 | not | ×1.75 views | no effect |
| Daytime Darling | $16 | genre: COOKING/SITCOM | +95 views, +$5 income | +50 views, +$3 upkeep |
| Donny Deviti | $18 | genre: SITCOM | +120 views | +40 views, +$3 upkeep |
| Event-Only Diva | $30 | size ≥ 2 | ×1.5 views, +$12 upkeep | +70 views, +$6 upkeep |
| Gordon Flambe | $18 | genre: COOKING | +125 views | +45 views, +$4 upkeep |
| Hank Modine | $30 | has_stars | +20 views | +25 views |
| Kieran Royalty | $28 | genre: DRAMA | +180 views, +$10 income | +60 views, +$4 upkeep |
| Lucille Ball | $26 | genre: SITCOM | ×1.6 views, +$5 income, +$8 upkeep | +70 views, +$4 upkeep |
| Method Maverick | $26 | genre: DRAMA | ×1.6 views, +$8 upkeep | +60 views, +$6 upkeep |
| Network Veteran | $28 | ad slots ≥ 1 | ×1.4 views, +$10 upkeep | +80 views, +$8 upkeep |
| News Anchor Emeritus | $20 | genre: NEWS | ×1.5 views, +$8 income | +60 views, +$4 upkeep |
| Nova Reyes | $31 | always | +$4 income | +$4 income |
| Patrick Stewart | $24 | genre: SCIFI | +140 views, +$-3 upkeep | +50 views, +$5 upkeep |
| Political Satirist | $16 | genre: SITCOM | +100 views, +$-2 upkeep | +50 views, +$3 upkeep |
| Reality Gremlin | $14 | genre: REALITY | +90 views | +60 views, +$6 upkeep |
| Reality TV Royalty | $22 | genre: REALITY | ×1.6 views, +$8 income | +70 views, +$5 upkeep |
| Roxxy Sterling | $40 | always | ×1.9 views, +$14 upkeep | no effect |
| Ryan Branston | $25 | genre: DRAMA | ×1.5 views | +50 views, +$5 upkeep |
| Sci-Fi Convention Legend | $20 | genre: SCIFI | +130 views, +$-3 upkeep | +50 views, +$4 upkeep |
| Sir Bertram Coyle | $36 | age ≥ 4 seasons | ×2.5 views | +$6 upkeep |
| Sitcom Quipster | $18 | genre: SITCOM | +140 views, +$4 upkeep | +50 views, +$4 upkeep |
| Social Media Influencer | $12 | genre: REALITY | +90 views | +-10 views |
| Sports Legend | $28 | genre: SPORTS | +80 views, ×1.4 views, +$10 upkeep | +50 views, +$8 upkeep |
| Streamer Turned Actor | $16 | always | +85 views, +$4 upkeep | no effect |
| Stunt Casting | $24 | size ≥ 2 | ×1.4 views, +$9 upkeep | +70 views, +$6 upkeep |
| Superfan Cameo | $14 | genre: SCIFI/COOKING | +90 views, +$3 income | +40 views, +$2 upkeep |
| Sweeps Whisperer | $22 | age ≥ 3 seasons | ×1.3 views, +$6 upkeep | +65 views, +$5 upkeep |
| The Comeback Kid | $24 | age ≥ 3 seasons | +125 views, +$-3 upkeep | +55 views, +$4 upkeep |
| The Humble Host | $15 | age ≥ 4 seasons | ×1.35 views, +$5 upkeep | +50 views, +$3 upkeep |
| The Pebble | $30 | genre: SPORTS/DRAMA | ×1.8 views, +$12 upkeep | +90 views, +$12 upkeep |
| Tim Sprint | $30 | genre: SCIFI/SPORTS | ×1.7 views, +$10 upkeep | ×1.1 views, +$10 upkeep |
| Veteran Newscaster | $18 | genre: NEWS | +110 views, +$-2 upkeep | +45 views, +$3 upkeep |
| Washed-Up Icon | $8 | always | +40 views, +$1 upkeep | no effect |
| Zandor Pyx | $32 | genre: SCIFI | ×1.85 views | ×0.85 views |

## Ads

Ads attach to shows (up to ad_slots per show). **Dual-income model:** each ad pays an upfront cash bonus when attached, then generates seasonal income each time the show airs. Morning slot (slot 0) scales positive ad income by ×1.20.

| Name | Cost | Upfront | Condition | Effect | Fallback |
|---|---|---|---|---|---|
| 3AM Miracle Infomercial | $6 | +$0 | age ≥ 3 seasons | +$26 income | +$8 income |
| BargainShield Compare | $0 | +$4 | genre: SITCOM/REALITY | +$15 income | +$7 income |
| BetZone Sports(TM) | $0 | +$8 | genre: SPORTS | +$22 income | +$9 income |
| Binge Box Subscription | $6 | +$0 | genre: DRAMA/SCIFI | +18 views, +$12 income | +$7 income |
| Breaking News Alert | $0 | +$5 | genre: NEWS | +$18 income | +$6 income |
| Chef's Secret Sauce(TM) | $0 | +$6 | genre: COOKING | +$18 income | +$8 income |
| Chronos Luxury Watches | $0 | +$0 | always | ×0.85 views, +$30 income | no effect |
| Civic Trust Bank | $14 | +$0 | genre_not | +$20 income | +$5 income |
| Cola Hill Singalong | $0 | +$4 | genre: SITCOM/SPORTS | +$14 income | +$14 income |
| Crypto For Pets(TM) | $8 | +$0 | genre: SCIFI | +22 views, +$16 income | +$10 income |
| CryptoBro Coin(TM) | $0 | +$12 | genre: SCIFI/REALITY | +-20 views, +$22 income | +$8 income |
| Cut-Rate Lizard Clone | $0 | +$6 | genre: SITCOM | +$16 income | +$7 income |
| Discount Gym Pass | $0 | +$4 | genre: REALITY/SPORTS | +$14 income | +$6 income |
| FreshMart Weekly | $0 | +$5 | genre: COOKING/REALITY | +$15 income | +$7 income |
| Fruit 1984 | $18 | +$0 | genre: SCIFI/DRAMA | +30 views, +$12 income | +$8 income |
| Guerrilla Viral Campaign | $10 | +$0 | always | +90 views, $-2 income | no effect |
| Lawyer's Finest | $0 | +$5 | genre: DRAMA | +$14 income | +$4 income |
| Lizard Insurance | $0 | +$8 | genre: SITCOM | +$16 income | +$8 income |
| Local Car Dealership | $0 | +$3 | always | +$7 income | no effect |
| Loyalty Card Commercial | $0 | +$3 | always | +$9 income | no effect |
| Maison Prestige | $12 | +$0 | genre: DRAMA | ×1.05 views, +$22 income | +$6 income |
| Meme Energy Drink | $6 | +$0 | genre: SITCOM/REALITY | +30 views, +$8 income | +$8 income |
| Midnight Mattress King | $0 | +$4 | always | +$6 income | no effect |
| Network Self-Promo | $15 | +$0 | always | ×1.2 views, $-2 income | no effect |
| Overdrive Energy | $9 | +$3 | always | +20 views, ×0.95 views, +$18 income | no effect |
| Prestige Cookware(TM) | $8 | +$0 | genre: COOKING | +25 views, +$14 income | +$9 income |
| RecipeBox(TM) Delivery | $0 | +$7 | genre: COOKING/SITCOM | +$16 income | +$6 income |
| RivalStream Banner | $0 | +$18 | always | +-35 views, +$25 income | no effect |
| RivalStream Takeover | $0 | +$45 | always | ×0.8 views, +$4 income | no effect |
| Sludge Cola | $0 | +$5 | always | ×0.9 views, +$12 income | no effect |
| Streaming Pivot Banner | $10 | +$0 | always | ×1.1 views, $-2 income | no effect |
| Stretch Seal | $8 | +$0 | genre: REALITY | +25 views, +$10 income | +$10 income |
| Synergy Ad Consortium | $8 | +$0 | has_ads | +$4 income | +$6 income |
| Tailgate Waffles | $0 | +$5 | genre: SPORTS | +$20 income | +$10 income |
| TechBro Launchpad(TM) | $10 | +$0 | genre: SCIFI | +28 views, +$18 income | +$8 income |
| True Crime Pod Crossover | $6 | +$0 | genre: DRAMA/NEWS | +22 views, +$10 income | +$7 income |
| Turbo Energy Drink | $8 | +$0 | genre: SPORTS | +20 views, +$18 income | +$6 income |
| Vague Pharma Ad | $0 | +$10 | genre: DRAMA | +$18 income | +$4 income |

## Upgrades

Global upgrades apply every season to every eligible show. Maximum 5 active simultaneously.

| Name | Cost | Effect |
|---|---|---|
| **24-Hour News Cycle** | $22 | All NEWS shows gain +35 Base Views & +$5 Income/season. Something is always happening. We cover all of it. |
| **Ad Conglomerate** | $42 | +$6 income per attached ad everywhere. But ad-heavy shows (2+ ads) take a Views x0.92 clutter penalty. |
| **Award Season** | $35 | All DRAMAs gain x1.25 Views. A golden trophy validates an entire season of suffering. Critics weep. Ratings soar. |
| **Awards Circuit** | $35 | All DRAMAs gain x1.25 Views. Stacks with Award Season for x1.5625 total. An extra trophy shelf has been ordered. |
| **Celebrity Feud** | $18 | PRIME TIME shows with 1+ Star gain +40 Views. Beef sells advertising. Always has. Taylor knows this. |
| **Closed Captioning Act (1990)** | $18 | All shows gain +10 Views. Shows with 1+ Ad gain +$3 Income. Accessibility wins ratings. |
| **Color Broadcast Rollout** | $22 | All shows gain +20 Base Views. The 1965 color switch made everything pop. |
| **Cooking Block** | $22 | All COOKING shows gain x1.2 Views. Schedule three back to back and the audience refuses to leave the couch. |
| **Counterprogramming** | $36 | Everything that is NOT a sitcom gets +40 Views. Reward for a diverse, un-safe schedule. |
| **DVR Revolution (TiVo 1999)** | $24 | Vault reruns gain +0.1 view multiplier & +$3 Income/season. Appointment viewing is optional now. |
| **Daytime Dominance** | $18 | Morning and Afternoon shows gain +25 Views. Coffee-fueled audiences are loyal. |
| **Golden Age Revival** | $26 | Shows in Season 3+ gain x1.2 Views. A vintage aesthetic is trending. Your older shows are now 'prestige classics.' |
| **HDTV Transition (2009)** | $28 | PRIME TIME shows gain x1.15 Views. It is so crisp you can see the stage lights. |
| **Late Bloomer Strategy** | $38 | Dormant early, devastating late: from Season 6 onward ALL shows gain Views x1.4. |
| **Late Night Ratings War** | $18 | Late Night shows gain +55 Views. The midnight slot is contested. Monologues are sharper. The band plays louder. |
| **Laugh Track** | $25 | All SITCOMs gain +50 Base Views. Even when nothing is funny. ESPECIALLY when nothing is funny. Ha. |
| **Lean Operation** | $40 | +$12 flat income on every show, at the cost of a slight across-the-board Views x0.95. Margins over reach. |
| **Merchandising Empire** | $20 | All SCIFI shows generate +$8 Income/season. The T-shirt costs $3 to make and sells for $45. This is the way. |
| **Night Owl Writers Room** | $20 | Late Night shows gain +$6 Income/season. The staff never sleeps anyway. |
| **Press Tour** | $24 | Shows with at least 1 Star gain +40 Views. The late-night circuit delivers. |
| **Prestige Division** | $55 | DRAMA & SCIFI shows surge x1.5 Views - but REALITY is starved (x0.8). A bet on prestige over trash. |
| **Product Placement** | $15 | Every attached Ad generates +$2 Extra Income per season. Tony Stark drinks Audi. Bond uses Sony. The check never bounces. |
| **Sports Bar Network** | $26 | All SPORTS shows gain +$10 Income/season. The bar sponsors everything with a TV. |
| **Star Factory** | $46 | Any show with a star gets Views x1.1 and +$7 income per attached star. Talent compounds. |
| **Streaming Threat** | $22 | All REALITY and SPORTS shows gain x1.2 Views. Panic-buy eyeballs before the streamers do. Act now. |
| **Sweeps Week** | $30 | PRIME TIME shows gain x1.3 Views. Networks have been gaming your emotions this way since 1954. |
| **Syndication Deal** | $20 | Vault shows earn x0.5 Views (up from x0.25) & +$5 Income/season. The show ended 15 years ago. The residuals are eternal. |
| **Syndication Engine** | $48 | Shows aged 3+ gain +25 Views for every season they have run. Old hits become evergreen cash cows. |
| **Tabloid Coverage** | $20 | Shows with 1+ Star gain +55 Views. A star-studded lineup generates gossip column inches. Every inch is an eyeball. |
| **Tentpole Doctrine** | $50 | Two-slot shows become monsters: +60 Views and Views x1.6. Single-slot shows get nothing. |
| **Test Kitchen Sponsorship** | $18 | All COOKING shows gain +$8 Income/season. A major appliance brand funds the kitchen. The blender is always on screen. |
| **The Algorithm** | $20 | All shows gain +(Current Season x 5) bonus Views each season. The machine knows what you want before you do. |
| **The Spinoff** | $28 | Shows in Season 3+ gain +80 Base Views. Good IP never truly dies. It just gets a prequel, a sequel, and a podcast. |
| **Triple Platinum Contract** | $26 | Live shows with 1+ Star AND 1+ Ad gain x1.15 Views. Star power and sponsorship in the same slot  -  executives call it synergy. |

## Events

One-off cards: purchased from the shop and applied immediately.

| Name | Cost | Effect |
|---|---|---|
| Ad Inventory Fire Sale | $8 | swap_budget_for_views |
| Advertiser Boycott | $5 | +$50 budget; -30 base views to all shows |
| Cash For Clicks | $9 | swap_budget_for_views |
| Celebrity Chef Meltdown | $10 | +35 base views to all shows |
| Coordinated Ad Blitz | $10 | boost_views_per_ad |
| Emergency View Injection | $14 | add_views_cost_budget |
| FCC Investigation | $6 | -$2 upkeep from all shows |
| Focus Group Frenzy | $14 | +40 base views to all shows |
| Midseason Retool | $10 | reduce all show ages by 1 (min 1) |
| Moon Landing Broadcast (1969) | $20 | +500 total views |
| Nationwide Taste Test | $14 | +$25 budget & +200 views |
| Network-Wide Retool | $11 | retool_lineup_for_views |
| Pilot Panic | $8 | refresh the shop for free |
| Production Tax Incentive | $8 | reduce_upkeep_and_budget |
| Ratings Hotline | $9 | +$20 budget & +150 views |
| Reality TV Craze | $12 | genre_surge |
| Sci-Fi Renaissance | $12 | genre_surge |
| Series Finale Event | $16 | age oldest show +1 seasons; +200 total views |
| Streaming Rights Auction | $18 | +$50 budget |
| Super Bowl Halftime Show | $22 | +$35 budget & +400 views |
| Surprise Sponsorship | $15 | +$30 budget |
| Sweeps Crossover | $18 | +50 base views to all shows |
| Syndication Windfall | $18 | multiply_total_views |
| The Clip That Went Everywhere | $10 | +350 total views |
| Viral Cold Open | $12 | +250 total views |
| Writers' Strike 2007 | $8 | +$40 budget; -20 base views to all shows |

## Seasonal Events

One seasonal event rolls at the END of each season and takes effect the following season.

There are four kinds:

- **Modifier** — passive effect while active (views/upkeep/income multipliers)

- **Mandate** — enforced requirement each season; penalty if unmet

- **Contract** — accept voluntarily from the offers board; reward if requirement met within window, optional penalty if window closes unmet

- **Instant** — one-time effect applied immediately

### Modifiers

| Name | Duration | Effect | Rarity (weight) |
|---|---|---|---|
| **Ad Market Surge** | 2 seasons | +$6 income/show | 5 |
| **Ad Revenue Windfall** | 2 seasons | +$8 income/show | 3 |
| **Awards Season Buzz** | 2 seasons | ×1.12 views | 4 |
| **Budget Audit** | 2 seasons | ×1.5 upkeep | 6 |
| **Cord-Cutting Reversal** | 2 seasons | ×1.1 views, +$4 income/show | 3 |
| **Global Pandemic** | 2 seasons | ×1.12 views, ×1.35 upkeep | 4 |
| **National Food Obsession** | 2 seasons | ×1.2 COOKING views, ×1.08 REALITY views | 4 |
| **Nostalgia Wave** | 2 seasons | ×1.18 SITCOM views, ×1.12 DRAMA views | 3 |
| **Production Strike** | 3 seasons | ×1.6 upkeep | 5 |
| **Sci-Fi Renaissance** | 2 seasons | ×1.22 SCIFI views, ×1.06 REALITY views, ×1.06 NEWS views | 3 |
| **Sports Rights Frenzy** | 2 seasons | ×1.25 SPORTS views, ×1.08 DRAMA views, ×1.08 NEWS views | 3 |
| **Streaming Wars** | 2 seasons | ×0.85 views | 7 |
| **Summer Ratings Slump** | 2 seasons | ×0.88 views | 7 |
| **Tech Sector Ad Blitz** | 2 seasons | +$5 income/show, ×1.1 SCIFI views, ×1.08 NEWS views | 4 |
| **Television Golden Age** | 2 seasons | ×1.1 views | 3 |

### Mandates

Mandates are auto-activated. Miss the requirement each season → pay the penalty.

| Name | Duration | Requirement | Penalty |
|---|---|---|---|
| **Prime Time Commitment** | 2 seasons | Keep Prime Time slot filled | −$12 |
| **Public Interest Directive** | 3 seasons | Air ≥ 1 NEWS shows | −$15 |
| **Talent Showcase Deal** | 2 seasons | Have ≥ 3 stars attached | −$18 |
| **Writers' Strike** | 2 seasons | Air ≥ 2 REALITY shows | −$20 |

### Auto-fired Contracts

These contracts activate automatically (not from the offers board).

| Name | Duration | Requirement | Reward | Penalty |
|---|---|---|---|---|
| **Network Merger Talks** | 3 seasons | Avoid airing REALITY shows | +$40 | −$15 |
| **Streaming Acquisition Offer** | 4 seasons | Reach 3,000 total views | +$60 | −$25 |

### Contracts (Offers Board)

These contracts appear on the offers board — you must click ACCEPT to activate them.

| Name | Duration | Requirement | Reward | Penalty |
|---|---|---|---|---|
| **All-Star Network Deal** | 3 seasons | Have ≥ 6 stars attached | +$44 | −$18 |
| **Blockbuster Slate Deal** | 3 seasons | {'type': 'air_size2_count', 'count': 2} | +$45 | −$18 |
| **Culinary Brand Sponsorship** | 3 seasons | Air ≥ 2 COOKING shows | +$26 | −$10 |
| **Full Schedule Guarantee** | 2 seasons | {'type': 'fill_lineup', 'count': 4} | +$30 | −$12 |
| **Live Sports Exclusivity** | 3 seasons | Air ≥ 2 SPORTS shows | +$30 | −$15 |
| **Prestige Drama Commission** | 3 seasons | Air ≥ 2 DRAMA shows | +$28 | −$12 |
| **Public Broadcasting Grant** | 4 seasons | Air ≥ 1 NEWS shows | +$30 | −$10 |
| **Ratings Agency Challenge** | 4 seasons | Reach 6,000 total views | +$40 | — |
| **Ratings Empire Challenge** | 4 seasons | Reach 9,000 total views | +$60 | — |
| **Sponsor Saturation Pact** | 3 seasons | {'type': 'attach_ads_count', 'count': 6} | +$36 | −$14 |
| **Talent Agency Showcase** | 3 seasons | Have ≥ 4 stars attached | +$32 | −$14 |
| **Variety Showcase Mandate** | 3 seasons | {'type': 'genre_variety', 'count': 4} | +$40 | −$16 |
| **War Chest Audit** | 3 seasons | Maintain ≥ $200 budget | +$30 | −$10 |
| **Weekend Sports Block** | 3 seasons | Air ≥ 2 SPORTS shows | +$34 | −$14 |

### Instant Events

| Name | Effect |
|---|---|
| **Clip Goes Viral** | +150 total views |
| **Creative Reinvention** | reduce all show ages by 1 (min 1) |
| **Emergency Arts Council Grant** | +$20 budget |
| **Industry Convention Buzz** | +$15 budget & +120 views |

## Executives

At the start of every new game — **after** choosing a difficulty — you are offered **3 of the 7** executives (drawn at random) and must pick one. Because only 3 are offered each game, you cannot always play the same executive. Your choice applies for the **entire run**: a persistent passive yield modifier plus economy and progression levers. Each pairs a strong upside with a real tradeoff.

### The Mogul — Lorne Castellano

A cigar-chewing media baron who buys his way to the top. Starts flush with cash (+$120) and skims +$12 from every season — but he greenlights for profit, not quality, so everything he touches loses a little shine (Views x0.95).

Effects: start budget +120$; +12$/season; all views x0.95.

### The Auteur — Margot Devereux

An award-hungry visionary obsessed with prestige. DRAMA and SCIFI soar under her eye (Views x1.30 each) — but her perfectionism is ruinously expensive (all upkeep x1.20).

Effects: all upkeep x1.20; Drama views x1.30; Scifi views x1.30.

### The Showrunner — Dev Okonkwo

A hands-on craftsman who makes every show better across the board (Views x1.12). The catch: he was hired on a shoestring and you start $50 in the hole on your opening budget.

Effects: start budget -50$; all views x1.12.

### The Accountant — Prudence Vale

A ruthless cost-cutter. Slashes all upkeep (x0.82) and squeezes +$5 income from every live show each season — but her penny-pinching saps ambition, dulling audience numbers (Views x0.93).

Effects: start budget +20$; all views x0.93; all upkeep x0.82; +5$ income/show; reroll cost x0.50.

### The Populist — Buck Rawlins

Gives the people what they want: spectacle. REALITY and SPORTS dominate (Views x1.35 each) — but he has no patience for highbrow fare, and DRAMA and SCIFI wither under him (Views x0.78 each).

Effects: start budget +30$; Reality views x1.35; Sports views x1.35; Drama views x0.78; Scifi views x0.78.

### The Visionary — Iris Chen

Plays the long game and demands the impossible. Audience quotas are 18% steeper every season — but her swing-for-the-fences slate has a colossal ceiling (Views x1.28) and she reinvests +$8 a season.

Effects: +8$/season; all views x1.28; quotas x1.18.

### The Closer — Sal Moretti

A deal-maker who keeps the network's expectations low and the war chest full: quotas are 15% gentler and you start with +$60. But his shows are pure filler with no monetisation muscle (-$4 income per live show each season).

Effects: start budget +60$; -4$ income/show; quotas x0.85.

## Reproducible Seeds

Every run is governed by a master **seed**, chosen at random by default so each new game differs. The seed drives all shop draws, rerolls, and seasonal rolls, and is recorded with your save — so the same seed (and difficulty + executive) replays an identical game.

## Insolvency Bailouts

When your budget drops below $0 after a season and you haven't yet used 2 bailouts, a bailout modal appears. Choose **LOAN** or **GRANT**. Bailouts are capped at **2 per run**.

### Tier 1 — First Lifeline

Both choices inject **+$50** into your budget immediately.

**LOAN (Parent Company Loan)**  
Binding contract: Reach 2,000 total views within 3 seasons. Miss it → −$40 penalty.

**GRANT (Arts Council Emergency Subsidy)**  
No ongoing obligation. Costs −200 views from your current total views immediately.

### Tier 2 — Last Resort

Both choices inject **+$65** into your budget immediately.

**LOAN (Investor Emergency Injection)**  
Binding contract: Reach 4,000 total views within 2 seasons. Miss it → −$60 penalty.

**GRANT (Emergency Broadcasting Grant)**  
No ongoing obligation. Costs −450 views from your current total views immediately.

## Autoplay Bots

Three headless strategy bots drive the balance simulator
(`python sim/run_batch.py`). Each bot calls `choose_actions(state)` once
per season planning phase, then the engine calls `advance_season()`.

**RandomBot**
Buys random affordable items from any category. Wildcard cards are skipped.
Serves as the floor baseline — roughly the performance of a player who makes
no strategic decisions.

**GreedyValueBot**
Maximises views-per-dollar. Each season it:
1. Rotates aging shows — vaults shows at age 5+, sells when the vault is full.
2. Chases genre monopoly — fills all 4 slots with the most common genre it can afford.
3. Buys view-boosting upgrades first (drama, laugh track, sweeps week, etc.).
4. Attaches stars to prime-time shows, ads to morning shows.
5. Adjusts priorities when mandate/contract requirements are active (seasonal awareness).

**AdEconomyBot**
Front-loads ad income for a budget snowball effect. Each season it:
1. Buys ads aggressively to maximise the upfront cash + seasonal income stream.
2. Prefers Morning slot placement for the +20% ad income bonus.
3. Buys budget-boosting events (emergency grants, free rerolls) before view events.
4. Falls back to GreedyValueBot show-buying logic when the ad pool is exhausted.

The three bots together form the win-rate measurement used in balance tuning.
Target bands (200-game batch, GreedyValueBot): EASY 50–70%, NORMAL 30–45%,
HARD 0–5%, BRUTAL ~0%.

<!-- COMPENDIUM:END -->

---

## License

This game is entirely fictional. All shows, stars, and ads are parodies.
Any resemblance to real television is purely intentional and legally deniable.
