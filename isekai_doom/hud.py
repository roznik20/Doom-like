"""hud.py — the heads-up display and all full-screen menu overlays.

Everything drawn in 2D on top of the 3D view: HP/MP/Armor bars, the weapon
panel with ammo, active-powerup timers, a live minimap, a boss health bar, a
transient message banner, the damage flash, and the title (with difficulty
select) / pause / game-over / victory screens.
"""

import math               # For the minimap player-direction arrow.
import pygame             # Fonts and 2D drawing.
from . import config      # Colors, caps, weapon list, minimap sizing.


# Reusable UI colors.
WHITE = (240, 240, 240)
GOLD = (255, 209, 102)
PINK = (255, 59, 107)
CYAN = (108, 204, 255)
GREEN = (90, 230, 140)
RED = (255, 60, 60)
PURPLE = (180, 110, 255)


class HUD:
    """Draws the HUD and menu screens. Holds the fonts it needs."""

    def __init__(self):
        pygame.font.init()                                   # Ensure fonts are ready.
        self.font_huge = pygame.font.SysFont("Courier New", 76, bold=True)
        self.font_big = pygame.font.SysFont("Courier New", 32, bold=True)
        self.font_mid = pygame.font.SysFont("Courier New", 22, bold=True)
        self.font_small = pygame.font.SysFont("Courier New", 16)
        self.font_tiny = pygame.font.SysFont("Courier New", 13, bold=True)

    # ----- low-level helpers -------------------------------------------------

    def _text(self, screen, font, text, color, x, y, center=True, glow=None):
        """Render text (optionally centered + glowing) and return its rect."""
        surf = font.render(text, True, color)
        rect = surf.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        if glow:
            gs = font.render(text, True, glow)
            for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                gr = gs.get_rect(center=rect.center) if center else gs.get_rect(topleft=rect.topleft)
                gr.move_ip(ox, oy)
                screen.blit(gs, gr)
        screen.blit(surf, rect)
        return rect

    def _bar(self, screen, x, y, w, h, frac, color, label=None, value=None):
        """Draw a labeled value bar with a dark track and a colored fill."""
        if label:
            self._text(screen, self.font_mid, label, GOLD, x - 6, y + h // 2 - 1, center=False)
            x += 34                                          # Indent the bar past the label.
        pygame.draw.rect(screen, (40, 0, 0), (x, y, w, h), border_radius=h // 2)
        fill = int(w * max(0.0, min(1.0, frac)))
        if fill > 0:
            pygame.draw.rect(screen, color, (x, y, fill, h), border_radius=h // 2)
        pygame.draw.rect(screen, (130, 20, 40), (x, y, w, h), 2, border_radius=h // 2)
        if value is not None:
            self._text(screen, self.font_small, str(value), WHITE, x + w + 22, y + h // 2 - 1)

    # ----- the in-game HUD ---------------------------------------------------

    def draw_hud(self, screen, state):
        """Draw the live HUD using values from the game `state` dict."""
        w, h = screen.get_size()
        player = state["player"]

        # Damage flash overlay.
        if state["damage_flash"] > 0:
            alpha = int(120 * min(1.0, state["damage_flash"] / 0.3))
            flash = pygame.Surface((w, h), pygame.SRCALPHA)
            flash.fill((255, 0, 0, alpha))
            screen.blit(flash, (0, 0))

        # Divine Shield tint (cyan vignette) while invulnerable.
        if player.invulnerable():
            tint = pygame.Surface((w, h), pygame.SRCALPHA)
            tint.fill((120, 200, 255, 30))
            screen.blit(tint, (0, 0))

        # Crosshair.
        cx, cy = w // 2, h // 2
        pygame.draw.line(screen, WHITE, (cx - 10, cy), (cx - 3, cy), 2)
        pygame.draw.line(screen, WHITE, (cx + 3, cy), (cx + 10, cy), 2)
        pygame.draw.line(screen, WHITE, (cx, cy - 10), (cx, cy - 3), 2)
        pygame.draw.line(screen, WHITE, (cx, cy + 3), (cx, cy + 10), 2)

        # Bottom HUD strip.
        strip_h = 86
        bar_bg = pygame.Surface((w, strip_h), pygame.SRCALPHA)
        bar_bg.fill((0, 0, 0, 180))
        screen.blit(bar_bg, (0, h - strip_h))

        # Left: HP / MP / Armor bars.
        base_y = h - strip_h + 12
        self._bar(screen, 50, base_y, 150, 14, player.health / config.MAX_HEALTH, RED, "HP", int(player.health))
        self._bar(screen, 50, base_y + 24, 150, 14, player.mana / config.MAX_MANA, CYAN, "MP", int(player.mana))
        self._bar(screen, 50, base_y + 48, 150, 14, player.armor / config.MAX_ARMOR, GREEN, "AR", int(player.armor))

        # Center: weapon panel.
        self._weapon_panel(screen, state, w, h - strip_h)

        # Right: score + kills.
        self._text(screen, self.font_mid, "SCORE " + str(state["score"]), GOLD, w - 150, base_y + 6, center=False)
        self._text(screen, self.font_mid, "KILLS {}/{}".format(state["kills"], state["total_enemies"]),
                  GOLD, w - 150, base_y + 32, center=False)

        # Level name (top-left).
        self._text(screen, self.font_small, state["level_name"], (210, 190, 190), 14, 12, center=False)

        # Active powerup timers.
        self._powerups(screen, player, w)

        # Live minimap (top-right).
        self._minimap(screen, state, w)

        # Boss health bar (top-center) when a boss is present + awake.
        boss = state.get("boss")
        if boss is not None and boss.aggroed and boss.alive:
            self._boss_bar(screen, boss, w)

        # Transient message banner.
        if state["message"] and state["message_timer"] > 0:
            self._text(screen, self.font_big, state["message"], WHITE, w // 2, 64, glow=PINK)

    def _weapon_panel(self, screen, state, w, panel_top):
        """Draw the equipped weapon name + ammo + the weapon slot list."""
        # Big equipped-weapon name.
        self._text(screen, self.font_big, state["weapon_name"], WHITE, w // 2, panel_top + 24, glow=CYAN)
        # Ammo readout for the current weapon.
        cur = state["weapon_current"]
        ammo_kind = config.WEAPONS[cur].get("ammo")
        player = state["player"]
        if ammo_kind == "mana":
            ammo_text = "MANA {}".format(int(player.mana))
        elif ammo_kind is None:
            ammo_text = "MELEE"
        else:
            ammo_text = "{} {}".format(ammo_kind.upper(), player.ammo.get(ammo_kind, 0))
        self._text(screen, self.font_small, ammo_text, GOLD, w // 2, panel_top + 50)
        # The slot list (1..5), highlighting the equipped one.
        slots = " ".join(
            ("[{}]".format(wdef["slot"]) if key == cur else str(wdef["slot"]))
            for key, wdef in sorted(config.WEAPONS.items(), key=lambda kv: kv[1]["slot"])
        )
        self._text(screen, self.font_small, slots, (180, 180, 200), w // 2, panel_top + 70)

    def _powerups(self, screen, player, w):
        """Draw small countdown chips for any active powerups."""
        chips = []
        if player.quad_timer > 0:
            chips.append(("QUAD", PURPLE, player.quad_timer, config.POWERUP_QUAD_DURATION))
        if player.haste_timer > 0:
            chips.append(("HASTE", GOLD, player.haste_timer, config.POWERUP_HASTE_DURATION))
        if player.shield_timer > 0:
            chips.append(("SHIELD", CYAN, player.shield_timer, config.POWERUP_SHIELD_DURATION))
        for i, (name, color, t, tmax) in enumerate(chips):
            x = 14
            y = 40 + i * 26
            pygame.draw.rect(screen, (0, 0, 0, 180), (x, y, 120, 20))
            frac = t / tmax
            pygame.draw.rect(screen, color, (x, y, int(120 * frac), 20))
            self._text(screen, self.font_tiny, "{} {:.0f}s".format(name, t), (10, 10, 10), x + 6, y + 10, center=False)

    def _boss_bar(self, screen, boss, w):
        """Draw the Demon Queen's big health bar across the top."""
        bw = int(w * 0.6)
        x = (w - bw) // 2
        y = 18
        self._text(screen, self.font_mid, "DEMON QUEEN", PINK, w // 2, y - 4, glow=(120, 0, 40))
        pygame.draw.rect(screen, (30, 0, 0), (x, y + 8, bw, 16), border_radius=8)
        frac = max(0.0, boss.hp / boss.max_hp)
        pygame.draw.rect(screen, (220, 30, 60), (x, y + 8, int(bw * frac), 16), border_radius=8)
        pygame.draw.rect(screen, (255, 120, 150), (x, y + 8, bw, 16), 2, border_radius=8)

    def _minimap(self, screen, state, w):
        """Draw a small top-right minimap of the level + entities."""
        level = state["level"]
        ts = config.MINIMAP_TILE
        mw = level["width"] * ts
        mh = level["height"] * ts
        ox = w - mw - config.MINIMAP_MARGIN          # Top-right origin x.
        oy = config.MINIMAP_MARGIN
        # Semi-transparent backing.
        bg = pygame.Surface((mw, mh), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 150))
        screen.blit(bg, (ox, oy))
        # Walls / doors / exit.
        grid = level["grid"]
        for y in range(level["height"]):
            for x in range(level["width"]):
                t = grid[y][x]
                if t == 0:
                    continue
                if t == config.TEX_EXIT:
                    col = GREEN
                elif t == config.TEX_DOOR:
                    col = GOLD
                else:
                    col = (90, 90, 110)
                pygame.draw.rect(screen, col, (ox + x * ts, oy + y * ts, ts - 1, ts - 1))
        # Pickups as tiny gold dots.
        for p in state["pickups"]:
            pygame.draw.rect(screen, (255, 220, 120), (ox + int(p["x"] * ts) - 1, oy + int(p["y"] * ts) - 1, 3, 3))
        # Enemies: red if alive, dim if fainted.
        for e in state["enemies"]:
            col = RED if e.alive else (90, 60, 60)
            r = 3 if e.is_boss else 2
            pygame.draw.circle(screen, col, (ox + int(e.x * ts), oy + int(e.y * ts)), r)
        # Player as a cyan arrow showing facing.
        px = ox + state["player"].x * ts
        py = oy + state["player"].y * ts
        a = state["player"].angle
        tip = (px + math.cos(a) * 6, py + math.sin(a) * 6)
        l = (px + math.cos(a + 2.5) * 5, py + math.sin(a + 2.5) * 5)
        r = (px + math.cos(a - 2.5) * 5, py + math.sin(a - 2.5) * 5)
        pygame.draw.polygon(screen, CYAN, [tip, l, r])

    # ----- overlays ----------------------------------------------------------

    def _dim(self, screen, alpha=200):
        """Darken the whole screen behind a menu."""
        w, h = screen.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((12, 4, 8, alpha))
        screen.blit(overlay, (0, 0))

    def draw_title(self, screen, difficulty_names, sel_index):
        """Title screen with a navigable difficulty selector."""
        self._dim(screen, 235)
        w, h = screen.get_size()
        self._text(screen, self.font_huge, "ISEKAI DOOM", PINK, w // 2, h * 0.16, glow=(120, 0, 40))
        self._text(screen, self.font_big, "Reborn in the Demon World", GOLD, w // 2, h * 0.16 + 60)
        lore = [
            "You died in a traffic accident. A goddess gave you a second life...",
            "...then dropped you in a labyrinth of anime demon-girls. Five holy",
            "weapons. Four levels. One Demon Queen. Escape — or be moe'd to death.",
        ]
        for i, line in enumerate(lore):
            self._text(screen, self.font_small, line, (210, 190, 190), w // 2, h * 0.34 + i * 22)
        # Difficulty selector.
        self._text(screen, self.font_mid, "CHOOSE YOUR FATE  (↑/↓)", CYAN, w // 2, h * 0.5)
        for i, name in enumerate(difficulty_names):
            selected = (i == sel_index)
            color = WHITE if selected else (150, 150, 160)
            label = (">  " + name + "  <") if selected else name
            self._text(screen, self.font_big if selected else self.font_mid, label, color,
                      w // 2, h * 0.56 + i * 34, glow=PINK if selected else None)
        self._text(screen, self.font_big, "PRESS  ENTER  TO  BEGIN", WHITE, w // 2, h * 0.84, glow=PINK)
        controls = "WASD move  Mouse/Arrows look  Click/Space fire  1-5 weapons  Wheel cycle  Shift run  M mute  Esc pause"
        self._text(screen, self.font_tiny, controls, (180, 180, 200), w // 2, h * 0.94)

    def draw_pause(self, screen):
        """Pause overlay."""
        self._dim(screen)
        w, h = screen.get_size()
        self._text(screen, self.font_huge, "PAUSED", GOLD, w // 2, h // 3)
        self._text(screen, self.font_big, "ENTER / Esc — Resume", WHITE, w // 2, h // 2)
        self._text(screen, self.font_big, "R — Restart Level", WHITE, w // 2, h // 2 + 44)
        self._text(screen, self.font_big, "T — Quit to Title", WHITE, w // 2, h // 2 + 88)

    def draw_gameover(self, screen, stats):
        """Death screen."""
        self._dim(screen)
        w, h = screen.get_size()
        self._text(screen, self.font_huge, "YOU DIED", RED, w // 2, h // 3, glow=(120, 0, 0))
        self._text(screen, self.font_big, "The demon-girls got you...", PINK, w // 2, h // 3 + 60)
        self._text(screen, self.font_mid, stats, WHITE, w // 2, h // 2 + 20)
        self._text(screen, self.font_big, "ENTER — Try Again", WHITE, w // 2, h * 0.72, glow=PINK)

    def draw_victory(self, screen, stats):
        """Victory screen."""
        self._dim(screen)
        w, h = screen.get_size()
        self._text(screen, self.font_huge, "YOU ESCAPED!", CYAN, w // 2, h // 3, glow=(40, 80, 160))
        self._text(screen, self.font_big, "The goddess smiles upon you.", GOLD, w // 2, h // 3 + 60)
        self._text(screen, self.font_mid, stats, WHITE, w // 2, h // 2 + 20)
        self._text(screen, self.font_big, "ENTER — Play Again", WHITE, w // 2, h * 0.72, glow=CYAN)
