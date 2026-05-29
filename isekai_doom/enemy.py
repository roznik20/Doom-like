"""enemy.py — the anime demon-girls, their AI, and the boss.

Five enemy archetypes, each with distinct stats and behavior:

  imp     — basic, fairly quick melee chibi.
  caster  — floats, keeps her distance, throws homing-free heart projectiles.
  brute   — huge, slow, very tanky, heavy melee club.
  dasher  — tiny, winged, extremely fast swarmer.
  boss    — the Demon Queen: hybrid melee + fireball volleys + summons dashers.

The AI is a small readable state machine:
    idle  -> wait until the player is seen (range + line of sight)
    chase -> approach (melee) or strafe to a preferred distance (ranged)
    attack/fire -> melee hit or spawn projectile(s) on a cooldown
    dead  -> collapse into a fainted sprite that stays as scenery

Difficulty multipliers (from config.DIFFICULTIES) scale health/damage/speed/fire
rate at spawn time.
"""

import math               # Distance + direction math.
import random             # Random palettes, catchphrases, summon jitter.
from . import config      # Tuning values.
from . import maps        # The catchphrase list.


# Base stats per archetype (the "Reborn Hero" baseline; difficulty scales them).
ENEMY_TYPES = {
    "imp": {
        "hp": 80, "speed": 1.7, "melee_dmg": 11, "atk_range": 1.0, "atk_cd": 1.0,
        "ranged": False, "score": 100, "vscale": 0.95, "radius": 0.3,
    },
    "caster": {
        "hp": 70, "speed": 1.2, "melee_dmg": 0, "atk_range": 1.0, "atk_cd": 1.0,
        "ranged": True, "preferred": 4.5, "proj_dmg": 9, "fire_cd": 1.8,
        "volley": 1, "spread": 0.0, "proj_kind": "heart",
        "score": 150, "vscale": 0.95, "radius": 0.3,
    },
    "brute": {
        "hp": 220, "speed": 1.0, "melee_dmg": 24, "atk_range": 1.3, "atk_cd": 1.4,
        "ranged": False, "score": 250, "vscale": 1.3, "radius": 0.42,
    },
    "dasher": {
        "hp": 45, "speed": 2.9, "melee_dmg": 8, "atk_range": 0.9, "atk_cd": 0.8,
        "ranged": False, "score": 120, "vscale": 0.8, "radius": 0.26,
    },
    "bomber": {
        "hp": 50, "speed": 2.4, "melee_dmg": 0, "atk_range": 1.1, "atk_cd": 1.0,
        "ranged": False, "score": 130, "vscale": 0.85, "radius": 0.3,
        "is_bomber": True, "explode_dmg": 36, "explode_radius": 1.8,
    },
    "healer": {
        "hp": 90, "speed": 1.2, "melee_dmg": 0, "atk_range": 1.0, "atk_cd": 1.0,
        "ranged": False, "score": 200, "vscale": 0.95, "radius": 0.3,
        "is_healer": True, "heal_amount": 28, "heal_interval": 3.0, "heal_radius": 5.5,
    },
    "boss": {
        "hp": 1600, "speed": 1.3, "melee_dmg": 30, "atk_range": 1.7, "atk_cd": 1.2,
        "ranged": True, "preferred": 3.5, "proj_dmg": 14, "fire_cd": 1.6,
        "volley": 3, "spread": 0.32, "proj_kind": "fireball",
        "summon": True, "summon_interval": 6.0,
        "score": 2500, "vscale": 2.4, "radius": 0.6, "is_boss": True,
    },
}


class Enemy:
    """One demon-girl (or the boss): position, stats, AI state, animation."""

    def __init__(self, etype, x, y, sprite_set, diff):
        self.etype = etype                       # Archetype key.
        base = ENEMY_TYPES[etype]                # Base stat block.
        self.x = x                               # World x.
        self.y = y                               # World y.
        # --- Stats scaled by the chosen difficulty multipliers ---
        self.max_hp = base["hp"] * diff["enemy_health"]
        self.hp = self.max_hp
        self.speed = base["speed"] * diff["enemy_speed"]
        self.melee_dmg = base.get("melee_dmg", 0) * diff["enemy_damage"]
        self.atk_range = base.get("atk_range", 1.0)
        self.atk_cd_max = base.get("atk_cd", 1.0)
        self.ranged = base.get("ranged", False)
        self.preferred = base.get("preferred", 4.0)
        self.proj_dmg = base.get("proj_dmg", 0) * diff["enemy_damage"]
        self.fire_cd_max = base.get("fire_cd", 1.5) / diff["enemy_fire_rate"]
        self.volley = base.get("volley", 1)
        self.spread = base.get("spread", 0.0)
        self.proj_kind = base.get("proj_kind", "heart")
        self.can_summon = base.get("summon", False)
        self.summon_interval = base.get("summon_interval", 6.0)
        self.score = base.get("score", 100)
        self.vscale = base.get("vscale", 0.95)
        self.radius = base.get("radius", 0.3)
        self.is_boss = base.get("is_boss", False)
        # Bomber (kamikaze) stats.
        self.is_bomber = base.get("is_bomber", False)
        self.explode_dmg = base.get("explode_dmg", 0) * diff["enemy_damage"]
        self.explode_radius = base.get("explode_radius", 1.5)
        # Healer (support) stats.
        self.is_healer = base.get("is_healer", False)
        self.heal_amount = base.get("heal_amount", 0)
        self.heal_interval = base.get("heal_interval", 3.0)
        self.heal_radius = base.get("heal_radius", 5.0)
        self.heal_cd = self.heal_interval

        self.sprites = sprite_set                # Animation frames.
        self.state = "idle"                      # AI state.
        self.attack_cd = 0.0                     # Melee cooldown timer.
        self.fire_cd = 0.0                       # Ranged cooldown timer.
        self.summon_cd = self.summon_interval    # Summon cooldown timer.
        self.anim_t = 0.0                        # Walk-cycle timer.
        self.attack_pose_t = 0.0                 # How long to hold the attack pose.
        self.shout = None                        # One-shot catchphrase for the HUD.
        self.aggroed = False                     # Whether she has noticed the player.
        self.pain_t = 0.0                        # Brief flinch timer after being hit.
        self.los_cd = 0.0                        # Throttle timer for the LOS cache.
        self.los_val = False                     # Last cached line-of-sight result.

    # ----- helpers -----------------------------------------------------------

    def _is_wall(self, level, x, y):
        """True if (x, y) is solid (closed doors block; open doors don't)."""
        gx, gy = int(x), int(y)
        if gx < 0 or gy < 0 or gx >= level["width"] or gy >= level["height"]:
            return True
        tile = level["grid"][gy][gx]
        if tile == 0:
            return False
        if tile == config.TEX_DOOR:
            return level.get("door_frac", {}).get((gx, gy), 0.0) < 0.85
        return True

    def _blocked(self, level, x, y):
        """Collision check around the enemy's radius."""
        r = self.radius
        return (self._is_wall(level, x - r, y) or self._is_wall(level, x + r, y) or
                self._is_wall(level, x, y - r) or self._is_wall(level, x, y + r))

    def _has_los(self, level, tx, ty):
        """Straight-line visibility check to a target point."""
        dx = tx - self.x; dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist == 0:
            return True
        # Coarser sampling (every 0.2 tiles) keeps this cheap with many enemies.
        steps = max(1, int(dist / 0.2))
        sx = dx / steps; sy = dy / steps
        cx, cy = self.x, self.y
        for _ in range(steps):
            cx += sx; cy += sy
            if self._is_wall(level, cx, cy):
                return False
        return True

    def _visible(self, level, player):
        """Line-of-sight to the player, cached and refreshed a few times/sec."""
        # Reuse the cached result until the throttle timer expires.
        if self.los_cd > 0:
            return self.los_val
        self.los_cd = 0.12                       # Refresh ~8x per second.
        self.los_val = self._has_los(level, player.x, player.y)
        return self.los_val

    def _say(self, audio, sound):
        """Pick a catchphrase to display and play a matching voice blip."""
        self.shout = random.choice(maps.CATCHPHRASES)
        audio.play(sound)

    def _move_toward(self, level, tx, ty, dt, sign=1.0):
        """Move toward (sign=+1) or away from (sign=-1) a target with sliding."""
        dx = tx - self.x; dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist == 0:
            return
        nx = (dx / dist) * sign; ny = (dy / dist) * sign
        step = self.speed * dt
        mx = self.x + nx * step; my = self.y + ny * step
        if not self._blocked(level, mx, self.y):
            self.x = mx
        if not self._blocked(level, self.x, my):
            self.y = my

    # ----- per-frame update --------------------------------------------------

    def update(self, dt, player, level, game):
        """Run AI for one frame; may damage the player or spawn projectiles/minions."""
        if self.state == "dead":
            return                               # Fainted girls do nothing.

        # Tick timers.
        self.anim_t += dt
        if self.attack_cd > 0: self.attack_cd = max(0.0, self.attack_cd - dt)
        if self.fire_cd > 0: self.fire_cd = max(0.0, self.fire_cd - dt)
        if self.summon_cd > 0: self.summon_cd = max(0.0, self.summon_cd - dt)
        if self.attack_pose_t > 0: self.attack_pose_t = max(0.0, self.attack_pose_t - dt)
        if self.pain_t > 0: self.pain_t = max(0.0, self.pain_t - dt)
        if self.los_cd > 0: self.los_cd = max(0.0, self.los_cd - dt)
        if self.heal_cd > 0: self.heal_cd = max(0.0, self.heal_cd - dt)

        # Distance to the player.
        dx = player.x - self.x; dy = player.y - self.y
        dist = math.hypot(dx, dy)

        # --- Acquire target ---
        if not self.aggroed:
            if dist < config.ENEMY_SIGHT_RANGE and self._visible(level, player):
                self.aggroed = True
                self.state = "chase"
                self._say(game.audio, "aggro")
            else:
                return                           # Stay idle.

        # Line of sight (cached) is only needed by ranged attackers.
        los = self._visible(level, player) if self.ranged else True

        # --- Bomber: rush the player and detonate ---
        if self.is_bomber:
            self.state = "attack" if dist <= self.atk_range + 0.6 else "chase"
            self._move_toward(level, player.x, player.y, dt, sign=1.0)
            if dist <= self.atk_range:
                game.bomber_explode(self)        # Game applies AoE + kills her.
            return

        # --- Healer: hang back and periodically heal nearby demon-girls ---
        if self.is_healer:
            if dist < 3.0:
                self._move_toward(level, player.x, player.y, dt, sign=-1.0)  # Keep clear.
            elif dist > 6.0:
                self._move_toward(level, player.x, player.y, dt, sign=1.0)
            if self.heal_cd <= 0:
                self.heal_cd = self.heal_interval
                if game.heal_allies(self):       # Returns True if anyone was healed.
                    self.attack_pose_t = 0.35
                    self._say(game.audio, "powerup")
            return

        # --- Boss: periodically summon a dasher minion ---
        if self.can_summon and self.summon_cd <= 0 and dist < config.ENEMY_SIGHT_RANGE:
            self.summon_cd = self.summon_interval
            game.spawn_minion("dasher", self.x, self.y)
            self.set_shout_text("Come, my children~!")
            game.audio.play("aggro")

        # --- Ranged behavior (casters + boss) ---
        if self.ranged:
            # Keep a preferred distance: back off if too close, approach if too far.
            if dist < self.preferred - 0.5:
                self._move_toward(level, player.x, player.y, dt, sign=-1.0)  # Retreat.
            elif dist > self.preferred + 0.5:
                self._move_toward(level, player.x, player.y, dt, sign=1.0)   # Close in.
            # Fire a volley if we have a clear shot and the cooldown is up.
            if los and self.fire_cd <= 0 and dist < config.ENEMY_SIGHT_RANGE:
                self.fire_cd = self.fire_cd_max
                self.attack_pose_t = 0.35
                base_ang = math.atan2(dy, dx)
                # Spread the volley around the aim direction.
                for i in range(self.volley):
                    if self.volley > 1:
                        offset = (i / (self.volley - 1) - 0.5) * self.spread * 2
                    else:
                        offset = 0.0
                    game.spawn_enemy_projectile(self.x, self.y, base_ang + offset,
                                                self.proj_dmg, self.proj_kind)
                self._say(game.audio, "enemy_attack")

        # --- Melee behavior (imps, brutes, dashers; boss also melees up close) ---
        if (not self.ranged) or self.is_boss:
            if dist <= self.atk_range:
                self.state = "attack"
                if self.attack_cd <= 0 and not player.dead and self.melee_dmg > 0:
                    player.take_damage(self.melee_dmg)
                    self.attack_cd = self.atk_cd_max
                    self.attack_pose_t = 0.3
                    self._say(game.audio, "enemy_attack")
                return                           # Don't also move while striking.
            # Otherwise chase (ranged boss only chases if not maintaining distance).
            if not self.ranged:
                self.state = "chase"
                self._move_toward(level, player.x, player.y, dt, sign=1.0)

    # ----- combat + rendering ------------------------------------------------

    def set_shout_text(self, text):
        """Force a specific shout line (used for the boss's summon line)."""
        self.shout = text

    def hit(self, damage, audio):
        """Apply damage; return True if this blow defeated her."""
        if self.state == "dead":
            return False
        self.hp -= damage
        self.pain_t = 0.12                       # Brief flinch.
        audio.play("impact")
        if self.hp <= 0:
            self.hp = 0
            self.state = "dead"
            self._say(audio, "enemy_death")
            return True
        return False

    def current_sprite(self):
        """Return (Surface, vscale) for this enemy's current frame."""
        if self.state == "dead":
            return self.sprites["dead"], self.vscale * 0.6
        if self.attack_pose_t > 0:
            return self.sprites["attack"], self.vscale
        frame = int(self.anim_t * 4) % 2
        return self.sprites["walk"][frame], self.vscale

    @property
    def alive(self):
        """True while she can still fight."""
        return self.state != "dead"
