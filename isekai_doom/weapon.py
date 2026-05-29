"""weapon.py — the hero's full arsenal, projectiles, and view-models.

Five weapons (defined in config.WEAPONS):
  1 HOLY SWORD     — instant short-range cone melee. No ammo, fast.
  2 SPIRIT BOLT    — spends mana; launches a travelling magic orb.
  3 SERAPH SHOTGUN — spends shells; fires a spread of instant holy pellets.
  4 ROSARY GATLING — spends rounds; very fast instant single shots.
  5 GODDESS BEAM   — spends energy; a piercing instant beam that hits all
                     enemies in a straight line.

`WeaponSystem` tracks the equipped weapon, cooldowns, ammo spending, the
firing animation, weapon bob while walking, and the muzzle flash. It returns a
small descriptor when you fire; game.py performs the actual damage resolution
(hitscans/beams need to see the enemies and walls).
"""

import math               # Trig for projectiles + view-model motion.
import pygame             # Drawing the view-model.
from . import config      # Weapon stats, bob/flash timings.


class Projectile:
    """A travelling orb fired by the player (Spirit Bolt) or an enemy."""

    def __init__(self, x, y, angle, speed, damage, radius, surf, owner, trail_color=None):
        self.x = x                              # World x.
        self.y = y                              # World y.
        self.dx = math.cos(angle) * speed       # X velocity.
        self.dy = math.sin(angle) * speed       # Y velocity.
        self.damage = damage                    # Damage on contact.
        self.radius = radius                    # Collision radius.
        self.surf = surf                        # Billboard sprite.
        self.owner = owner                      # "player" or "enemy".
        self.alive = True                       # False once it hits something.
        self.trail_color = trail_color          # Color for its particle trail (or None).

    def update(self, dt, level):
        """Advance the projectile; die if it flies into a wall/out of bounds."""
        self.x += self.dx * dt                  # Step x.
        self.y += self.dy * dt                  # Step y.
        gx, gy = int(self.x), int(self.y)        # Grid cell.
        if gx < 0 or gy < 0 or gx >= level["width"] or gy >= level["height"]:
            self.alive = False                  # Off the map.
            return
        tile = level["grid"][gy][gx]            # Wall id at the cell.
        # A wall stops the projectile (an open door does not).
        if tile != 0:
            if tile == config.TEX_DOOR and level.get("door_frac", {}).get((gx, gy), 0.0) >= 1.0:
                return                          # Pass through a fully-open door.
            self.alive = False                  # Hit a wall.


class WeaponSystem:
    """Tracks the equipped weapon, cooldowns, ammo, bob, and view-model."""

    def __init__(self, sprite_lookup):
        # A callable/dict that returns a projectile sprite by name.
        self.sprites = sprite_lookup
        # Which weapon is equipped (a key into config.WEAPONS).
        self.current = "sword"
        # Seconds remaining before the player may fire again.
        self.cooldown = 0.0
        # Animation timer (counts down while a swing/cast plays).
        self.anim = 0.0
        self.anim_len = 0.30
        # Muzzle-flash timer for guns.
        self.muzzle = 0.0
        # Weapon-bob phase + the resulting pixel offset.
        self.bob_phase = 0.0
        self.bob_x = 0.0
        self.bob_y = 0.0

    # ----- selection --------------------------------------------------------

    def switch(self, name):
        """Equip a weapon by key if it exists."""
        if name in config.WEAPONS:
            self.current = name

    def switch_slot(self, slot):
        """Equip the weapon bound to a number-key slot (1..5)."""
        for key, w in config.WEAPONS.items():
            if w["slot"] == slot:
                self.current = key
                return

    def cycle(self, direction):
        """Cycle to the next/previous weapon (mouse wheel). direction = +1/-1."""
        order = config.WEAPON_ORDER
        i = order.index(self.current)            # Current index.
        self.current = order[(i + direction) % len(order)]  # Wrap around.

    def display_name(self):
        """HUD-friendly name of the equipped weapon."""
        return config.WEAPONS[self.current]["name"]

    # ----- per-frame update -------------------------------------------------

    def update(self, dt, moving):
        """Tick cooldown/animation/muzzle timers and advance the weapon bob."""
        if self.cooldown > 0:
            self.cooldown = max(0.0, self.cooldown - dt)
        if self.anim > 0:
            self.anim = max(0.0, self.anim - dt)
        if self.muzzle > 0:
            self.muzzle = max(0.0, self.muzzle - dt)
        # Advance the bob phase only while the player is walking.
        if moving:
            self.bob_phase += dt * config.WEAPON_BOB_SPEED
        else:
            # Ease the bob back toward rest when standing still.
            self.bob_phase += dt * 2.0
        # A figure-eight bob: x uses the phase, y uses double frequency.
        self.bob_x = math.sin(self.bob_phase) * config.WEAPON_BOB_AMOUNT * (1.0 if moving else 0.2)
        self.bob_y = abs(math.sin(self.bob_phase * 2)) * config.WEAPON_BOB_AMOUNT * (1.0 if moving else 0.2)

    # ----- firing -----------------------------------------------------------

    def _has_ammo(self, player):
        """Return True if the equipped weapon can be paid for right now."""
        w = config.WEAPONS[self.current]
        ammo = w.get("ammo")
        if ammo is None:
            return True                          # Free weapon (sword).
        if ammo == "mana":
            return player.mana >= w["ammo_cost"]  # Mana-based.
        return player.ammo.get(ammo, 0) >= w["ammo_cost"]  # Item ammo.

    def _spend_ammo(self, player):
        """Deduct the equipped weapon's ammo/mana cost."""
        w = config.WEAPONS[self.current]
        ammo = w.get("ammo")
        if ammo is None:
            return
        if ammo == "mana":
            player.mana -= w["ammo_cost"]
        else:
            player.ammo[ammo] -= w["ammo_cost"]

    def try_fire(self, player):
        """Attempt to fire. Returns a descriptor dict, or None if it can't fire.

        Descriptors (handled by game.py):
          {"kind":"melee","damage","range","arc"}
          {"kind":"projectile","proj":Projectile}
          {"kind":"hitscan","damage","pellets","spread","range"}
          {"kind":"beam","damage","range"}
        """
        if self.cooldown > 0:
            return None                          # Still cooling down.
        if not self._has_ammo(player):
            return ("noammo", None)              # Signal "click" / no ammo.

        w = config.WEAPONS[self.current]
        # Pay the cost and start the cooldown + animation.
        self._spend_ammo(player)
        self.cooldown = w["cooldown"]
        self.anim = self.anim_len = w["anim_len"]
        kind = w["kind"]

        if kind == "melee":
            return {"kind": "melee", "damage": w["damage"],
                    "range": w["range"], "arc": w["arc"]}

        if kind == "projectile":
            # Muzzle flash + spawn the orb just ahead of the player.
            self.muzzle = config.MUZZLE_FLASH_TIME
            sx = player.x + math.cos(player.angle) * 0.4
            sy = player.y + math.sin(player.angle) * 0.4
            proj = Projectile(sx, sy, player.angle, w["speed"], w["damage"],
                              w["radius"], self.sprites["bolt"], "player",
                              trail_color=(120, 200, 255))
            return {"kind": "projectile", "proj": proj}

        if kind == "hitscan":
            self.muzzle = config.MUZZLE_FLASH_TIME
            return {"kind": "hitscan", "damage": w["damage"],
                    "pellets": w["pellets"], "spread": w["spread"], "range": w["range"]}

        if kind == "beam":
            self.muzzle = config.MUZZLE_FLASH_TIME * 3
            return {"kind": "beam", "damage": w["damage"], "range": w["range"]}

        return None

    # ----- view-model drawing -----------------------------------------------

    def draw_viewmodel(self, screen):
        """Draw the first-person weapon (with bob + animation + muzzle flash)."""
        w, h = screen.get_size()
        # Animation progress 0..1 (1 right after firing, easing to 0).
        t = (self.anim / self.anim_len) if self.anim_len > 0 else 0.0
        # Bob offsets applied to the whole view-model.
        bx, by = self.bob_x, self.bob_y
        kind = config.WEAPONS[self.current]["kind"]
        if self.current == "sword":
            self._draw_sword(screen, w, h, t, bx, by)
        elif self.current == "bolt":
            self._draw_staff(screen, w, h, t, bx, by)
        elif self.current == "shotgun":
            self._draw_shotgun(screen, w, h, t, bx, by)
        elif self.current == "gatling":
            self._draw_gatling(screen, w, h, t, bx, by)
        elif self.current == "beam":
            self._draw_beamgun(screen, w, h, t, bx, by)

    def _draw_sword(self, screen, w, h, t, bx, by):
        """Holy Sword rising from the lower-right, swinging on fire."""
        swing = math.sin(t * math.pi) * 0.9
        base_x = w * 0.72 + bx
        base_y = h + by
        tip_x = base_x - math.sin(swing) * w * 0.5
        tip_y = base_y - h * 0.7 - math.cos(swing) * 40
        pygame.draw.line(screen, (220, 230, 255), (base_x, base_y), (tip_x, tip_y), 14)
        pygame.draw.line(screen, (255, 255, 210), (base_x, base_y), (tip_x, tip_y), 5)
        gx = base_x - math.sin(swing) * 40
        gy = base_y - 90
        pygame.draw.line(screen, (255, 200, 60), (gx - 34, gy + 14), (gx + 34, gy - 14), 10)
        pygame.draw.line(screen, (90, 50, 20), (base_x, base_y), (gx, gy), 12)

    def _draw_staff(self, screen, w, h, t, bx, by):
        """Spirit staff with a charging orb in the lower-right."""
        kick = math.sin(t * math.pi) * 30
        bottom = (w * 0.78 + bx, h + by)
        top = (w * 0.6 - kick + bx, h * 0.45 - kick + by)
        pygame.draw.line(screen, (120, 80, 50), bottom, top, 12)
        pygame.draw.circle(screen, (80, 60, 40), (int(top[0]), int(top[1])), 22, 5)
        glow = 12 + int(t * 8)
        pygame.draw.circle(screen, (120, 200, 255), (int(top[0]), int(top[1])), glow)
        pygame.draw.circle(screen, (230, 245, 255), (int(top[0]), int(top[1])), glow // 2)

    def _draw_shotgun(self, screen, w, h, t, bx, by):
        """Twin-barrel seraph shotgun, recoiling on fire, with a muzzle flash."""
        recoil = math.sin(t * math.pi) * 36
        cx = w * 0.5 + bx
        base_y = h - recoil + by
        # Two stubby barrels.
        pygame.draw.rect(screen, (210, 210, 220), (cx - 36, base_y - 150, 28, 150), border_radius=6)
        pygame.draw.rect(screen, (210, 210, 220), (cx + 8, base_y - 150, 28, 150), border_radius=6)
        # Wooden stock between/below.
        pygame.draw.rect(screen, (120, 70, 30), (cx - 20, base_y - 70, 40, 90), border_radius=8)
        # Golden seraph trim.
        pygame.draw.rect(screen, (240, 200, 60), (cx - 40, base_y - 90, 80, 12), border_radius=4)
        # Muzzle flash burst at the barrel tips.
        if self.muzzle > 0:
            for tip in (cx - 22, cx + 22):
                pygame.draw.circle(screen, (255, 240, 160), (int(tip), int(base_y - 150)), 22)
                pygame.draw.circle(screen, (255, 180, 60), (int(tip), int(base_y - 150)), 12)

    def _draw_gatling(self, screen, w, h, t, bx, by):
        """Spinning rosary gatling with a rapid muzzle flash."""
        spin = self.bob_phase * 3
        cx = w * 0.55 + bx
        base_y = h + by
        # The rotating barrel cluster (a few circles offset by the spin).
        for i in range(4):
            a = spin + i * (math.pi / 2)
            ox = math.cos(a) * 12
            pygame.draw.rect(screen, (90, 90, 100), (cx - 14 + ox, base_y - 140, 28, 140), border_radius=6)
        pygame.draw.rect(screen, (60, 40, 20), (cx - 24, base_y - 60, 48, 80), border_radius=10)
        # Rapid muzzle flash.
        if self.muzzle > 0:
            pygame.draw.circle(screen, (255, 240, 150), (int(cx), int(base_y - 140)), 20)
            pygame.draw.circle(screen, (255, 170, 40), (int(cx), int(base_y - 140)), 10)

    def _draw_beamgun(self, screen, w, h, t, bx, by):
        """Goddess beam emitter; fires a bright vertical glow when shooting."""
        cx = w * 0.5 + bx
        base_y = h + by
        # A crystalline emitter.
        pygame.draw.polygon(screen, (120, 220, 255),
                            [(cx - 30, base_y), (cx + 30, base_y),
                             (cx + 18, base_y - 120), (cx - 18, base_y - 120)])
        pygame.draw.circle(screen, (200, 245, 255), (int(cx), int(base_y - 120)), 18)
        # The beam itself flares up the screen while firing.
        if self.muzzle > 0:
            beam = pygame.Surface((w, h), pygame.SRCALPHA)
            alpha = int(180 * (self.muzzle / (config.MUZZLE_FLASH_TIME * 3)))
            pygame.draw.line(beam, (180, 240, 255, alpha), (cx, base_y - 120), (w // 2, 0), 26)
            pygame.draw.line(beam, (255, 255, 255, alpha), (cx, base_y - 120), (w // 2, 0), 10)
            screen.blit(beam, (0, 0))
