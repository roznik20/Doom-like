"""player.py — the isekai'd hero: position, facing, movement, and all vitals.

Beyond position + facing, the player now tracks health, mana, armor, per-type
ammo, kill count, and active powerup timers (Quad Damage, Haste, Divine
Shield). Movement is collision-checked against walls (and closed doors) with
axis-separated "wall sliding".
"""

import math                # Trig for converting the facing angle into motion.
from . import config       # Speeds, radius, vital caps, ammo, powerups.


class Player:
    """Holds all mutable state for the hero and updates it each frame."""

    def __init__(self, x, y):
        self.x = x                       # World x position.
        self.y = y                       # World y position.
        self.angle = 0.0                 # Facing direction in radians.
        self.health = config.MAX_HEALTH  # Current health.
        self.mana = config.MAX_MANA      # Current mana (Spirit Bolt fuel).
        self.armor = 0                   # Current armor (soaks part of damage).
        # Per-type ammunition, copied so we never mutate the config defaults.
        self.ammo = dict(config.START_AMMO)
        self.dead = False                # Set True by combat when health hits 0.
        self.kills = 0                   # Lifetime kills (for stats).
        # Active powerup timers (seconds remaining; 0 = inactive).
        self.quad_timer = 0.0            # Quad Damage.
        self.haste_timer = 0.0           # Haste (move faster).
        self.shield_timer = 0.0          # Divine Shield (invulnerable).
        # True for one frame after taking damage (so game.py can flash/shake).
        self.just_hurt = False

    def reset(self, x, y, start_health):
        """Reposition and fully restore the player for a new level/run."""
        self.x = x                       # New spawn x.
        self.y = y                       # New spawn y.
        self.angle = 0.0                 # Reset facing.
        self.health = start_health       # Difficulty-dependent start health.
        self.mana = config.MAX_MANA      # Refill mana.
        self.armor = 0                   # No armor to start.
        self.ammo = dict(config.START_AMMO)  # Reset ammo to defaults.
        self.dead = False                # Alive again.
        self.quad_timer = 0.0            # Clear powerups.
        self.haste_timer = 0.0
        self.shield_timer = 0.0

    # ----- collision ---------------------------------------------------------

    def _is_wall(self, level, x, y):
        """True if (x, y) is inside a solid wall (treating open doors as clear)."""
        gx, gy = int(x), int(y)
        if gx < 0 or gy < 0 or gx >= level["width"] or gy >= level["height"]:
            return True                  # Out of bounds = solid.
        tile = level["grid"][gy][gx]
        if tile == 0:
            return False                 # Empty floor.
        if tile == config.TEX_DOOR:
            # A door is passable once it has slid mostly open.
            return level.get("door_frac", {}).get((gx, gy), 0.0) < 0.85
        return True                      # Any other non-zero tile is solid.

    def _blocked(self, level, x, y):
        """Collision check around the player's radius."""
        r = config.PLAYER_RADIUS
        return (self._is_wall(level, x - r, y) or
                self._is_wall(level, x + r, y) or
                self._is_wall(level, x, y - r) or
                self._is_wall(level, x, y + r))

    # ----- powerup helpers ---------------------------------------------------

    def damage_multiplier(self):
        """Return the current outgoing-damage multiplier (Quad Damage)."""
        return config.POWERUP_QUAD_MULT if self.quad_timer > 0 else 1.0

    def speed_multiplier(self):
        """Return the current movement-speed multiplier (Haste)."""
        return config.POWERUP_HASTE_MULT if self.haste_timer > 0 else 1.0

    def invulnerable(self):
        """True while the Divine Shield is active."""
        return self.shield_timer > 0

    # ----- per-frame update --------------------------------------------------

    def update(self, dt, inp, level):
        """Advance facing, position, mana regen, and powerup timers."""
        # --- Turning ---
        if inp.left:
            self.angle -= config.TURN_SPEED * dt
        if inp.right:
            self.angle += config.TURN_SPEED * dt
        self.angle += inp.mouse_dx * config.MOUSE_SENSITIVITY

        # --- Movement speed (walk, sprint, haste) ---
        speed = config.MOVE_SPEED * self.speed_multiplier()
        if inp.sprint:
            speed *= config.SPRINT_MULTIPLIER
        step = speed * dt

        # Forward + strafe basis vectors from the facing angle.
        fwd_x = math.cos(self.angle)
        fwd_y = math.sin(self.angle)
        strafe_x = math.cos(self.angle + math.pi / 2)
        strafe_y = math.sin(self.angle + math.pi / 2)

        # Accumulate desired movement from pressed keys.
        dx = 0.0
        dy = 0.0
        if inp.forward:
            dx += fwd_x * step; dy += fwd_y * step
        if inp.back:
            dx -= fwd_x * step; dy -= fwd_y * step
        if inp.strafe_left:
            dx -= strafe_x * step; dy -= strafe_y * step
        if inp.strafe_right:
            dx += strafe_x * step; dy += strafe_y * step

        # Remember whether we actually moved (for weapon bob).
        self.moving = (dx != 0 or dy != 0)

        # Axis-separated movement -> wall sliding.
        if not self._blocked(level, self.x + dx, self.y):
            self.x += dx
        if not self._blocked(level, self.x, self.y + dy):
            self.y += dy

        # --- Mana regen ---
        self.mana = min(config.MAX_MANA, self.mana + config.MANA_REGEN * dt)

        # --- Powerup countdowns ---
        if self.quad_timer > 0:
            self.quad_timer = max(0.0, self.quad_timer - dt)
        if self.haste_timer > 0:
            self.haste_timer = max(0.0, self.haste_timer - dt)
        if self.shield_timer > 0:
            self.shield_timer = max(0.0, self.shield_timer - dt)

    # ----- vitals ------------------------------------------------------------

    def take_damage(self, amount):
        """Apply damage, accounting for the shield + armor, and flag death."""
        if self.invulnerable():
            return                       # Divine Shield negates all damage.
        # Armor soaks a fraction of the hit while it lasts.
        if self.armor > 0:
            absorbed = min(self.armor, amount * config.ARMOR_ABSORB)
            self.armor -= absorbed       # Spend that much armor.
            amount -= absorbed           # Reduce the damage to health.
        self.health -= amount            # Apply remaining damage to health.
        self.just_hurt = True            # Mark for the flash/shake this frame.
        if self.health <= 0:
            self.health = 0
            self.dead = True

    def heal(self, amount):
        """Restore health up to the maximum."""
        self.health = min(config.MAX_HEALTH, self.health + amount)

    def add_mana(self, amount):
        """Restore mana up to the maximum."""
        self.mana = min(config.MAX_MANA, self.mana + amount)

    def add_armor(self, amount):
        """Restore armor up to the maximum."""
        self.armor = min(config.MAX_ARMOR, self.armor + amount)

    def add_ammo(self, kind, amount):
        """Add ammo of a type, capped at its maximum."""
        cap = config.MAX_AMMO.get(kind, 999)
        self.ammo[kind] = min(cap, self.ammo.get(kind, 0) + amount)
