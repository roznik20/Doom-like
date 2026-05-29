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

        # Combo multiplier (shown under the score when active).
        if state.get("combo_mult", 1) > 1:
            self._text(screen, self.font_mid, "COMBO x{}".format(state["combo_mult"]),
                      (255, 140, 60), w - 150, base_y + 58, center=False)

        # Held keycards (top-left, under the level name).
        self._keys(screen, state.get("keys", set()))

        # Active powerup timers.
        self._powerups(screen, player, w)

        # Damage-direction indicators around the crosshair.
        self._damage_indicators(screen, state.get("damage_dirs", []), player, cx, cy)

        # Live minimap (top-right), if enabled in options.
        if state.get("show_minimap", True):
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

    def _keys(self, screen, keys):
        """Draw little colored key icons for each keycard the player holds."""
        colors = {"red": (230, 50, 60), "blue": (60, 110, 240), "yellow": (235, 200, 50)}
        x = 14
        for i, color in enumerate(["red", "blue", "yellow"]):
            if color in keys:
                kx = x + i * 22
                pygame.draw.circle(screen, colors[color], (kx + 6, 36), 5, 2)   # Bow.
                pygame.draw.line(screen, colors[color], (kx + 10, 36), (kx + 18, 36), 3)  # Shaft.

    def _damage_indicators(self, screen, dirs, player, cx, cy):
        """Draw fading red arcs around the crosshair pointing at recent threats."""
        for ang, t in dirs:
            # Convert the world angle to one relative to where the player looks.
            rel = ang - player.angle
            # Place an arrow on a ring around the crosshair at that relative angle.
            ring = 70
            ax = cx + math.cos(rel) * ring
            ay = cy + math.sin(rel) * ring
            # Build a small triangle pointing outward, fading with the timer.
            alpha = max(0, min(255, int(220 * t)))
            tip = (ax + math.cos(rel) * 12, ay + math.sin(rel) * 12)
            l = (ax + math.cos(rel + 2.4) * 10, ay + math.sin(rel + 2.4) * 10)
            r = (ax + math.cos(rel - 2.4) * 10, ay + math.sin(rel - 2.4) * 10)
            surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(surf, (255, 40, 40, alpha), [tip, l, r])
            screen.blit(surf, (0, 0))

    def draw_lava_tint(self, screen):
        """An orange pulsing vignette while the player stands in lava."""
        w, h = screen.get_size()
        tint = pygame.Surface((w, h), pygame.SRCALPHA)
        tint.fill((255, 90, 20, 40))
        screen.blit(tint, (0, 0))

    def draw_full_map(self, screen, level, player, enemies, pickups):
        """A large centered automap overlay (toggled with Tab)."""
        self._dim(screen, 200)
        w, h = screen.get_size()
        # Choose a tile size that fits the map nicely on screen.
        ts = min((w - 120) // level["width"], (h - 140) // level["height"])
        ts = max(6, ts)
        mw = level["width"] * ts
        mh = level["height"] * ts
        ox = (w - mw) // 2
        oy = (h - mh) // 2 + 10
        self._text(screen, self.font_big, "AUTOMAP", GOLD, w // 2, oy - 26)
        grid = level["grid"]
        for y in range(level["height"]):
            for x in range(level["width"]):
                t = grid[y][x]
                if t == 0:
                    if level.get("hazard_grid") is not None and level["hazard_grid"][y][x]:
                        pygame.draw.rect(screen, (200, 80, 20), (ox + x * ts, oy + y * ts, ts - 1, ts - 1))
                    continue
                if t == config.TEX_EXIT:
                    col = GREEN
                elif t in config.DOOR_TILES:
                    col = GOLD
                else:
                    col = (110, 110, 130)
                pygame.draw.rect(screen, col, (ox + x * ts, oy + y * ts, ts - 1, ts - 1))
        for p in pickups:
            pygame.draw.circle(screen, (255, 220, 120), (ox + int(p["x"] * ts), oy + int(p["y"] * ts)), max(2, ts // 4))
        for e in enemies:
            col = RED if e.alive else (90, 60, 60)
            pygame.draw.circle(screen, col, (ox + int(e.x * ts), oy + int(e.y * ts)), max(2, ts // 3))
        px = ox + player.x * ts; py = oy + player.y * ts
        a = player.angle
        pygame.draw.polygon(screen, CYAN, [
            (px + math.cos(a) * ts, py + math.sin(a) * ts),
            (px + math.cos(a + 2.5) * ts * 0.8, py + math.sin(a + 2.5) * ts * 0.8),
            (px + math.cos(a - 2.5) * ts * 0.8, py + math.sin(a - 2.5) * ts * 0.8),
        ])
        self._text(screen, self.font_small, "Tab — close", (200, 200, 210), w // 2, oy + mh + 20)

    def _scores_block(self, screen, highscores, cx, y):
        """Draw a compact high-score list centered on cx starting at y."""
        self._text(screen, self.font_mid, "— HIGH SCORES —", GOLD, cx, y)
        if not highscores:
            self._text(screen, self.font_small, "(none yet — be the first!)", (190, 190, 200), cx, y + 26)
            return
        for i, s in enumerate(highscores[:5]):
            line = "{}. {:>7}  {}".format(i + 1, s["score"], s.get("difficulty", ""))
            self._text(screen, self.font_small, line, WHITE, cx, y + 26 + i * 20)

    # ----- overlays ----------------------------------------------------------

    def _dim(self, screen, alpha=200):
        """Darken the whole screen behind a menu."""
        w, h = screen.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((12, 4, 8, alpha))
        screen.blit(overlay, (0, 0))

    def draw_title(self, screen, difficulty_names, sel_index, highscores=None):
        """Title screen with a navigable difficulty selector + high scores."""
        self._dim(screen, 235)
        w, h = screen.get_size()
        self._text(screen, self.font_huge, "ISEKAI DOOM", PINK, w // 2, h * 0.13, glow=(120, 0, 40))
        self._text(screen, self.font_big, "Reborn in the Demon World", GOLD, w // 2, h * 0.13 + 54)
        # Difficulty selector (left column).
        self._text(screen, self.font_mid, "CHOOSE YOUR FATE  (↑/↓)", CYAN, w * 0.3, h * 0.34)
        for i, name in enumerate(difficulty_names):
            selected = (i == sel_index)
            color = WHITE if selected else (150, 150, 160)
            label = (">  " + name + "  <") if selected else name
            self._text(screen, self.font_big if selected else self.font_mid, label, color,
                      w * 0.3, h * 0.40 + i * 34, glow=PINK if selected else None)
        # High scores (right column).
        if highscores is not None:
            self._scores_block(screen, highscores, w * 0.72, h * 0.36)
        self._text(screen, self.font_big, "ENTER — Begin      O — Options", WHITE, w // 2, h * 0.82, glow=PINK)
        controls = "WASD move  Mouse/Arrows look  Click/Space fire  1-5 weapons  Wheel cycle  Shift run  Tab map  M mute  Esc pause"
        self._text(screen, self.font_tiny, controls, (180, 180, 200), w // 2, h * 0.93)

    def draw_options(self, screen, options, settings, sel_index):
        """Options menu: adjust each setting with ←/→."""
        self._dim(screen, 230)
        w, h = screen.get_size()
        self._text(screen, self.font_huge, "OPTIONS", GOLD, w // 2, h * 0.18)
        self._text(screen, self.font_small, "↑/↓ select    ←/→ change    Enter/Esc back", CYAN, w // 2, h * 0.28)
        for i, (key, label, step, lo, hi, is_bool) in enumerate(options):
            selected = (i == sel_index)
            val = settings[key]
            if is_bool:
                shown = "ON" if val else "OFF"
            elif key == "mouse_sensitivity":
                shown = "{:.4f}".format(val)
            elif key == "fov_degrees":
                shown = "{}°".format(int(val))
            else:
                shown = "{:.0f}%".format(val * 100)
            color = WHITE if selected else (160, 160, 170)
            prefix = "> " if selected else "  "
            line = "{}{:<20}  < {} >".format(prefix, label, shown)
            self._text(screen, self.font_big if selected else self.font_mid, line, color,
                      w // 2, h * 0.4 + i * 40, glow=PINK if selected else None)

    def draw_intermission(self, screen, info):
        """Between-levels stats summary."""
        self._dim(screen, 220)
        w, h = screen.get_size()
        self._text(screen, self.font_huge, "LEVEL CLEARED", GREEN, w // 2, h * 0.22, glow=(20, 80, 30))
        self._text(screen, self.font_big, info.get("level", ""), GOLD, w // 2, h * 0.22 + 56)
        mins = int(info.get("time", 0) // 60)
        secs = int(info.get("time", 0) % 60)
        lines = [
            "Demon-girls defeated:  {} / {}".format(info.get("kills", 0), info.get("total", 0)),
            "Time:  {:d}:{:02d}".format(mins, secs),
            "Total score:  {}".format(info.get("score", 0)),
        ]
        for i, line in enumerate(lines):
            self._text(screen, self.font_mid, line, WHITE, w // 2, h * 0.46 + i * 34)
        self._text(screen, self.font_big, "ENTER — Continue", WHITE, w // 2, h * 0.74, glow=PINK)

    def draw_pause(self, screen):
        """Pause overlay."""
        self._dim(screen)
        w, h = screen.get_size()
        self._text(screen, self.font_huge, "PAUSED", GOLD, w // 2, h // 4)
        self._text(screen, self.font_big, "ENTER / Esc — Resume", WHITE, w // 2, h * 0.46)
        self._text(screen, self.font_big, "R — Restart Level", WHITE, w // 2, h * 0.46 + 42)
        self._text(screen, self.font_big, "O — Options", WHITE, w // 2, h * 0.46 + 84)
        self._text(screen, self.font_big, "T — Quit to Title", WHITE, w // 2, h * 0.46 + 126)

    def draw_gameover(self, screen, stats, highscores=None):
        """Death screen."""
        self._dim(screen)
        w, h = screen.get_size()
        self._text(screen, self.font_huge, "YOU DIED", RED, w // 2, h // 5, glow=(120, 0, 0))
        self._text(screen, self.font_big, "The demon-girls got you...", PINK, w // 2, h // 5 + 56)
        self._text(screen, self.font_mid, stats, WHITE, w // 2, h * 0.42)
        if highscores is not None:
            self._scores_block(screen, highscores, w // 2, h * 0.5)
        self._text(screen, self.font_big, "ENTER — Try Again     T — Title", WHITE, w // 2, h * 0.86, glow=PINK)

    def draw_victory(self, screen, stats, highscores=None):
        """Victory screen."""
        self._dim(screen)
        w, h = screen.get_size()
        self._text(screen, self.font_huge, "YOU ESCAPED!", CYAN, w // 2, h // 5, glow=(40, 80, 160))
        self._text(screen, self.font_big, "The goddess smiles upon you.", GOLD, w // 2, h // 5 + 56)
        self._text(screen, self.font_mid, stats, WHITE, w // 2, h * 0.42)
        if highscores is not None:
            self._scores_block(screen, highscores, w // 2, h * 0.5)
        self._text(screen, self.font_big, "ENTER — Play Again     T — Title", WHITE, w // 2, h * 0.86, glow=CYAN)
