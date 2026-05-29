"""audio.py — every sound is synthesized at runtime with numpy.

We deliberately ship NO copyrighted anime audio. Instead we generate
chiptune-style sound effects and high-pitched "anime voice" blips from raw
waveforms, then hand them to pygame's mixer. The demon-girls' actual anime
*lines* are shown as on-screen text (see maps.py / hud.py); the blips give
those lines a voice-like chirp without using any real recordings.

If audio hardware/mixer is unavailable (e.g. a headless server), the module
degrades gracefully: every play() call simply does nothing.
"""

import numpy as np      # Used to build the raw sample arrays.
import pygame           # pygame.mixer turns sample arrays into playable Sounds.

# Standard CD-quality sample rate (samples per second).
SAMPLE_RATE = 44100


class SoundBank:
    """Builds and stores all synthesized sound effects, and plays them."""

    def __init__(self):
        # Tracks whether the mixer initialized successfully; if not, we stay silent.
        self.enabled = False
        # Will map a sound name -> pygame Sound object.
        self.sounds = {}
        # Global mute flag toggled by the player.
        self.muted = False
        # Attempt to initialize the audio mixer; tolerate failure on headless setups.
        try:
            # Pre-set the mixer format BEFORE pygame.init runs in game.py.
            pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
            # Actually initialize the mixer subsystem.
            pygame.mixer.init()
            # If we got here without raising, audio is available.
            self.enabled = True
        except Exception:
            # Any failure (no device, dummy driver) -> run silently.
            self.enabled = False

    # ----- low-level waveform builders -------------------------------------

    def _tone(self, freq, end_freq, dur, vol, wave="sine"):
        """Return a mono float array for one enveloped, optionally swept tone."""
        # Total number of samples for this tone's duration.
        n = int(SAMPLE_RATE * dur)
        # A time axis from 0 to dur seconds, one entry per sample.
        t = np.linspace(0, dur, n, endpoint=False)
        # Linearly interpolate the (instantaneous) frequency from freq to end_freq.
        inst_freq = np.linspace(freq, end_freq, n)
        # Integrate frequency over time to get phase (cumulative sum approximates the integral).
        phase = 2 * np.pi * np.cumsum(inst_freq) / SAMPLE_RATE
        # Pick a waveform shape based on the requested type.
        if wave == "sine":
            w = np.sin(phase)                                  # Smooth pure tone.
        elif wave == "square":
            w = np.sign(np.sin(phase))                         # Harsh chiptune square.
        elif wave == "triangle":
            w = 2 / np.pi * np.arcsin(np.sin(phase))           # Mellow triangle wave.
        else:  # "sawtooth"
            w = 2 * (t * freq - np.floor(0.5 + t * freq))      # Buzzy sawtooth.
        # Build an amplitude envelope: quick attack then exponential decay.
        env = np.ones(n)                                       # Start flat at 1.
        attack = max(1, int(0.01 * SAMPLE_RATE))               # ~10ms attack length.
        env[:attack] = np.linspace(0, 1, attack)               # Ramp up over the attack.
        env *= np.exp(-3.0 * t / dur)                          # Exponential decay over the tone.
        # Apply volume and envelope to the waveform and return it.
        return (w * env * vol).astype(np.float32)

    def _noise(self, dur, vol):
        """Return a mono float array of decaying white noise (for impacts)."""
        # Number of samples for this burst.
        n = int(SAMPLE_RATE * dur)
        # Random samples uniformly in [-1, 1].
        w = np.random.uniform(-1, 1, n).astype(np.float32)
        # Time axis for the decay envelope.
        t = np.linspace(0, dur, n, endpoint=False)
        # Exponential decay so the noise "punches" then fades.
        env = np.exp(-6.0 * t / dur)
        # Apply volume + envelope.
        return (w * env * vol).astype(np.float32)

    def _compose(self, segments):
        """Mix a list of (start_time, mono_array) pairs into one Sound.

        This lets us schedule several blips at different delays to build a
        little "phrase" (e.g. a defeated warble).
        """
        # Figure out the total length needed to fit every scheduled segment.
        total = 0
        for start, arr in segments:                            # Inspect each segment.
            end = int(start * SAMPLE_RATE) + len(arr)          # Sample index where it ends.
            total = max(total, end)                            # Track the furthest end.
        # Allocate the mixing buffer (silence) of the required length.
        buf = np.zeros(total, dtype=np.float32)
        # Add each segment into the buffer at its start offset.
        for start, arr in segments:
            i = int(start * SAMPLE_RATE)                       # Start sample index.
            buf[i:i + len(arr)] += arr                         # Sum (mix) it in.
        # Prevent clipping by gently limiting the peak amplitude.
        peak = np.max(np.abs(buf)) if total else 0             # Loudest sample magnitude.
        if peak > 1.0:                                         # If it would clip...
            buf /= peak                                        # ...normalize back to <= 1.
        # Convert the float buffer to 16-bit stereo and make a pygame Sound.
        return self._make_sound(buf)

    def _make_sound(self, mono):
        """Convert a mono float array in [-1,1] into a stereo pygame Sound."""
        # Scale floats to the signed 16-bit integer range.
        ints = np.int16(np.clip(mono, -1, 1) * 32767)
        # Duplicate the mono channel into two columns to make it stereo.
        stereo = np.column_stack((ints, ints))
        # Build and return a playable Sound from the sample array.
        return pygame.sndarray.make_sound(stereo)

    # ----- assemble the named sound effects --------------------------------

    def build(self):
        """Synthesize every sound effect and store it by name.

        Safe to call even when audio is disabled; it simply returns early.
        """
        # If the mixer never initialized, there is nothing to build.
        if not self.enabled:
            return
        # Holy Sword swing: a fast downward whoosh plus a little air noise.
        self.sounds["sword"] = self._compose([
            (0.0, self._tone(700, 200, 0.18, 0.4, "triangle")),
            (0.0, self._noise(0.12, 0.15)),
        ])
        # Spirit Bolt cast: a rising magical "pew" with a detuned square layer.
        self.sounds["bolt"] = self._compose([
            (0.0, self._tone(300, 900, 0.22, 0.4, "sine")),
            (0.0, self._tone(450, 1200, 0.18, 0.12, "square")),
        ])
        # Generic impact: a low thud plus a noise crunch.
        self.sounds["impact"] = self._compose([
            (0.0, self._tone(160, 60, 0.12, 0.3, "square")),
            (0.0, self._noise(0.1, 0.25)),
        ])
        # Player hurt: a short low descending grunt.
        self.sounds["hurt"] = self._compose([
            (0.0, self._tone(220, 90, 0.2, 0.4, "sawtooth")),
        ])
        # Enemy aggro: two quick rising blips = a startled "eh?!".
        self.sounds["aggro"] = self._compose([
            (0.0, self._tone(600, 800, 0.08, 0.3, "sine")),
            (0.09, self._tone(800, 1000, 0.08, 0.3, "sine")),
        ])
        # Enemy attack: a bright high chirp = a "kyaa!" lunge.
        self.sounds["enemy_attack"] = self._compose([
            (0.0, self._tone(1000, 1300, 0.1, 0.3, "sine")),
            (0.08, self._tone(1300, 900, 0.1, 0.2, "sine")),
        ])
        # Enemy death: a falling warble = a comedic anime faint.
        self.sounds["enemy_death"] = self._compose([
            (0.0, self._tone(1100, 900, 0.1, 0.3, "sine")),
            (0.1, self._tone(900, 1100, 0.1, 0.3, "sine")),
            (0.2, self._tone(1100, 400, 0.25, 0.3, "sine")),
        ])
        # Pickup: a cheerful two-note "got item" chime.
        self.sounds["pickup"] = self._compose([
            (0.0, self._tone(660, 660, 0.1, 0.3, "square")),
            (0.1, self._tone(990, 990, 0.14, 0.3, "square")),
        ])
        # Level cleared: an ascending major arpeggio fanfare.
        self.sounds["level_clear"] = self._compose([
            (0.0, self._tone(523, 523, 0.18, 0.35, "triangle")),
            (0.12, self._tone(659, 659, 0.18, 0.35, "triangle")),
            (0.24, self._tone(784, 784, 0.18, 0.35, "triangle")),
            (0.36, self._tone(1047, 1047, 0.3, 0.35, "triangle")),
        ])
        # Player death: a long mournful descending tone.
        self.sounds["death"] = self._compose([
            (0.0, self._tone(400, 60, 1.2, 0.4, "sawtooth")),
        ])

    # ----- playback control -------------------------------------------------

    def play(self, name):
        """Play a previously built sound by name (no-op if muted/disabled)."""
        # Do nothing if audio is off, muted, or the sound wasn't built.
        if not self.enabled or self.muted or name not in self.sounds:
            return
        # Play the sound once on any free channel.
        self.sounds[name].play()

    def toggle_mute(self):
        """Flip the mute flag and return the new state."""
        self.muted = not self.muted    # Invert the mute flag.
        return self.muted              # Report whether we are now muted.
