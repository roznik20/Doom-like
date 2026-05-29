"""weapon.py — the hero's arsenal and the Spirit Bolt projectile.

Two weapons:
  * Holy Sword  — instant, short-range cone melee. No ammo, just a cooldown.
  * Spirit Bolt — spends mana to launch a homing-free magic orb that flies
                  forward until it hits a wall or a demon-girl.

`WeaponSystem` tracks which weapon is equipped, the firing cooldowns, and the
swing/cast animation, and it draws the first-person "view-model" (the weapon
you see in front of you). The actual damage resolution lives in game.py so it
can see both the player and the enemies; this module just reports intent.
"""

import math               # Trig for projectile velocity and view-model motion.
import pygame             # Drawing the view-model.
from . import config      # Cooldowns, costs, speeds.


class Projectile:
    """A single in-flight Spirit Bolt."""

    def __init__(self, x, y, angle, surf):
        # Current world position of the bolt.
        self.x = x                          # Bolt x.
        self.y = y                          # Bolt y.
        # Velocity components derived from the firing angle and bolt speed.
        self.dx = math.cos(angle) * config.BOLT_SPEED   # X velocity.
        self.dy = math.sin(angle) * config.BOLT_SPEED   # Y velocity.
        # The billboard sprite used to draw the bolt in the world.
        self.surf = surf
        # Whether the bolt is still active (False once it hits something).
        self.alive = True

    def update(self, dt, level):
        """Advance the bolt; deactivate it if it flies into a wall."""
        # Move the bolt forward by velocity * time.
        self.x += self.dx * dt              # Step x.
        self.y += self.dy * dt              # Step y.
        # Convert to grid indices to test for a wall collision.
        gx, gy = int(self.x), int(self.y)
        # Out of bounds counts as hitting something solid.
        if gx < 0 or gy < 0 or gx >= level["width"] or gy >= level["height"]:
            self.alive = False              # Kill the bolt.
            return
        # If the bolt entered a wall cell, deactivate it.
        if level["grid"][gy][gx] != 0:
            self.alive = False              # Kill the bolt.


class WeaponSystem:
    """Tracks the equipped weapon, cooldowns, and draws the view-model."""

    def __init__(self, bolt_sprite):
        # Sprite handed to each spawned Projectile so it can be billboarded.
        self.bolt_sprite = bolt_sprite
        # Which weapon is equipped: "sword" or "bolt".
        self.current = "sword"
        # Seconds remaining before the player may fire again.
        self.cooldown = 0.0
        # Animation timer (0 = idle); counts down while a swing/cast plays.
        self.anim = 0.0
        # How long the current weapon's animation lasts (set when fired).
        self.anim_len = 0.30

    def switch(self, name):
        """Equip a weapon by name if it's a valid choice."""
        # Only accept known weapon names.
        if name in ("sword", "bolt"):
            self.current = name             # Equip it.

    def display_name(self):
        """Return the HUD-friendly name of the equipped weapon."""
        # Map the internal id to a pretty label.
        return "HOLY SWORD" if self.current == "sword" else "SPIRIT BOLT"

    def update(self, dt):
        """Tick down the cooldown and animation timers each frame."""
        # Reduce the cooldown but never below zero.
        if self.cooldown > 0:
            self.cooldown = max(0.0, self.cooldown - dt)
        # Reduce the animation timer but never below zero.
        if self.anim > 0:
            self.anim = max(0.0, self.anim - dt)

    def try_fire(self, player):
        """Attempt to fire the equipped weapon.

        Returns one of:
          ("sword", None)               -> a melee swing happened (resolve a cone)
          ("bolt", Projectile)          -> a bolt was spawned (add to the world)
          None                          -> couldn't fire (on cooldown / no mana)
        """
        # Reject the shot if we're still on cooldown.
        if self.cooldown > 0:
            return None

        if self.current == "sword":
            # Start the swing cooldown + animation.
            self.cooldown = config.SWORD_COOLDOWN
            self.anim = self.anim_len = 0.30
            # Report a melee swing; game.py resolves the damage cone.
            return ("sword", None)

        # Otherwise the Spirit Bolt is equipped.
        # Refuse to cast if the player lacks the mana.
        if player.mana < config.BOLT_COST:
            return None
        # Spend the mana.
        player.mana -= config.BOLT_COST
        # Start the cast cooldown + animation.
        self.cooldown = config.BOLT_COOLDOWN
        self.anim = self.anim_len = 0.25
        # Spawn the bolt slightly in front of the player so it doesn't self-collide.
        spawn_x = player.x + math.cos(player.angle) * 0.4
        spawn_y = player.y + math.sin(player.angle) * 0.4
        bolt = Projectile(spawn_x, spawn_y, player.angle, self.bolt_sprite)
        # Report the new projectile so game.py can track it.
        return ("bolt", bolt)

    def draw_viewmodel(self, screen):
        """Draw the first-person weapon at the bottom of the screen."""
        # The window dimensions, used to position the view-model.
        w, h = screen.get_size()
        # Animation progress 0..1 (1 right after firing, easing back to 0).
        t = (self.anim / self.anim_len) if self.anim_len > 0 else 0.0

        if self.current == "sword":
            self._draw_sword(screen, w, h, t)   # Draw the melee weapon.
        else:
            self._draw_staff(screen, w, h, t)   # Draw the magic staff.

    def _draw_sword(self, screen, w, h, t):
        """Draw the Holy Sword rising from the lower-right, swinging on fire."""
        # The swing rotates the blade across the screen; map progress to an angle.
        swing = math.sin(t * math.pi) * 0.9    # Smooth out-and-back swing arc.
        # Base of the blade near the bottom-right of the screen.
        base_x = w * 0.72                      # Horizontal anchor of the hilt.
        base_y = h                              # Anchor at the very bottom edge.
        # The blade tip position, swung left as `swing` grows.
        tip_x = base_x - math.sin(swing) * w * 0.5    # Tip sweeps left during a swing.
        tip_y = base_y - h * 0.7 - math.cos(swing) * 40  # Tip rises up the screen.
        # Draw the wide steel blade as a thick line.
        pygame.draw.line(screen, (220, 230, 255), (base_x, base_y), (tip_x, tip_y), 14)
        # A bright holy-glow core down the middle of the blade.
        pygame.draw.line(screen, (255, 255, 210), (base_x, base_y), (tip_x, tip_y), 5)
        # The golden crossguard near the hilt (perpendicular short bar).
        gx = base_x - math.sin(swing) * 40     # Crossguard center x.
        gy = base_y - 90                        # Crossguard center y.
        pygame.draw.line(screen, (255, 200, 60),
                        (gx - 34, gy + 14), (gx + 34, gy - 14), 10)
        # The dark hilt handle below the crossguard.
        pygame.draw.line(screen, (90, 50, 20), (base_x, base_y), (gx, gy), 12)

    def _draw_staff(self, screen, w, h, t):
        """Draw the Spirit staff in the lower-right with a charging orb."""
        # A small recoil kick: the staff jolts up-left right after casting.
        kick = math.sin(t * math.pi) * 30      # Recoil amount in pixels.
        # The staff shaft, a thick diagonal line from bottom-right upward.
        bottom = (w * 0.78, h)                 # Shaft base at the bottom edge.
        top = (w * 0.6 - kick, h * 0.45 - kick)  # Shaft head, pulled by recoil.
        pygame.draw.line(screen, (120, 80, 50), bottom, top, 12)   # Wooden shaft.
        # The orb housing (a ring) at the head of the staff.
        pygame.draw.circle(screen, (80, 60, 40), (int(top[0]), int(top[1])), 22, 5)
        # The glowing orb; it brightens/grows briefly while casting.
        glow = 12 + int(t * 8)                 # Orb radius pulses with the cast.
        pygame.draw.circle(screen, (120, 200, 255), (int(top[0]), int(top[1])), glow)
        pygame.draw.circle(screen, (230, 245, 255), (int(top[0]), int(top[1])), glow // 2)
