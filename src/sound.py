"""
sound.py
========
Procedurally generated sound effects + a looping background music bed.

No external audio files are required — every sound is synthesized at runtime
from waveforms, which keeps the project dependency-free and trivial to bundle
into a single executable.

If ``pygame.mixer`` is unavailable on the host (e.g. headless CI), the module
degrades to silent no-ops so the game still runs.
"""

from __future__ import annotations

import array
import math
import random
from typing import Optional

import pygame

from . import constants as C


class SoundManager:
    """Generates and plays SFX/music. Safe to call when audio is disabled."""

    def __init__(self) -> None:
        self.enabled = C.SOUND_ENABLED_DEFAULT
        self.music_enabled = C.MUSIC_ENABLED_DEFAULT
        self._ok = False
        self.sounds: dict[str, Optional[pygame.mixer.Sound]] = {}
        # Initialize ALL attributes up front so they exist even when mixer init
        # fails and we bail out of the try block below.
        self._music_volume = 0.18
        self._music_channel: Optional[pygame.mixer.Channel] = None
        self._music_buffer = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._ok = True
        except Exception:
            # mixer not available — run silently
            self._ok = False
            return
        self._build_sounds()
        self._music_buffer = self._build_music()

    # --------------------------------------------------------------- public API
    def play(self, name: str, *, pitch_var: float = 0.0) -> None:
        """Play a named sound.

        Parameters
        ----------
        name : str
            Sound key ("jump", "land", "death", "complete", "menu",
            "unlock", "bonk", "footstep", "ghost_hum", "near_miss",
            "ghost_despawn").
        pitch_var : float
            If > 0, randomly resample the sound by ±pitch_var semitones for
            variation.  Used on "jump" (±10%) and "footstep" (±15%) to avoid
            repetitive mono-tone.
        """
        if not self.enabled or not self._ok:
            return
        snd = self.sounds.get(name)
        if snd:
            if pitch_var > 0 and self._ok:
                snd = self._pitch_shift(snd, pitch_var)
            snd.play()

    def start_music(self) -> None:
        if not self.music_enabled or not self._ok or self._music_buffer is None:
            return
        try:
            ch = pygame.mixer.find_channel()
            if ch:
                ch.play(self._music_buffer, loops=-1)
                ch.set_volume(self._music_volume)
                self._music_channel = ch
        except Exception:
            pass

    def stop_music(self) -> None:
        if self._music_channel:
            try:
                self._music_channel.stop()
            except Exception:
                pass
            self._music_channel = None

    def toggle_sound(self) -> bool:
        self.enabled = not self.enabled
        if not self.enabled:
            self.stop_music()
        elif self.music_enabled:
            self.start_music()
        return self.enabled

    def toggle_music(self) -> bool:
        self.music_enabled = not self.music_enabled
        if self.music_enabled:
            self.start_music()
        else:
            self.stop_music()
        return self.music_enabled

    # --------------------------------------------------------------- synthesis
    def _wave(self, samples: list[float], volume: float = 1.0) -> pygame.mixer.Sound:
        """Convert a list of float samples in [-1, 1] into a stereo Sound."""
        arr = array.array("h")
        for s in samples:
            v = max(-1.0, min(1.0, s * volume))
            n = int(v * 32767)
            arr.append(n)
            arr.append(n)  # duplicate for stereo
        return pygame.mixer.Sound(buffer=arr.tobytes())

    def _pitch_shift(self, snd: pygame.mixer.Sound, semitones: float
                     ) -> pygame.mixer.Sound:
        """Create a pitch-shifted copy by resampling.

        semitones : float
            Max ±semitones; a random value in [-semitones, +semitones] is chosen.
        """
        try:
            shift = random.uniform(-semitones, semitones)
            ratio = 2.0 ** (shift / 12.0)
            src = pygame.mixer.Sound(buffer=snd.get_raw())
            # Resample: stretch the buffer by the ratio
            raw = bytes(src.get_raw())
            new_len = max(1, int(len(raw) / ratio))
            # Simple linear interpolation resample on raw 16-bit stereo samples
            samples = self._resample_stereo(raw, new_len, ratio)
            return pygame.mixer.Sound(buffer=samples)
        except Exception:
            return snd

    @staticmethod
    def _resample_stereo(raw: bytes, new_len: int, ratio: float) -> bytes:
        """Resample 16-bit stereo audio by linear interpolation."""
        n_frames = len(raw) // 4  # 2 bytes * 2 channels
        out = array.array("h")
        for i in range(new_len // 4):
            pos = i * ratio
            idx = int(pos)
            frac = pos - idx
            if idx + 1 >= n_frames:
                idx = n_frames - 1
                frac = 0.0
            base = idx * 4
            next_base = (idx + 1) * 4 if idx + 1 < n_frames else base
            for ch in range(2):
                a = int.from_bytes(raw[base + ch * 2: base + ch * 2 + 2], "little", signed=True)
                b = int.from_bytes(raw[next_base + ch * 2: next_base + ch * 2 + 2], "little", signed=True)
                v = int(a + (b - a) * frac)
                v = max(-32768, min(32767, v))
                out.append(v)
                out.append(v)  # stereo duplicate
        return out.tobytes()

    def _build_sounds(self) -> None:
        sr = 44100
        self.sounds["jump"] = self._wave(self._blip(440, 760, 0.14, sr), 0.4)
        self.sounds["land"] = self._wave(self._thud(0.10, sr), 0.35)
        self.sounds["death"] = self._wave(self._sweep(500, 60, 0.45, sr), 0.5)
        # Extended complete fanfare: 5-note ascending arp
        self.sounds["complete"] = self._wave(
            self._arp([523, 659, 784, 1047, 1319], 0.10, sr), 0.45)
        self.sounds["menu"] = self._wave(self._blip(660, 660, 0.06, sr), 0.3)
        self.sounds["unlock"] = self._wave(self._arp([392, 523, 784], 0.12, sr), 0.4)
        # Bonk: short, dull thud for head bumps on ceilings
        self.sounds["bonk"] = self._wave(self._bonk(sr), 0.35)
        # Footstep: subtle click while running
        self.sounds["footstep"] = self._wave(self._click(0.04, sr), 0.15)
        # Ghost proximity hum: low eerie drone
        self.sounds["ghost_hum"] = self._wave(self._drone(0.6, sr), 0.12)
        # Near-miss whoosh: short airy sweep when player grazes a ghost
        self.sounds["near_miss"] = self._wave(self._whoosh(0.18, sr), 0.28)
        # Ghost despawn: soft fade-out tone when a ghost finishes its replay
        self.sounds["ghost_despawn"] = self._wave(self._despawn(0.25, sr), 0.15)
        # Jump pad: bouncy springy boing sound
        self.sounds["jump_pad"] = self._wave(self._boing(0.18, sr), 0.45)

    def _blip(self, f0: float, f1: float, dur: float, sr: int) -> list[float]:
        """A short frequency sweep — good for a jump sound."""
        n = int(dur * sr)
        out = []
        for i in range(n):
            t = i / sr
            f = f0 + (f1 - f0) * (i / n)
            env = math.exp(-3.0 * t)
            out.append(env * math.sin(2 * math.pi * f * t))
        return out

    def _thud(self, dur: float, sr: int) -> list[float]:
        """Low-frequency noise burst — landing thud."""
        n = int(dur * sr)
        out = []
        for i in range(n):
            t = i / sr
            env = math.exp(-18.0 * t)
            out.append(env * (math.sin(2 * math.pi * 90 * t) * 0.6
                              + random.uniform(-1, 1) * 0.4))
        return out

    def _sweep(self, f0: float, f1: float, dur: float, sr: int) -> list[float]:
        """A falling sweep — death sound."""
        n = int(dur * sr)
        out = []
        for i in range(n):
            t = i / sr
            f = f0 + (f1 - f0) * (i / n)
            env = math.exp(-2.5 * t)
            out.append(env * math.sin(2 * math.pi * f * t))
        return out

    def _arp(self, freqs: list[float], note_dur: float, sr: int) -> list[float]:
        """Sequence of tones — level complete / unlock jingle."""
        out = []
        for f in freqs:
            n = int(note_dur * sr)
            for i in range(n):
                t = i / sr
                env = math.exp(-4.0 * t)
                out.append(env * (math.sin(2 * math.pi * f * t)
                                  + 0.3 * math.sin(2 * math.pi * f * 2 * t)))
        return out

    def _bonk(self, sr: int) -> list[float]:
        """Short dull thud — head bonk on ceiling."""
        dur = 0.08
        n = int(dur * sr)
        out = []
        for i in range(n):
            t = i / sr
            env = math.exp(-25.0 * t)
            # Low thud + slight rattle
            out.append(env * (math.sin(2 * math.pi * 120 * t) * 0.5
                              + math.sin(2 * math.pi * 280 * t) * 0.3
                              + random.uniform(-1, 1) * 0.2))
        return out

    def _click(self, dur: float, sr: int) -> list[float]:
        """Very short subtle click — footstep."""
        n = int(dur * sr)
        out = []
        for i in range(n):
            t = i / sr
            env = math.exp(-40.0 * t)
            out.append(env * (math.sin(2 * math.pi * 200 * t) * 0.6
                              + random.uniform(-1, 1) * 0.4))
        return out

    def _drone(self, dur: float, sr: int) -> list[float]:
        """Low eerie drone — ghost proximity warning."""
        n = int(dur * sr)
        out = []
        for i in range(n):
            t = i / sr
            env = math.exp(-2.0 * t) * 0.7
            # Two slightly detuned low sines create a beating/uneasy feel
            out.append(env * (math.sin(2 * math.pi * 55 * t)
                              + math.sin(2 * math.pi * 57.5 * t)))
        return out

    def _whoosh(self, dur: float, sr: int) -> list[float]:
        """Short airy sweep — near-miss sound when player grazes a ghost."""
        n = int(dur * sr)
        out = []
        for i in range(n):
            t = i / sr
            # Envelope: rise then fall
            env = math.sin(math.pi * t / dur) * math.exp(-3.0 * t)
            # White noise + high-freq tone sweep
            noise = random.uniform(-1, 1) * 0.6
            freq = 800 + 600 * (i / n)
            tone = math.sin(2 * math.pi * freq * t) * 0.4
            out.append(env * (noise + tone))
        return out

    def _despawn(self, dur: float, sr: int) -> list[float]:
        """Soft fading tone — ghost finished its replay and despawned."""
        n = int(dur * sr)
        out = []
        for i in range(n):
            t = i / sr
            env = math.exp(-8.0 * t)  # fast decay — subtle, not distracting
            # Slightly detuned twin tones for an ethereal, vanishing feel
            out.append(env * (math.sin(2 * math.pi * 420 * t) * 0.5
                              + math.sin(2 * math.pi * 418 * t) * 0.3))
        return out

    def _boing(self, dur: float, sr: int) -> list[float]:
        """Bouncy springy sound for jump pads — rapid upward frequency sweep."""
        n = int(dur * sr)
        out = []
        for i in range(n):
            t = i / sr
            # Quick upward sweep then settle
            f = 300 + 900 * (i / n) * math.exp(-3.0 * t)
            env = math.exp(-4.0 * t)
            out.append(env * (math.sin(2 * math.pi * f * t) * 0.7
                              + math.sin(2 * math.pi * f * 1.5 * t) * 0.3))
        return out

    def _build_music(self) -> Optional[pygame.mixer.Sound]:
        """A soft, looping ambient pad. Slow chord changes keep it unobtrusive."""
        if not self._ok:
            return None
        sr = 22050
        # A minor pad: A2, C3, E3, A3 — slow arpeggiation
        chord = [110.0, 130.81, 164.81, 220.0]
        dur = 4.0
        n = int(dur * sr)
        out = [0.0] * n
        for k, f in enumerate(chord):
            for i in range(n):
                t = i / sr
                # slow LFO on amplitude per voice for movement
                lfo = 0.5 + 0.5 * math.sin(2 * math.pi * (0.07 + 0.01 * k) * t + k)
                out[i] += 0.12 * lfo * math.sin(2 * math.pi * f * t)
        # normalize
        peak = max(abs(v) for v in out) or 1.0
        out = [v / peak for v in out]
        return self._wave(out, 0.6)
