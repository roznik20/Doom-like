"""hud.py — the heads-up display and all full-screen menu overlays.

This module owns everything drawn in 2D *on top of* the 3D view: the health
and mana bars, score/kill counters, the equipped-weapon name, a crosshair, a
transient message banner, the red "you got hit" flash, and the title / pause /
game-over / victory screens.
"""

import pygame             # Fonts and 2D drawing.
from . import config      # Colors and vital caps.


# Reusable color constants for the UI (R, G, B).
WHITE = (240, 240, 240)       # General text.
GOLD = (255, 209, 102)        # Labels and accents.
PINK = (255, 59, 107)         # Logo / highlights.
CYAN = (108, 204, 255)        # Magic / victory accents.
RED = (255, 42, 42)           # Health + danger.
DARK = (10, 4, 8)             # Panel backgrounds.


class HUD:
    """Draws the HUD and menu screens. Holds the fonts it needs."""

    def __init__(self):
        # Make sure the font subsystem is ready before we build fonts.
        pygame.font.init()
        # A big font for logos/titles.
        self.font_huge = pygame.font.SysFont("Courier New", 72, bold=True)
        # A medium font for headings/subtitles.
        self.font_big = pygame.font.SysFont("Courier New", 32, bold=True)
        # A normal font for HUD numbers and labels.
        self.font_mid = pygame.font.SysFont("Courier New", 22, bold=True)
        # A small font for body text / control hints.
        self.font_small = pygame.font.SysFont("Courier New", 16)

    # ----- low-level text helpers -------------------------------------------

    def _text(self, screen, font, text, color, cx, y, center=True, glow=None):
        """Render `text` and blit it; optionally centered and with a glow."""
        # Render the main text to a Surface.
        surf = font.render(text, True, color)
        # Compute the blit rectangle (centered horizontally on cx, or left at cx).
        rect = surf.get_rect()
        if center:
            rect.center = (cx, y)              # Center the text on (cx, y).
        else:
            rect.topleft = (cx, y)             # Anchor at the top-left.
        # If a glow color was given, draw a few offset copies behind the text.
        if glow:
            glow_surf = font.render(text, True, glow)
            for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                gr = glow_surf.get_rect(center=rect.center) if center else glow_surf.get_rect(topleft=rect.topleft)
                gr.move_ip(ox, oy)             # Offset the glow copy.
                screen.blit(glow_surf, gr)     # Blit the soft glow behind.
        # Blit the crisp main text on top.
        screen.blit(surf, rect)
        # Return the rect so callers can stack text below it if they want.
        return rect

    def _bar(self, screen, x, y, w, h, frac, color):
        """Draw a labeled value bar: a dark track with a colored fill."""
        # The empty track background.
        pygame.draw.rect(screen, (40, 0, 0), (x, y, w, h), border_radius=h // 2)
        # The colored fill, width scaled by the 0..1 fraction.
        fill_w = int(w * max(0.0, min(1.0, frac)))
        if fill_w > 0:
            pygame.draw.rect(screen, color, (x, y, fill_w, h), border_radius=h // 2)
        # A thin border around the whole bar.
        pygame.draw.rect(screen, (130, 20, 40), (x, y, w, h), 2, border_radius=h // 2)

    # ----- the in-game HUD ---------------------------------------------------

    def draw_hud(self, screen, state):
        """Draw the live HUD using values pulled from the game `state`."""
        w, h = screen.get_size()               # Window dimensions.
        player = state["player"]               # The player object.

        # --- Damage flash: a translucent red overlay right after being hit ---
        if state["damage_flash"] > 0:
            # Alpha scales with the remaining flash time for a quick fade.
            alpha = int(120 * min(1.0, state["damage_flash"] / 0.3))
            flash = pygame.Surface((w, h), pygame.SRCALPHA)   # Transparent layer.
            flash.fill((255, 0, 0, alpha))                    # Fill translucent red.
            screen.blit(flash, (0, 0))                        # Overlay it.

        # --- Crosshair in the screen center ---
        cx, cy = w // 2, h // 2                 # Center coordinates.
        pygame.draw.line(screen, (255, 255, 255), (cx - 10, cy), (cx + 10, cy), 2)  # Horizontal.
        pygame.draw.line(screen, (255, 255, 255), (cx, cy - 10), (cx, cy + 10), 2)  # Vertical.

        # --- Bottom HUD strip background ---
        strip_h = 64                            # Height of the bottom bar.
        bar_bg = pygame.Surface((w, strip_h), pygame.SRCALPHA)   # Transparent strip.
        bar_bg.fill((0, 0, 0, 180))             # Semi-opaque black.
        screen.blit(bar_bg, (0, h - strip_h))   # Place it at the bottom.

        # --- Health label + bar + number ---
        base_y = h - strip_h + 14               # Top y for the first bar.
        self._text(screen, self.font_mid, "HP", GOLD, 20, base_y + 2, center=False)
        self._bar(screen, 56, base_y, 160, 16, player.health / config.MAX_HEALTH, RED)
        self._text(screen, self.font_mid, str(int(player.health)), WHITE, 224, base_y + 2, center=False)

        # --- Mana label + bar + number (second row) ---
        my = base_y + 24                        # Top y for the mana bar.
        self._text(screen, self.font_mid, "MP", GOLD, 20, my + 2, center=False)
        self._bar(screen, 56, my, 160, 16, player.mana / config.MAX_MANA, CYAN)
        self._text(screen, self.font_mid, str(int(player.mana)), WHITE, 224, my + 2, center=False)

        # --- Equipped weapon name (center bottom) ---
        self._text(screen, self.font_big, state["weapon_name"], WHITE,
                  w // 2, h - strip_h // 2, glow=CYAN)

        # --- Score + kills (right side) ---
        self._text(screen, self.font_mid, "SCORE " + str(state["score"]), GOLD,
                  w - 110, base_y + 4)
        self._text(screen, self.font_mid,
                  "KILLS " + str(state["kills"]) + "/" + str(state["total_enemies"]),
                  GOLD, w - 110, my + 4)

        # --- Level name (top-left) ---
        self._text(screen, self.font_small, state["level_name"], (200, 180, 180),
                  16, 12, center=False)

        # --- Transient message banner (top-center) ---
        if state["message"] and state["message_timer"] > 0:
            self._text(screen, self.font_big, state["message"], WHITE,
                      w // 2, 40, glow=PINK)

    # ----- full-screen overlays ---------------------------------------------

    def _dim(self, screen, alpha=200):
        """Darken the whole screen behind a menu for readability."""
        w, h = screen.get_size()                # Window size.
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)   # Transparent layer.
        overlay.fill((12, 4, 8, alpha))         # Dark crimson tint.
        screen.blit(overlay, (0, 0))            # Apply it.

    def draw_title(self, screen):
        """Render the title / start screen."""
        self._dim(screen, 230)                  # Strong dim behind the title.
        w, h = screen.get_size()                # Window size.
        # The two-tone logo (ISEKAI in pink, DOOM in gold) on one baseline.
        self._text(screen, self.font_huge, "ISEKAI DOOM", PINK, w // 2, h // 5, glow=(120, 0, 40))
        # Subtitle.
        self._text(screen, self.font_big, "Reborn in the Demon World", GOLD, w // 2, h // 5 + 60)
        # A few lines of lore, drawn one under another.
        lore = [
            "You died in a traffic accident. A goddess gave you a second life...",
            "...then dropped you in a labyrinth of demon-girls who only speak",
            "in anime catchphrases. Find the exit. Survive. Stay sane.",
        ]
        for i, line in enumerate(lore):         # Draw each lore line.
            self._text(screen, self.font_small, line, (210, 190, 190), w // 2, h // 2 - 10 + i * 22)
        # The call-to-action prompt.
        self._text(screen, self.font_big, "PRESS  ENTER  TO  BEGIN", WHITE, w // 2, h * 0.66, glow=PINK)
        # Compact controls reminder.
        controls = [
            "WASD move    Arrows / Mouse turn    Shift sprint",
            "Left-Click / Space attack    1 Sword   2 Bolt    M mute   Esc pause",
        ]
        for i, line in enumerate(controls):     # Draw each controls line.
            self._text(screen, self.font_small, line, (180, 180, 200), w // 2, h * 0.8 + i * 22)

    def draw_pause(self, screen):
        """Render the pause overlay."""
        self._dim(screen)                       # Dim the frozen game behind it.
        w, h = screen.get_size()                # Window size.
        self._text(screen, self.font_huge, "PAUSED", GOLD, w // 2, h // 3)   # Big PAUSED text.
        self._text(screen, self.font_big, "ENTER / Esc — Resume", WHITE, w // 2, h // 2)
        self._text(screen, self.font_big, "R — Restart Level", WHITE, w // 2, h // 2 + 44)

    def draw_gameover(self, screen, stats):
        """Render the death screen with final stats."""
        self._dim(screen)                       # Dim the background.
        w, h = screen.get_size()                # Window size.
        self._text(screen, self.font_huge, "YOU DIED", RED, w // 2, h // 3, glow=(120, 0, 0))
        self._text(screen, self.font_big, "The demon-girls got you...", PINK, w // 2, h // 3 + 60)
        self._text(screen, self.font_mid, stats, WHITE, w // 2, h // 2 + 10)   # Stats line.
        self._text(screen, self.font_big, "ENTER — Try Again", WHITE, w // 2, h * 0.7, glow=PINK)

    def draw_victory(self, screen, stats):
        """Render the victory screen with final stats."""
        self._dim(screen)                       # Dim the background.
        w, h = screen.get_size()                # Window size.
        self._text(screen, self.font_huge, "YOU ESCAPED!", CYAN, w // 2, h // 3, glow=(40, 80, 160))
        self._text(screen, self.font_big, "The goddess smiles upon you.", GOLD, w // 2, h // 3 + 60)
        self._text(screen, self.font_mid, stats, WHITE, w // 2, h // 2 + 10)   # Stats line.
        self._text(screen, self.font_big, "ENTER — Play Again", WHITE, w // 2, h * 0.7, glow=CYAN)
