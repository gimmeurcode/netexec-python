"""
audio.py — NETEXEC
==================
Synthesized audio engine — no external sound files required.

All sounds are generated programmatically using Python's array module and
pygame.mixer.Sound(buffer=...). This means the game ships without any audio
assets and can be packaged into a standalone executable cleanly.

Sound catalogue
---------------
sfx_buy       Short upward tone: item purchased from shop.
sfx_place     Blip: card placed onto a slot.
sfx_error     Low buzz: invalid action.
sfx_milestone Ascending arpeggio: milestone quota hit.
sfx_gameover  Descending tone: run ended in loss.
sfx_win       Celebratory arpeggio: 12-season victory.
sfx_reroll    Quick whoosh: shop rerolled.
sfx_season    Medium tone: AIR SEASON pressed.
sfx_click     Soft tick: generic UI click.
sfx_toast     Very short blip: toast message appeared.

Music
-----
bg_ambience   Looping drone: low atmospheric hum while playing.

Usage
-----
  audio_mgr = AudioManager()
  audio_mgr.play("sfx_buy")
  audio_mgr.set_sfx_volume(0.5)
  audio_mgr.set_music_volume(0.2)
"""

import array
import math
import pygame
from scripts.engine.constants import (
    AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_BUFFER,
    DEFAULT_MUSIC_VOL, DEFAULT_SFX_VOL,
)

# Number of bytes per sample (16-bit signed short)
_SAMPLE_FMT  = "h"
_MAX_AMP     = 32767
_SAMPLE_RATE = AUDIO_SAMPLE_RATE


def _sine(freq: float, duration_ms: int, volume: float = 0.6,
           attack_ms: int = 5, decay_ms: int = 30) -> array.array:
    """
    Generate a mono 16-bit sine wave sample buffer with simple ADSR envelope.

    Parameters
    ----------
    freq        : float  Frequency in Hz.
    duration_ms : int    Total duration in milliseconds.
    volume      : float  Peak amplitude (0.0–1.0).
    attack_ms   : int    Attack ramp duration (ms).
    decay_ms    : int    Decay tail before silence (ms from end).

    Returns
    -------
    array.array  Mono 'h' (short) sample array at AUDIO_SAMPLE_RATE.
    """
    n   = int(_SAMPLE_RATE * duration_ms / 1000)
    buf = array.array(_SAMPLE_FMT, [0] * n)
    att = int(_SAMPLE_RATE * attack_ms  / 1000)
    dec = int(_SAMPLE_RATE * decay_ms   / 1000)

    for i in range(n):
        # ADSR envelope
        if i < att:
            env = i / att
        elif i > n - dec:
            env = (n - i) / dec
        else:
            env = 1.0

        t     = i / _SAMPLE_RATE
        val   = int(volume * _MAX_AMP * env * math.sin(2 * math.pi * freq * t))
        buf[i] = max(-_MAX_AMP, min(_MAX_AMP, val))

    return buf


def _square(freq: float, duration_ms: int, volume: float = 0.3) -> array.array:
    """
    Generate a mono 16-bit square wave buffer (harsher/buzzy tone).

    Parameters
    ----------
    freq        : float  Frequency in Hz.
    duration_ms : int    Duration in milliseconds.
    volume      : float  Amplitude (0.0–1.0).

    Returns
    -------
    array.array  Mono 'h' sample array.
    """
    n   = int(_SAMPLE_RATE * duration_ms / 1000)
    buf = array.array(_SAMPLE_FMT, [0] * n)
    for i in range(n):
        t   = i / _SAMPLE_RATE
        val = volume * _MAX_AMP * (1 if math.sin(2 * math.pi * freq * t) >= 0 else -1)
        buf[i] = int(val)
    return buf


def _mix(*buffers) -> array.array:
    """
    Mix multiple mono sample arrays into one, normalising to avoid clipping.

    Parameters
    ----------
    *buffers : array.array  Variable number of mono 'h' buffers (must be equal length).

    Returns
    -------
    array.array  Mixed mono 'h' buffer.
    """
    if not buffers:
        return array.array(_SAMPLE_FMT)
    length = min(len(b) for b in buffers)
    result = array.array(_SAMPLE_FMT, [0] * length)
    n      = len(buffers)
    for i in range(length):
        total      = sum(b[i] for b in buffers) // n
        result[i]  = max(-_MAX_AMP, min(_MAX_AMP, total))
    return result


def _mono_to_stereo(buf: array.array) -> array.array:
    """
    Duplicate a mono buffer into interleaved stereo (L, R, L, R, …).

    Parameters
    ----------
    buf : array.array  Mono 'h' buffer.

    Returns
    -------
    array.array  Stereo 'h' buffer (2× length).
    """
    stereo = array.array(_SAMPLE_FMT, [0] * (len(buf) * 2))
    for i, s in enumerate(buf):
        stereo[i * 2]     = s
        stereo[i * 2 + 1] = s
    return stereo


def _make_sound(buf: array.array) -> pygame.mixer.Sound:
    """
    Wrap a sample buffer in a pygame.mixer.Sound object.
    Automatically converts mono to stereo if mixer is initialised in stereo.

    Parameters
    ----------
    buf : array.array  Mono 'h' sample buffer.

    Returns
    -------
    pygame.mixer.Sound or None if mixer is unavailable.
    """
    try:
        if pygame.mixer.get_init() and pygame.mixer.get_init()[2] == 2:
            buf = _mono_to_stereo(buf)
        return pygame.mixer.Sound(buffer=buf)
    except Exception:
        return None


# ─── SOUND DEFINITIONS ────────────────────────────────────────────────────────

def _build_sfx_buy():
    """Short rising two-note blip: 440 Hz → 660 Hz."""
    a = _sine(440, 60, 0.5, attack_ms=5, decay_ms=20)
    b = _sine(660, 80, 0.6, attack_ms=5, decay_ms=30)
    # Concatenate
    buf = array.array(_SAMPLE_FMT, a.tolist() + b.tolist())
    return buf


def _build_sfx_place():
    """Single blip at 550 Hz."""
    return _sine(550, 80, 0.45, attack_ms=3, decay_ms=20)


def _build_sfx_error():
    """Low square-wave buzz: 120 Hz for 200 ms."""
    return _square(120, 200, 0.25)


def _build_sfx_milestone():
    """Ascending 4-note arpeggio: C-E-G-C."""
    notes = [262, 330, 392, 523]
    parts = [_sine(f, 120, 0.55, attack_ms=5, decay_ms=30) for f in notes]
    buf   = array.array(_SAMPLE_FMT)
    for p in parts:
        buf.extend(p)
    return buf


def _build_sfx_gameover():
    """Descending 3-note falling tone."""
    notes = [330, 262, 196]
    parts = [_sine(f, 200, 0.55, attack_ms=10, decay_ms=60) for f in notes]
    buf   = array.array(_SAMPLE_FMT)
    for p in parts:
        buf.extend(p)
    return buf


def _build_sfx_win():
    """Celebratory 6-note ascending arpeggio."""
    notes = [262, 330, 392, 523, 659, 784]
    parts = [_sine(f, 120, 0.60, attack_ms=5, decay_ms=40) for f in notes]
    buf   = array.array(_SAMPLE_FMT)
    for p in parts:
        buf.extend(p)
    return buf


def _build_sfx_reroll():
    """Descending whoosh: 600 Hz → 300 Hz sweep."""
    n   = int(_SAMPLE_RATE * 0.15)
    buf = array.array(_SAMPLE_FMT, [0] * n)
    for i in range(n):
        t     = i / _SAMPLE_RATE
        freq  = 600 - (300 * i / n)
        env   = 1.0 - i / n
        val   = int(0.5 * _MAX_AMP * env * math.sin(2 * math.pi * freq * t))
        buf[i] = max(-_MAX_AMP, min(_MAX_AMP, val))
    return buf


def _build_sfx_season():
    """Mid-range two-tone chord to signal season start."""
    a = _sine(330, 200, 0.5, attack_ms=10, decay_ms=50)
    b = _sine(440, 200, 0.5, attack_ms=10, decay_ms=50)
    return _mix(a, b)


def _build_sfx_click():
    """Very short soft tick at 800 Hz."""
    return _sine(800, 25, 0.25, attack_ms=2, decay_ms=10)


def _build_sfx_toast():
    """Brief high blip at 900 Hz."""
    return _sine(900, 40, 0.20, attack_ms=2, decay_ms=10)


def _build_bg_ambience():
    """
    2-second looping atmospheric drone combining 55 Hz + 82 Hz.
    Very low volume — meant as background texture, not foreground.
    """
    a = _sine(55,  2000, 0.08, attack_ms=200, decay_ms=200)
    b = _sine(82,  2000, 0.05, attack_ms=200, decay_ms=200)
    return _mix(a, b)


# ─── AUDIO MANAGER ────────────────────────────────────────────────────────────

class AudioManager:
    """
    Central audio controller. Lazily builds pygame.mixer.Sound objects on first
    use so startup is fast. Respects user-set volume levels.
    """

    def __init__(self):
        self._sfx_vol   = DEFAULT_SFX_VOL
        self._music_vol = DEFAULT_MUSIC_VOL
        self._sounds: dict[str, pygame.mixer.Sound | None] = {}
        self._bg_channel: pygame.mixer.Channel | None = None
        self._available = False
        self._try_init()

    def _try_init(self):
        """Attempt to initialise pygame.mixer; silently no-ops on failure."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(
                    frequency=AUDIO_SAMPLE_RATE,
                    size=-16,
                    channels=AUDIO_CHANNELS,
                    buffer=AUDIO_BUFFER,
                )
                pygame.mixer.init()
            self._available = True
        except Exception:
            self._available = False

    def _get_sound(self, key: str) -> "pygame.mixer.Sound | None":
        """
        Return the Sound object for key, building it lazily on first request.

        Parameters
        ----------
        key : str  Sound identifier (e.g. 'sfx_buy').

        Returns
        -------
        pygame.mixer.Sound or None if unavailable.
        """
        if not self._available:
            return None
        if key not in self._sounds:
            builders = {
                "sfx_buy":       _build_sfx_buy,
                "sfx_place":     _build_sfx_place,
                "sfx_error":     _build_sfx_error,
                "sfx_milestone": _build_sfx_milestone,
                "sfx_gameover":  _build_sfx_gameover,
                "sfx_win":       _build_sfx_win,
                "sfx_reroll":    _build_sfx_reroll,
                "sfx_season":    _build_sfx_season,
                "sfx_click":     _build_sfx_click,
                "sfx_toast":     _build_sfx_toast,
                "bg_ambience":   _build_bg_ambience,
            }
            builder = builders.get(key)
            if builder:
                buf   = builder()
                sound = _make_sound(buf)
            else:
                sound = None
            self._sounds[key] = sound

        return self._sounds[key]

    def play(self, key: str):
        """
        Play a sound effect by key (fire-and-forget).

        Parameters
        ----------
        key : str  Sound identifier.
        """
        sound = self._get_sound(key)
        if sound:
            try:
                sound.set_volume(self._sfx_vol)
                sound.play()
            except Exception:
                pass

    def start_bg_music(self):
        """Begin looping the background ambience drone."""
        sound = self._get_sound("bg_ambience")
        if sound:
            try:
                sound.set_volume(self._music_vol)
                ch = sound.play(loops=-1)
                self._bg_channel = ch
            except Exception:
                pass

    def stop_bg_music(self):
        """Stop the background ambience."""
        if self._bg_channel:
            try:
                self._bg_channel.stop()
            except Exception:
                pass

    def set_sfx_volume(self, vol: float):
        """
        Set the SFX volume level (0.0–1.0).

        Parameters
        ----------
        vol : float  New SFX volume.
        """
        self._sfx_vol = max(0.0, min(1.0, vol))

    def set_music_volume(self, vol: float):
        """
        Set the background music volume (0.0–1.0).

        Parameters
        ----------
        vol : float  New music volume.
        """
        self._music_vol = max(0.0, min(1.0, vol))
        sound = self._sounds.get("bg_ambience")
        if sound:
            try:
                sound.set_volume(self._music_vol)
            except Exception:
                pass

    @property
    def sfx_volume(self) -> float:
        """Current SFX volume (0.0–1.0)."""
        return self._sfx_vol

    @property
    def music_volume(self) -> float:
        """Current music volume (0.0–1.0)."""
        return self._music_vol

    @property
    def is_available(self) -> bool:
        """True if pygame.mixer initialised successfully."""
        return self._available
