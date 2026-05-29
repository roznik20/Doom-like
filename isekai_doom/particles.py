"""particles.py — a lightweight world-space particle system.

Particles are tiny coloured dots that live in the world (x, y plus a height
fraction `h` between the floor at 0.0 and the ceiling at 1.0). They drift,
fall under a little gravity, and fade out. The raycaster draws them as
distance-scaled dots, occluded by the wall z-buffer just like sprites.

We use them for blood spurts when enemies are hit, sparkle bursts on kills,
glowing trails behind projectiles, and muzzle sparks when firing.
"""

import math      # Direction math for bursts.
import random     # Randomised velocities/spreads.


class Particle:
    """One particle: position, velocity, height, lifetime, colour, size."""

    def __init__(self, x, y, h, vx, vy, vh, life, color, size):
        self.x = x              # World x position.
        self.y = y              # World y position.
        self.h = h              # Height fraction (0 floor .. 1 ceiling).
        self.vx = vx            # World x velocity (tiles/sec).
        self.vy = vy            # World y velocity (tiles/sec).
        self.vh = vh            # Vertical velocity (height fraction/sec).
        self.life = life        # Remaining life in seconds.
        self.max_life = life    # Original life (used to fade the size/alpha).
        self.color = color      # (r, g, b) colour.
        self.size = size        # Base world size used to scale on screen.


class ParticleSystem:
    """Owns and updates all active particles."""

    def __init__(self):
        self.particles = []     # The live particle list.

    def update(self, dt):
        """Move every particle, apply gravity, and cull the dead ones."""
        survivors = []                              # Particles still alive after this tick.
        for p in self.particles:
            p.x += p.vx * dt                        # Integrate horizontal motion.
            p.y += p.vy * dt
            p.h += p.vh * dt                        # Integrate vertical motion.
            p.vh -= 1.5 * dt                        # Gravity pulls the height down.
            if p.h < 0.02:                          # Hit the floor?
                p.h = 0.02                          # Rest just above the floor.
                p.vh = 0.0                          # Stop falling.
                p.vx *= 0.6                         # Friction on landing.
                p.vy *= 0.6
            p.life -= dt                            # Age the particle.
            if p.life > 0:                          # Keep it if still alive.
                survivors.append(p)
        self.particles = survivors                  # Replace with the survivors.

    def _emit(self, x, y, h, count, color, speed, life, size, vh_base=0.8):
        """Spawn `count` particles bursting outward from a point."""
        for _ in range(count):
            ang = random.uniform(0, 2 * math.pi)    # Random horizontal direction.
            spd = random.uniform(0.2, 1.0) * speed  # Random outward speed.
            self.particles.append(Particle(
                x, y, h,
                math.cos(ang) * spd,                # vx.
                math.sin(ang) * spd,                # vy.
                random.uniform(0.2, 1.0) * vh_base, # Upward kick.
                life * random.uniform(0.6, 1.0),    # Slightly varied life.
                color,
                size,
            ))

    # --- Convenience emitters used by the game -----------------------------

    def blood(self, x, y):
        """A red spurt when a demon-girl is hit."""
        self._emit(x, y, 0.5, 10, (200, 20, 40), 2.2, 0.5, 0.07)

    def kill_burst(self, x, y, color=(255, 120, 180)):
        """A bigger, colourful burst when a demon-girl is defeated."""
        self._emit(x, y, 0.5, 24, color, 3.0, 0.8, 0.08, vh_base=1.4)
        self._emit(x, y, 0.5, 12, (255, 255, 255), 2.0, 0.6, 0.05, vh_base=1.0)

    def sparks(self, x, y, color=(255, 230, 120)):
        """Bright sparks for hitscan/impact feedback."""
        self._emit(x, y, 0.5, 8, color, 2.5, 0.35, 0.05)

    def trail(self, x, y, color=(120, 200, 255)):
        """A faint glowing dot left behind a projectile."""
        self.particles.append(Particle(
            x, y, 0.5,
            random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), 0.0,
            0.25, color, 0.06,
        ))

    def clear(self):
        """Drop all particles (used when (re)loading a level)."""
        self.particles = []
