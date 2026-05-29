"""enemy.py — the anime demon-girls and their AI.

Each demon-girl wanders idle until she sees the player, then chases and
attacks in melee. She shouts an (original) anime-style catchphrase when she
notices you or lands a hit, and faints with a comedic warble when defeated.

The AI is intentionally simple and readable:
    idle   -> stand still until the player comes within sight (with line of sight)
    chase  -> walk straight toward the player, sliding along walls
    attack -> when close enough, hit on a cooldown
    dead   -> collapse into a "fainted" sprite that stays as scenery
"""

import math               # Distance + direction math.
import random             # Random palette + catchphrase selection.
from . import config      # Enemy tuning values.
from . import maps        # The catchphrase list.


class Enemy:
    """One demon-girl: position, health, AI state, and animation."""

    def __init__(self, x, y, sprite_set):
        # World position on the grid.
        self.x = x                              # Enemy x.
        self.y = y                              # Enemy y.
        # Hit points; when this reaches zero she faints.
        self.health = config.ENEMY_HEALTH
        # AI state machine value: "idle" | "chase" | "attack" | "dead".
        self.state = "idle"
        # The dict of animation frames for this girl (walk/attack/dead).
        self.sprites = sprite_set
        # Seconds left before she can attack again.
        self.attack_cd = 0.0
        # A timer that drives the 2-frame walk cycle.
        self.anim_t = 0.0
        # A short timer that holds the "attack" pose after striking.
        self.attack_pose_t = 0.0
        # One-shot catchphrase the game reads and displays, then clears.
        self.shout = None
        # True once she has noticed the player (so we only play the gasp once).
        self.aggroed = False

    # ----- helpers ----------------------------------------------------------

    def _is_wall(self, level, x, y):
        """True if (x, y) is inside a solid wall cell or out of bounds."""
        gx, gy = int(x), int(y)                 # Grid indices.
        if gx < 0 or gy < 0 or gx >= level["width"] or gy >= level["height"]:
            return True                         # Out of bounds = solid.
        return level["grid"][gy][gx] != 0       # Non-zero = wall.

    def _blocked(self, level, x, y):
        """Collision check around the enemy's radius."""
        r = config.ENEMY_RADIUS                 # Enemy collision radius.
        # Sample the four edges of the collision circle.
        return (self._is_wall(level, x - r, y) or
                self._is_wall(level, x + r, y) or
                self._is_wall(level, x, y - r) or
                self._is_wall(level, x, y + r))

    def _has_line_of_sight(self, level, tx, ty):
        """Walk a straight line to the target, blocked by any wall in between."""
        # Vector from the enemy to the target (the player).
        dx = tx - self.x                        # X distance to target.
        dy = ty - self.y                        # Y distance to target.
        dist = math.hypot(dx, dy)               # Straight-line distance.
        if dist == 0:
            return True                         # Same spot -> trivially visible.
        # Number of sample steps (~10 per tile) along the line (at least 1).
        steps = max(1, int(dist / 0.1))
        # Per-step increments.
        sx = dx / steps                         # X step.
        sy = dy / steps                         # Y step.
        # Start sampling from the enemy's position.
        cx, cy = self.x, self.y
        for _ in range(steps):
            cx += sx                            # Advance along the line.
            cy += sy
            # If we hit a wall before reaching the player, sight is blocked.
            if self._is_wall(level, cx, cy):
                return False
        return True                             # Reached the player unobstructed.

    def _say(self, audio, kind):
        """Pick a random catchphrase to display and play a matching blip."""
        # Choose a random line from the catchphrase pool.
        self.shout = random.choice(maps.CATCHPHRASES)
        # Play the appropriate voice blip for this kind of moment.
        audio.play(kind)

    # ----- per-frame update --------------------------------------------------

    def update(self, dt, player, level, audio):
        """Run the AI for one frame and apply damage to the player if attacking."""
        # Dead girls don't think; they just lie there as scenery.
        if self.state == "dead":
            return
        # Tick the walk-cycle animation timer.
        self.anim_t += dt
        # Tick down the attack cooldown.
        if self.attack_cd > 0:
            self.attack_cd = max(0.0, self.attack_cd - dt)
        # Tick down how long the attack pose is shown.
        if self.attack_pose_t > 0:
            self.attack_pose_t = max(0.0, self.attack_pose_t - dt)

        # Vector + distance to the player.
        dx = player.x - self.x                  # X to player.
        dy = player.y - self.y                  # Y to player.
        dist = math.hypot(dx, dy)               # Distance to player.

        # --- Acquire the player if in range and visible ---
        if not self.aggroed:
            # Become aggressive if within sight range AND there's a clear line.
            if dist < config.ENEMY_SIGHT_RANGE and self._has_line_of_sight(level, player.x, player.y):
                self.aggroed = True             # Lock onto the player.
                self.state = "chase"            # Start chasing.
                self._say(audio, "aggro")       # Gasp + shout a catchphrase.
            else:
                return                          # Still idle; nothing else to do.

        # --- Attack if close enough ---
        if dist <= config.ENEMY_ATTACK_RANGE:
            self.state = "attack"               # Enter the attack state.
            # Only strike when the cooldown has elapsed.
            if self.attack_cd <= 0 and not player.dead:
                player.take_damage(config.ENEMY_DAMAGE)  # Hurt the player.
                self.attack_cd = config.ENEMY_ATTACK_COOLDOWN  # Reset cooldown.
                self.attack_pose_t = 0.3        # Hold the attack pose briefly.
                self._say(audio, "enemy_attack")  # Shout + attack blip.
            return                              # Don't also move this frame.

        # --- Otherwise chase the player ---
        self.state = "chase"                    # Make sure we're in chase state.
        # If we somehow lost sight for a long path it's fine; keep pursuing.
        if dist > 0:
            # Normalized direction toward the player.
            nx = dx / dist                      # Unit x toward player.
            ny = dy / dist                      # Unit y toward player.
            # How far we move this frame.
            step = config.ENEMY_SPEED * dt
            # Proposed new position.
            mx = self.x + nx * step             # Candidate x.
            my = self.y + ny * step             # Candidate y.
            # Axis-separated movement so she slides along walls instead of sticking.
            if not self._blocked(level, mx, self.y):
                self.x = mx                     # Accept x movement.
            if not self._blocked(level, self.x, my):
                self.y = my                     # Accept y movement.

    # ----- combat + rendering ------------------------------------------------

    def hit(self, damage, audio):
        """Apply damage to this enemy; return True if this blow killed her."""
        # Ignore hits on an already-fainted girl.
        if self.state == "dead":
            return False
        # Subtract the damage.
        self.health -= damage
        # Play a generic impact sound for feedback.
        audio.play("impact")
        # Check for death.
        if self.health <= 0:
            self.health = 0                     # Clamp.
            self.state = "dead"                 # Switch to the fainted state.
            self._say(audio, "enemy_death")     # Defeated warble + final shout.
            return True                         # Report the kill.
        return False                            # Survived the hit.

    def current_sprite(self):
        """Return (Surface, vscale) for this enemy's current animation frame."""
        # A fainted girl always shows the "dead" frame, drawn shorter.
        if self.state == "dead":
            return self.sprites["dead"], 0.55
        # While the attack pose timer is active, show the attack frame.
        if self.attack_pose_t > 0:
            return self.sprites["attack"], 0.95
        # Otherwise alternate the two walk frames a few times per second.
        frame = int(self.anim_t * 4) % 2        # 0 or 1, toggling ~4x/sec.
        return self.sprites["walk"][frame], 0.95

    @property
    def alive(self):
        """Convenience flag: True while she can still fight."""
        return self.state != "dead"
