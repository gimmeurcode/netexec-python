"""
constants.py — NETEXEC: Network Executive Simulator
====================================================
Single source of truth for every tunable value in the game.
Adjust numbers here to re-balance without touching logic files.

Sections
--------
  SCREEN          Resolution, FPS, title
  PALETTE         Broadcast control room color definitions
  GENRE_COLORS    Per-genre badge colors (text, bg)
  LAYOUT          Panel dimensions, slot sizes, tooltip/counter sizing
  FONTS           Font size hierarchy
  TIMINGS         Animation, toast, flash durations
  GAME BALANCE    Core economy constants
  AGE_MULTIPLIERS Lifecycle decay table
  TIME_SLOTS      Slot definitions (index, label, ability)
  DIFFICULTY      Per-difficulty modifier dictionaries
  AUDIO           Mixer settings & default volumes
"""

# ─── SCREEN ───────────────────────────────────────────────────────────────────

SCREEN_WIDTH   = 1280
SCREEN_HEIGHT  = 800
FPS            = 60
WINDOW_TITLE   = "NETEXEC - Network Executive Simulator"

# All supported resolutions shown in the Settings screen.
# Each entry is (width, height).
RESOLUTIONS = [
    (1024, 640),
    (1280, 720),
    (1280, 800),
    (1440, 900),
    (1920, 1080),
]

# ─── PALETTE (broadcast control room — dark slate + LED indicators) ────────────

# Background & panels
C_BG           = (  8,  10,  14)   # deep slate black — main canvas
C_PANEL        = ( 14,  18,  26)   # panel backgrounds — slightly lighter
C_PANEL_ALT    = ( 10,  22,  18)   # alternate panel (left side tint)
C_PANEL_BORDER = ( 30,  42,  60)   # panel borders — steel blue-grey
C_PANEL_ACCENT = (  0, 180,  80)   # bright green panel accents

# Primary text & signal green (ON-AIR, active)
C_GREEN_BRIGHT = (  0, 255, 100)   # bright phosphor — active ON-AIR indicator
C_GREEN_MID    = (  0, 195,  70)   # standard active text
C_GREEN_DIM    = (  0,  80,  35)   # inactive/off labels
C_GREEN_PANEL  = ( 10,  24,  14)   # dark green panel fill

# Amber / budget / income
C_AMBER        = (255, 190,  20)   # budget numbers, income highlights
C_AMBER_DIM    = (140, 100,  10)   # dim amber — unfulfilled states
C_AMBER_GLOW   = (255, 160,   0)   # warm amber glow

# Red / danger / deficit
C_RED          = (255,  60,  60)   # danger, deficit, error
C_RED_DIM      = (100,  25,  25)   # inactive danger
C_RED_GLOW     = (200,   0,  40)   # deep red alert

# Blue / info / cooldown
C_BLUE         = ( 60, 160, 255)   # info, cooldowns, neutral state
C_BLUE_DIM     = ( 20,  60, 120)   # inactive blue
C_CYAN         = ( 80, 230, 220)   # tooltip highlights, detail info

# UI chrome
C_WHITE        = (230, 235, 245)   # headings, important numbers
C_GREY_LIGHT   = (140, 150, 165)   # sub-labels
C_GREY_MID     = ( 70,  80,  95)   # borders, dividers
C_GREY_DARK    = ( 30,  35,  45)   # subtle background elements

# Interaction states
C_SELECTED     = (255, 240,  80)   # selected item (bright yellow)
C_HOVER        = ( 40, 220, 120)   # hover highlight
C_HOVER_PANEL  = ( 20,  40,  30)   # hover panel background tint
C_BORDER       = (  0, 130,  50)   # active borders
C_BORDER_DIM   = (  0,  50,  22)   # inactive borders

# Flash
C_FLASH_POS    = ( 40, 255, 100)   # positive action flash
C_FLASH_NEG    = (255,  50,  50)   # negative action flash
C_SCANLINE     = (  0,   0,   0)   # CRT scanline (drawn with alpha)

# Net counter colors — income/view projection display
C_NET_POS      = ( 80, 255, 140)   # net positive (more income/views)
C_NET_NEG      = (255,  80,  80)   # net negative
C_NET_NEUTRAL  = (180, 180, 200)   # no change
C_VIEWS_ACCENT = (120, 200, 255)   # views/ratings color
C_INCOME_ACCENT= (255, 210,  60)   # income/money color

# ─── GENRE BADGE COLORS ───────────────────────────────────────────────────────
# Each entry: (text_rgb, background_rgb)

GENRE_COLORS = {
    "SITCOM":  ((255, 220,  60), ( 60,  44,   0)),
    "DRAMA":   ((200, 100, 255), ( 50,   0,  70)),
    "SCIFI":   (( 60, 200, 255), (  0,  40,  75)),
    "REALITY": ((255, 100, 100), ( 75,  10,  10)),
    "SPORTS":  ((255, 150,  40), ( 75,  38,   0)),
    "NEWS":    ((190, 195, 210), ( 30,  32,  40)),
    "COOKING": ((210, 135,  55), ( 55,  26,   0)),
}

# ─── LAYOUT ───────────────────────────────────────────────────────────────────

HEADER_H       = 75    # header bar height in pixels
PAD            = 6     # universal internal padding

LEFT_W         = 642   # left panel width
RIGHT_W        = 632   # right panel width  (LEFT_W + RIGHT_W + PAD ≈ SCREEN_WIDTH)
PANEL_SPLIT_X  = LEFT_W + PAD

# Left panel sections
SLOT_H         = 106   # height of each time-slot card
VAULT_H        = 102   # height of each vault slot card
UPGRADE_ROW_H  = 56    # upgrades row height (shows up to 5 badges)
MONOPOLY_BAR_H  = 28   # monopoly status bar below upgrades
SEASONAL_STRIP_H = 52  # seasonal-events status strip below monopoly bar
AIR_BTN_H       = 50  # AIR SEASON button height

# Right panel sections
TAB_ROW_H      = 48    # shop tab row height
SHOP_CARD_H    = 110   # height of each shop item card
REROLL_BTN_H   = 50    # reroll button height

# Inline card attachment rows (inside each time-slot card)
ATTACHMENT_H   = 20    # height of a single star/ad attachment label line

# Net view/income projection bar & tooltips
NET_COUNTER_H  = 32    # height of the net view/income projection bar
TOOLTIP_MAX_W  = 340   # maximum tooltip panel width
TOOLTIP_PAD    = 10    # internal tooltip padding

# ─── FONT SIZES ───────────────────────────────────────────────────────────────
# Used to request SysFont variants at these point sizes.

# CRITICAL: MIN_FONT_SIZE = 8pt is a HARD FLOOR that ALL text rendering must respect.
# This applies everywhere: theme.py fonts, bezel.py fonts, assets.py fonts, ui.py fonts.
# Every single font size must be max(requested_size, MIN_FONT_SIZE) to ensure no text
# goes below 8pt (equivalent to Times New Roman 8pt with technical monospace rendering).
# Use this in all direct pygame.font.Font() and pygame.font.SysFont() calls.
MIN_FONT_SIZE = 8     # hard floor: 8pt (Times New Roman equivalent) with technical monospace fonts

FONT_TITLE   = 42    # main menu, game-over title
FONT_HEADER  = 27    # panel headers, season counter
FONT_BODY    = 22    # card text, labels
FONT_SMALL   = 20    # sub-labels, genre badges, cooldown numbers
FONT_MICRO   = 18    # HUD fine-print, card stats, tooltips

# ─── ANIMATION TIMINGS (milliseconds) ─────────────────────────────────────────

TOAST_DURATION      = 3200   # how long a toast message stays at full opacity
TOAST_FADE_MS       = 500    # toast fade-out duration
FLASH_DURATION_MS   = 180    # screen-colour flash on significant action
NUMBER_POP_DURATION = 1400   # floating +/− view/income pop-up lifetime
TRANSITION_MS       = 350    # screen wipe transition
BLINK_PERIOD_MS     = 700    # full on→off→on period for blinking indicators
SCANLINE_ALPHA      = 22     # alpha of the CRT scanline overlay strip (0–255)
SCANLINE_SPACING    = 3      # pixels between scanline strips

# ─── GAME BALANCE ─────────────────────────────────────────────────────────────

MAX_SEASONS          = 12
INITIAL_BUDGET       = 70
MAX_RERUN_SLOTS      = 2
REROLL_BASE_COST     = 3
BASE_INCOME          = 0        # baseline income per season before any shows
MAX_ACTIVE_UPGRADES  = 5

TARGET_INTERVAL      = 3        # milestone check every N seasons
BASE_VIEW_TARGET     = 1000     # Season-3 minimum total views
TARGET_GROWTH_RATE   = 2.4      # each milestone target = previous × this
MILESTONE_REWARD     = 50       # +$ on hitting a milestone

SELL_REFUND_RATE     = 0.75     # fraction of show cost refunded on cancel/sell
STAR_REFUND_RATE     = 0.50     # fraction of each attached star's cost refunded on sell

# Wildcard ability balance caps — enforced by data + verified in tests
WILDCARD_MAX_V_FLAT  = 80       # max flat view bonus per wildcard ability
WILDCARD_MAX_V_MULT  = 1.35     # max view multiplier per wildcard ability
WILDCARD_MAX_INCOME  = 20       # max seasonal income per wildcard ability
WILDCARD_MIN_UPKEEP  = -4       # most negative upkeep allowed (max reduction)

# Shop composition (items per refresh per category)
SHOP_SHOW_COUNT      = 5
SHOP_STAR_COUNT      = 3
SHOP_AD_COUNT        = 3
SHOP_UPG_COUNT       = 2
SHOP_EVENT_COUNT     = 2

# Prestige (run-over-run) difficulty scaling
PRESTIGE_TARGET_SCALE = 0.25   # view quotas × (1 + prestige × 0.25)
PRESTIGE_GROWTH_BONUS = 0.10   # milestone growth rate += prestige × 0.10

# Time-slot penalty for placing a show outside its recommended slots
SLOT_PENALTY_MULT    = 0.70    # ×0.70 views when in the wrong slot

# ─── LIFECYCLE DECAY TABLE ────────────────────────────────────────────────────
# List of (age_min, age_max, view_multiplier).
# Shows peak at season 2 then decline. Upgrades can partially counteract decay.

AGE_MULTIPLIERS = [
    (1, 1,   1.00),   # debut season — finding its audience
    (2, 2,   1.25),   # sophomore surge — peak window
    (3, 3,   1.05),   # still strong, coming off the peak
    (4, 4,   0.85),   # mid-run fatigue
    (5, 5,   0.70),   # long-run sag
    (6, 6,   0.58),   # audience restlessness
    (7, 999, 0.45),   # veteran burnout (age 7+)
]

# ─── TIME SLOT DEFINITIONS ────────────────────────────────────────────────────
# Ordered list; index corresponds to position in STATE.lineup[].
# 'ability' text is displayed in the UI; actual math is in network.py.

TIME_SLOTS = [
    {"index": 0, "id": "MORNING",    "label": "Morning",    "ability": "Ad Income +20%"},
    {"index": 1, "id": "AFTERNOON",  "label": "Afternoon",  "ability": "Base Views +10%"},
    {"index": 2, "id": "PRIME TIME", "label": "Prime Time", "ability": "Star Bonus ×1.5"},
    {"index": 3, "id": "LATE NIGHT", "label": "Late Night", "ability": "Upkeep −50%"},
]

# ─── DIFFICULTY LEVELS ────────────────────────────────────────────────────────
# All modifiers are applied by DifficultyManager in difficulty.py.
#
# budget_mod        : flat dollars added to starting INITIAL_BUDGET
# target_mult       : multiplies all milestone view targets
# growth_mod        : added to TARGET_GROWTH_RATE for milestone scaling
# star_cost_mult    : multiplies star purchase costs
# ad_income_mult    : multiplies all ad income values (upfront + seasonal)
# event_freq_mod    : fraction modifier on how many event slots appear in shop
# rival_pressure    : flat views added to every milestone (simulates rival network)

DIFFICULTY_LEVELS = {
    "EASY": {
        "label":          "EASY",
        "color":          ( 50, 220, 100),
        "budget_mod":     +15,
        "target_mult":    0.83,
        "growth_mod":     -0.20,
        "star_cost_mult": 0.80,
        "ad_income_mult": 1.15,
        "event_freq_mod": +0.25,
        "rival_pressure": 0,
        "desc": (
            "Reserved parking spot. Free coffee machine on every floor. "
            "The board is rooting for you. Relax - ratings will come."
        ),
    },
    "NORMAL": {
        "label":          "NORMAL",
        "color":          (  0, 200,  60),
        "budget_mod":     0,
        "target_mult":    1.00,
        "growth_mod":     -0.25,
        "star_cost_mult": 1.00,
        "ad_income_mult": 1.00,
        "event_freq_mod": 0.00,
        "rival_pressure": 0,
        "desc": (
            "Standard network grind. No favors. No excuses. "
            "Hit the quotas or clear your desk."
        ),
    },
    "HARD": {
        "label":          "HARD",
        "color":          (255, 140,   0),
        "budget_mod":     -10,
        "target_mult":    1.10,
        "growth_mod":     -0.15,
        "star_cost_mult": 1.25,
        "ad_income_mult": 0.90,
        "event_freq_mod": -0.10,
        "rival_pressure": 100,
        "desc": (
            "Rival networks are buying talent and undercutting ad rates. "
            "The board wants results. Yesterday."
        ),
    },
    "BRUTAL": {
        "label":          "BRUTAL",
        "color":          (255,  40,  40),
        "budget_mod":     -20,
        "target_mult":    1.30,
        "growth_mod":     -0.15,
        "star_cost_mult": 1.50,
        "ad_income_mult": 0.80,
        "event_freq_mod": -0.20,
        "rival_pressure": 200,
        "desc": (
            "You are one bad quarter from being replaced by a reality show "
            "about your replacement. Good luck."
        ),
    },
}

DEFAULT_DIFFICULTY = "NORMAL"

# ─── AUDIO ────────────────────────────────────────────────────────────────────

AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS    = 2       # stereo
AUDIO_BUFFER      = 512
DEFAULT_MUSIC_VOL = 0.30    # background ambience volume (0.0–1.0)
DEFAULT_SFX_VOL   = 0.65    # sound effects volume (0.0–1.0)
