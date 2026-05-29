"""sprites.py — every billboard sprite, drawn procedurally (no art files).

This module grew a lot for the "maximized" build. It now draws FIVE kinds of
anime demon-girl, a giant boss, several projectile orbs, all the pickups
(health/mana/armor/ammo), and the temporary powerup icons. Each enemy "sprite
set" is a dict of animation frames the raycaster billboards into the world:

    {"walk": [frameA, frameB], "attack": frame, "dead": frame}

Drawing in code keeps the repo self-contained and lets us cheaply generate
color variations of each enemy.
"""

import math      # Wavy tails, wings, and a little trig.
import pygame     # All drawing happens onto pygame Surfaces.

# Hair/dress/horn/skin/eye palettes so demon-girls of a type aren't identical.
PALETTES = [
    {"hair": (255, 80, 140), "dress": (60, 20, 60),  "horn": (40, 0, 30),  "skin": (255, 224, 200), "eye": (160, 0, 220)},
    {"hair": (120, 200, 255), "dress": (20, 30, 70),  "horn": (10, 20, 60), "skin": (255, 224, 200), "eye": (0, 140, 230)},
    {"hair": (210, 180, 255), "dress": (50, 10, 70),  "horn": (30, 0, 50),  "skin": (255, 228, 206), "eye": (210, 40, 230)},
    {"hair": (40, 40, 50),    "dress": (90, 0, 20),   "horn": (20, 0, 0),   "skin": (255, 220, 195), "eye": (230, 20, 50)},
    {"hair": (255, 220, 120), "dress": (70, 50, 10),  "horn": (50, 30, 0),  "skin": (255, 226, 202), "eye": (230, 170, 0)},
    {"hair": (140, 255, 180), "dress": (10, 60, 40),  "horn": (0, 40, 20),  "skin": (255, 224, 200), "eye": (0, 200, 120)},
]


def _blank(w, h):
    """Create a fully transparent Surface of the given size to draw on."""
    return pygame.Surface((w, h), pygame.SRCALPHA)   # Per-pixel alpha keeps corners clear.


# ---------------------------------------------------------------------------
# Shared face/feature helpers (used by several enemy types)
# ---------------------------------------------------------------------------

def _face(surf, cx, cy, r, pal, pose, fang=True):
    """Draw a chibi anime face centered at (cx, cy) with radius r."""
    pygame.draw.circle(surf, pal["skin"], (cx, cy), r)                       # Head.
    # Big eyes (whites + iris + sparkle highlight).
    ew = max(6, r // 2)                                                      # Eye width.
    pygame.draw.ellipse(surf, (255, 255, 255), (cx - r // 2 - ew // 2, cy - 2, ew, ew + 4))
    pygame.draw.ellipse(surf, (255, 255, 255), (cx + r // 2 - ew // 2, cy - 2, ew, ew + 4))
    pygame.draw.circle(surf, pal["eye"], (cx - r // 2, cy + 4), max(2, r // 6))   # Left iris.
    pygame.draw.circle(surf, pal["eye"], (cx + r // 2, cy + 4), max(2, r // 6))   # Right iris.
    pygame.draw.circle(surf, (255, 255, 255), (cx - r // 2 - 1, cy + 2), 1)       # Sparkle.
    pygame.draw.circle(surf, (255, 255, 255), (cx + r // 2 - 1, cy + 2), 1)       # Sparkle.
    # Mouth changes with the pose.
    if pose == "attack":
        pygame.draw.ellipse(surf, (120, 0, 30), (cx - 6, cy + r // 2, 12, 8))     # Open mouth.
        if fang:
            pygame.draw.polygon(surf, (255, 255, 255), [(cx - 5, cy + r // 2 + 1), (cx - 2, cy + r // 2 + 1), (cx - 3, cy + r // 2 + 5)])
            pygame.draw.polygon(surf, (255, 255, 255), [(cx + 2, cy + r // 2 + 1), (cx + 5, cy + r // 2 + 1), (cx + 3, cy + r // 2 + 5)])
    else:
        pygame.draw.arc(surf, (150, 0, 40), (cx - 5, cy + r // 2 - 2, 10, 8), math.pi, 2 * math.pi, 2)  # Smile.
    # Blush marks.
    pygame.draw.circle(surf, (255, 150, 170), (cx - r + 2, cy + r // 3), 3)
    pygame.draw.circle(surf, (255, 150, 170), (cx + r - 2, cy + r // 3), 3)


def _horns(surf, cx, cy, size, color):
    """Draw a pair of demon horns above (cx, cy)."""
    pygame.draw.polygon(surf, color, [(cx - size, cy), (cx - size * 1.4, cy - size * 1.6), (cx - size * 0.4, cy - size * 0.3)])
    pygame.draw.polygon(surf, color, [(cx + size, cy), (cx + size * 1.4, cy - size * 1.6), (cx + size * 0.4, cy - size * 0.3)])


def _dead_frame(w, h, pal):
    """A generic 'fainted' frame: a puff with a KO'd head and dizzy stars."""
    surf = _blank(w, h)
    cx = w // 2
    pygame.draw.ellipse(surf, (220, 220, 240, 170), (w * 0.1, h - 30, w * 0.8, 24))   # Floor puff.
    pygame.draw.circle(surf, pal["skin"], (cx, h - 24), 16)                            # Head down.
    for sx in (-8, 0):                                                                  # Two X eyes.
        pygame.draw.line(surf, (60, 0, 0), (cx + sx, h - 28), (cx + sx + 8, h - 20), 2)
        pygame.draw.line(surf, (60, 0, 0), (cx + sx + 8, h - 28), (cx + sx, h - 20), 2)
    pygame.draw.circle(surf, (255, 230, 120), (cx + 16, h - 40), 3)                    # Dizzy star.
    return surf


# ---------------------------------------------------------------------------
# Enemy type 1 — Imp-chan (basic fast-ish melee chibi)
# ---------------------------------------------------------------------------

def _draw_imp(pal, pose):
    surf = _blank(96, 128); cx = 48                       # Canvas + center.
    if pose == "dead":
        return _dead_frame(96, 128, pal)                  # Fainted pose.
    spread = 8 if pose == "step" else 4                   # Walk-cycle leg splay.
    pygame.draw.rect(surf, pal["skin"], (cx - spread - 5, 96, 8, 26), border_radius=4)  # Left leg.
    pygame.draw.rect(surf, pal["skin"], (cx + spread - 3, 96, 8, 26), border_radius=4)  # Right leg.
    # Wiggly devil tail with a heart tip.
    pts = [(cx + 26 + math.sin(i / 9 * 3) * 8, 92 + i / 9 * 28) for i in range(10)]
    pygame.draw.lines(surf, pal["horn"], False, pts, 3)
    hx, hy = pts[-1]
    pygame.draw.circle(surf, (255, 60, 120), (int(hx - 3), int(hy)), 4)
    pygame.draw.circle(surf, (255, 60, 120), (int(hx + 3), int(hy)), 4)
    # Dress.
    pygame.draw.polygon(surf, pal["dress"], [(cx - 8, 70), (cx + 8, 70), (cx + 22, 102), (cx - 22, 102)])
    pygame.draw.rect(surf, pal["dress"], (cx - 9, 58, 18, 16), border_radius=3)
    # Arms.
    if pose == "attack":
        pygame.draw.line(surf, pal["skin"], (cx - 8, 62), (cx - 24, 44), 6)
        pygame.draw.line(surf, pal["skin"], (cx + 8, 62), (cx + 24, 44), 6)
        pygame.draw.polygon(surf, (200, 0, 0), [(cx - 27, 40), (cx - 24, 33), (cx - 21, 40)])  # Claw.
        pygame.draw.polygon(surf, (200, 0, 0), [(cx + 21, 40), (cx + 24, 33), (cx + 27, 40)])  # Claw.
    else:
        pygame.draw.line(surf, pal["skin"], (cx - 8, 62), (cx - 16, 82), 6)
        pygame.draw.line(surf, pal["skin"], (cx + 8, 62), (cx + 16, 82), 6)
    # Hair puffs + face + bangs + horns.
    pygame.draw.circle(surf, pal["hair"], (cx - 22, 40), 12)
    pygame.draw.circle(surf, pal["hair"], (cx + 22, 40), 12)
    _face(surf, cx, 36, 22, pal, pose)
    pygame.draw.polygon(surf, pal["hair"], [(cx - 22, 30), (cx + 22, 30), (cx + 18, 18), (cx, 12), (cx - 18, 18)])  # Bangs.
    _horns(surf, cx, 18, 8, pal["horn"])
    return surf


# ---------------------------------------------------------------------------
# Enemy type 2 — Caster-chan (floating ranged mage who throws hearts)
# ---------------------------------------------------------------------------

def _draw_caster(pal, pose):
    surf = _blank(96, 140); cx = 48
    if pose == "dead":
        return _dead_frame(96, 140, pal)
    # A floating long robe (no legs) — she hovers.
    pygame.draw.polygon(surf, pal["dress"], [(cx - 10, 60), (cx + 10, 60), (cx + 28, 120), (cx - 28, 120)])
    # Hovering glow beneath the robe.
    pygame.draw.ellipse(surf, (pal["eye"][0], pal["eye"][1], pal["eye"][2], 120), (cx - 26, 116, 52, 14))
    # A magic staff held to the side; orb at the top brightens when casting.
    sx_top = cx + 30
    pygame.draw.line(surf, (110, 80, 50), (cx + 14, 64), (sx_top, 24), 4)               # Staff shaft.
    orb_r = 9 if pose == "attack" else 6                                                # Orb pulses.
    pygame.draw.circle(surf, (255, 80, 140), (sx_top, 22), orb_r)                       # Glowing heart-orb.
    pygame.draw.circle(surf, (255, 200, 220), (sx_top, 22), orb_r // 2)
    # Arms toward the staff (or raised when casting).
    pygame.draw.line(surf, pal["skin"], (cx + 6, 62), (cx + 14, 64), 5)
    pygame.draw.line(surf, pal["skin"], (cx - 6, 62), (cx - 16, 72 if pose != "attack" else 56), 5)
    # Long flowing hair + face + horns + a witch-like point.
    pygame.draw.ellipse(surf, pal["hair"], (cx - 26, 30, 14, 50))                       # Left hair fall.
    pygame.draw.ellipse(surf, pal["hair"], (cx + 12, 30, 14, 50))                       # Right hair fall.
    _face(surf, cx, 40, 20, pal, pose)
    pygame.draw.polygon(surf, pal["hair"], [(cx - 20, 34), (cx + 20, 34), (cx + 16, 22), (cx, 16), (cx - 16, 22)])
    _horns(surf, cx, 22, 7, pal["horn"])
    return surf


# ---------------------------------------------------------------------------
# Enemy type 3 — Brute-chan (big, tanky, slow, huge horns + club)
# ---------------------------------------------------------------------------

def _draw_brute(pal, pose):
    surf = _blank(128, 168); cx = 64
    if pose == "dead":
        return _dead_frame(128, 168, pal)
    spread = 12 if pose == "step" else 6
    pygame.draw.rect(surf, pal["skin"], (cx - spread - 10, 126, 16, 38), border_radius=6)  # Legs.
    pygame.draw.rect(surf, pal["skin"], (cx + spread - 6, 126, 16, 38), border_radius=6)
    # Bulky armored dress/torso.
    pygame.draw.polygon(surf, pal["dress"], [(cx - 24, 80), (cx + 24, 80), (cx + 40, 132), (cx - 40, 132)])
    pygame.draw.rect(surf, pal["dress"], (cx - 22, 64, 44, 24), border_radius=5)
    # A massive club raised when attacking.
    if pose == "attack":
        pygame.draw.line(surf, (110, 70, 40), (cx + 18, 70), (cx + 50, 24), 9)             # Handle.
        pygame.draw.circle(surf, (90, 90, 100), (cx + 54, 18), 18)                         # Club head.
        pygame.draw.circle(surf, (60, 60, 70), (cx + 54, 18), 18, 3)
    else:
        pygame.draw.line(surf, (110, 70, 40), (cx + 22, 72), (cx + 40, 120), 9)            # Resting club.
        pygame.draw.circle(surf, (90, 90, 100), (cx + 42, 126), 16)
    pygame.draw.line(surf, pal["skin"], (cx - 22, 72), (cx - 34, 110), 9)                  # Free arm.
    # Big head, big horns, fierce face.
    pygame.draw.circle(surf, pal["hair"], (cx - 26, 46), 14)
    pygame.draw.circle(surf, pal["hair"], (cx + 26, 46), 14)
    _face(surf, cx, 42, 28, pal, pose)
    _horns(surf, cx, 18, 16, pal["horn"])
    return surf


# ---------------------------------------------------------------------------
# Enemy type 4 — Dasher-chan (small, winged, very fast swarmer)
# ---------------------------------------------------------------------------

def _draw_dasher(pal, pose):
    surf = _blank(84, 112); cx = 42
    if pose == "dead":
        return _dead_frame(84, 112, pal)
    # Bat wings (flap between frames).
    flap = 14 if pose == "step" else 4
    pygame.draw.polygon(surf, pal["horn"], [(cx - 6, 54), (cx - 34, 40 - flap), (cx - 30, 64), (cx - 12, 62)])  # Left wing.
    pygame.draw.polygon(surf, pal["horn"], [(cx + 6, 54), (cx + 34, 40 - flap), (cx + 30, 64), (cx + 12, 62)])  # Right wing.
    # Small slim body.
    pygame.draw.polygon(surf, pal["dress"], [(cx - 7, 56), (cx + 7, 56), (cx + 16, 92), (cx - 16, 92)])
    # Tiny legs.
    pygame.draw.line(surf, pal["skin"], (cx - 6, 90), (cx - 8, 106), 5)
    pygame.draw.line(surf, pal["skin"], (cx + 6, 90), (cx + 8, 106), 5)
    # Claws forward when attacking.
    if pose == "attack":
        pygame.draw.line(surf, pal["skin"], (cx - 6, 58), (cx - 18, 46), 4)
        pygame.draw.line(surf, pal["skin"], (cx + 6, 58), (cx + 18, 46), 4)
    # Head + small horns.
    pygame.draw.circle(surf, pal["hair"], (cx - 16, 36), 9)
    pygame.draw.circle(surf, pal["hair"], (cx + 16, 36), 9)
    _face(surf, cx, 34, 17, pal, pose)
    _horns(surf, cx, 18, 6, pal["horn"])
    return surf


# ---------------------------------------------------------------------------
# Enemy type 5 — Bomber-chan (round kamikaze who rushes in and explodes)
# ---------------------------------------------------------------------------

def _draw_bomber(pal, pose):
    surf = _blank(88, 112); cx = 44
    if pose == "dead":
        return _dead_frame(88, 112, pal)
    # A round, bomb-like body.
    pygame.draw.circle(surf, pal["dress"], (cx, 70), 28)
    # The glowing volatile core (brighter/larger when about to detonate).
    core = 16 if pose == "attack" else 10
    glow = (255, 120, 40) if pose == "attack" else (255, 80, 80)
    pygame.draw.circle(surf, glow, (cx, 70), core)
    pygame.draw.circle(surf, (255, 240, 180), (cx, 70), core // 2)
    # A lit fuse on top with a spark.
    pygame.draw.line(surf, (60, 40, 20), (cx, 44), (cx + 8, 30), 3)
    pygame.draw.circle(surf, (255, 220, 80), (cx + 8, 28), 4)
    # Tiny panicked arms + legs.
    pygame.draw.line(surf, pal["skin"], (cx - 24, 66), (cx - 34, 54 if pose == "attack" else 74), 5)
    pygame.draw.line(surf, pal["skin"], (cx + 24, 66), (cx + 34, 54 if pose == "attack" else 74), 5)
    pygame.draw.line(surf, pal["skin"], (cx - 10, 96), (cx - 12, 110), 5)
    pygame.draw.line(surf, pal["skin"], (cx + 10, 96), (cx + 12, 110), 5)
    # Worried little face + tiny horns.
    _face(surf, cx, 40, 16, pal, "idle", fang=False)
    _horns(surf, cx, 26, 6, pal["horn"])
    return surf


# ---------------------------------------------------------------------------
# Enemy type 6 — Healer-chan (priestess who heals nearby demon-girls)
# ---------------------------------------------------------------------------

def _draw_healer(pal, pose):
    surf = _blank(96, 140); cx = 48
    if pose == "dead":
        return _dead_frame(96, 140, pal)
    # Long priestess robe (white-trimmed dress).
    pygame.draw.polygon(surf, (235, 235, 245), [(cx - 12, 60), (cx + 12, 60), (cx + 26, 122), (cx - 26, 122)])
    pygame.draw.polygon(surf, pal["dress"], [(cx - 8, 64), (cx + 8, 64), (cx + 16, 118), (cx - 16, 118)])
    # A healing staff with a green cross; it glows when casting.
    sx_top = cx + 28
    pygame.draw.line(surf, (200, 200, 210), (cx + 12, 66), (sx_top, 26), 4)
    cross = 12 if pose == "attack" else 8
    col = (80, 255, 140) if pose == "attack" else (120, 230, 160)
    pygame.draw.line(surf, col, (sx_top - cross, 24), (sx_top + cross, 24), 4)   # Cross bar.
    pygame.draw.line(surf, col, (sx_top, 24 - cross), (sx_top, 24 + cross), 4)   # Cross stem.
    pygame.draw.circle(surf, (200, 255, 220), (sx_top, 24), 4)
    # Arms.
    pygame.draw.line(surf, pal["skin"], (cx + 6, 64), (cx + 12, 66), 5)
    pygame.draw.line(surf, pal["skin"], (cx - 6, 64), (cx - 16, 78), 5)
    # Hair + face + a glowing halo above the head.
    pygame.draw.ellipse(surf, pal["hair"], (cx - 24, 30, 14, 46))
    pygame.draw.ellipse(surf, pal["hair"], (cx + 10, 30, 14, 46))
    _face(surf, cx, 40, 20, pal, "idle")
    pygame.draw.ellipse(surf, (255, 255, 180), (cx - 16, 10, 32, 8), 2)          # Halo.
    _horns(surf, cx, 22, 6, pal["horn"])
    return surf


# ---------------------------------------------------------------------------
# Boss — the Demon Queen (huge, winged, crowned, throws fireballs)
# ---------------------------------------------------------------------------

def _draw_boss(pose):
    surf = _blank(240, 280); cx = 120
    pal = {"hair": (40, 0, 60), "dress": (30, 0, 40), "horn": (10, 0, 0), "skin": (245, 210, 220), "eye": (255, 40, 60)}
    if pose == "dead":
        # A dramatic large faint.
        pygame.draw.ellipse(surf, (180, 60, 120, 160), (30, 240, 180, 30))
        pygame.draw.circle(surf, pal["skin"], (cx, 250), 30)
        for sx in (-16, 4):
            pygame.draw.line(surf, (80, 0, 0), (cx + sx, 244), (cx + sx + 12, 256), 3)
            pygame.draw.line(surf, (80, 0, 0), (cx + sx + 12, 244), (cx + sx, 256), 3)
        return surf
    # Vast bat wings spread behind her (flap a touch between frames).
    flap = 26 if pose == "step" else 8
    pygame.draw.polygon(surf, (50, 0, 50), [(cx - 20, 110), (cx - 110, 50 - flap), (cx - 100, 150), (cx - 60, 150), (cx - 30, 130)])
    pygame.draw.polygon(surf, (50, 0, 50), [(cx + 20, 110), (cx + 110, 50 - flap), (cx + 100, 150), (cx + 60, 150), (cx + 30, 130)])
    # Flowing gown.
    pygame.draw.polygon(surf, pal["dress"], [(cx - 30, 130), (cx + 30, 130), (cx + 70, 270), (cx - 70, 270)])
    pygame.draw.rect(surf, pal["dress"], (cx - 28, 96, 56, 40), border_radius=8)
    # Scepter with a flaming orb (brighter while attacking).
    pygame.draw.line(surf, (180, 150, 40), (cx + 30, 110), (cx + 78, 30), 7)
    orb = 22 if pose == "attack" else 14
    pygame.draw.circle(surf, (255, 120, 40), (cx + 82, 24), orb)
    pygame.draw.circle(surf, (255, 230, 150), (cx + 82, 24), orb // 2)
    # Arms.
    pygame.draw.line(surf, pal["skin"], (cx + 20, 104), (cx + 30, 110), 8)
    pygame.draw.line(surf, pal["skin"], (cx - 20, 104), (cx - 40, 130 if pose != "attack" else 80), 8)
    # Long dark hair.
    pygame.draw.ellipse(surf, pal["hair"], (cx - 50, 50, 26, 90))
    pygame.draw.ellipse(surf, pal["hair"], (cx + 24, 50, 26, 90))
    # Big regal face.
    _face(surf, cx, 60, 40, pal, pose)
    # Glowing eyes overlay (boss menace).
    pygame.draw.circle(surf, (255, 60, 60), (cx - 20, 64), 5)
    pygame.draw.circle(surf, (255, 60, 60), (cx + 20, 64), 5)
    # Huge horns + a golden crown.
    _horns(surf, cx, 28, 26, pal["horn"])
    pygame.draw.polygon(surf, (230, 190, 50), [(cx - 30, 26), (cx - 18, 6), (cx - 6, 22), (cx + 6, 4), (cx + 18, 22), (cx + 30, 6), (cx + 30, 30), (cx - 30, 30)])
    return surf


# ---------------------------------------------------------------------------
# Sprite-set assembly
# ---------------------------------------------------------------------------

def _make_set(drawer, pal):
    """Build the standard {walk, attack, dead} frame dict for one drawer+palette."""
    return {
        "walk": [drawer(pal, "idle"), drawer(pal, "step")],   # Two-frame walk cycle.
        "attack": drawer(pal, "attack"),                      # Attack pose.
        "dead": drawer(pal, "dead"),                          # Fainted pose.
    }


def build_all_enemy_sprites():
    """Return {enemy_type: [sprite_set_per_palette, ...]} for every enemy type.

    The boss has a single set (no palette variants).
    """
    out = {}
    out["imp"] = [_make_set(_draw_imp, p) for p in PALETTES]        # Basic melee.
    out["caster"] = [_make_set(_draw_caster, p) for p in PALETTES]  # Ranged mage.
    out["brute"] = [_make_set(_draw_brute, p) for p in PALETTES]    # Tank.
    out["dasher"] = [_make_set(_draw_dasher, p) for p in PALETTES]  # Fast swarmer.
    out["bomber"] = [_make_set(_draw_bomber, p) for p in PALETTES]  # Kamikaze.
    out["healer"] = [_make_set(_draw_healer, p) for p in PALETTES]  # Support medic.
    # Boss: build its frames with the fixed boss palette.
    out["boss"] = [{
        "walk": [_draw_boss("idle"), _draw_boss("step")],
        "attack": _draw_boss("attack"),
        "dead": _draw_boss("dead"),
    }]
    return out


# ---------------------------------------------------------------------------
# Projectiles (player + enemy)
# ---------------------------------------------------------------------------

def _glow_orb(size, inner, outer):
    """A generic glowing orb sprite from two colors (outer halo, inner core)."""
    surf = _blank(size, size); c = size // 2
    pygame.draw.circle(surf, (outer[0], outer[1], outer[2], 90), (c, c), c)
    pygame.draw.circle(surf, (outer[0], outer[1], outer[2], 160), (c, c), c * 2 // 3)
    pygame.draw.circle(surf, inner, (c, c), c // 3)
    return surf


def build_projectile_sprites():
    """Return all projectile sprites: player bolt + enemy heart/fireball."""
    out = {}
    out["bolt"] = _glow_orb(26, (230, 245, 255), (80, 160, 255))     # Player Spirit Bolt.
    # Enemy heart projectile (caster): a pink heart.
    heart = _blank(28, 28)
    pygame.draw.circle(heart, (255, 80, 140), (9, 10), 7)
    pygame.draw.circle(heart, (255, 80, 140), (19, 10), 7)
    pygame.draw.polygon(heart, (255, 80, 140), [(2, 12), (26, 12), (14, 26)])
    pygame.draw.circle(heart, (255, 180, 210), (9, 8), 2)            # Highlight.
    out["heart"] = heart
    out["fireball"] = _glow_orb(34, (255, 240, 180), (255, 100, 30)) # Boss fireball.
    return out


# ---------------------------------------------------------------------------
# Pickups (health/mana/armor + ammo + powerups)
# ---------------------------------------------------------------------------

def build_pickup_sprites():
    """Return a dict of every collectable item's sprite."""
    out = {}

    # Health potion (red bottle with a cross).
    h = _blank(40, 48)
    pygame.draw.rect(h, (180, 180, 200), (16, 4, 8, 8))
    pygame.draw.ellipse(h, (220, 40, 60), (6, 12, 28, 32))
    pygame.draw.ellipse(h, (255, 120, 140), (12, 16, 8, 10))
    pygame.draw.line(h, (255, 255, 255), (20, 22), (20, 30), 2)
    pygame.draw.line(h, (255, 255, 255), (16, 26), (24, 26), 2)
    out["health"] = h

    # Mana crystal (blue diamond).
    m = _blank(40, 48)
    pygame.draw.polygon(m, (60, 140, 255), [(20, 4), (34, 24), (20, 44), (6, 24)])
    pygame.draw.polygon(m, (160, 210, 255), [(20, 4), (27, 24), (20, 24)])
    pygame.draw.polygon(m, (20, 80, 200), [(20, 24), (20, 44), (6, 24)])
    out["mana"] = m

    # Armor shard (green hex shield).
    a = _blank(40, 48)
    pygame.draw.polygon(a, (40, 200, 120), [(20, 4), (36, 14), (36, 32), (20, 44), (4, 32), (4, 14)])
    pygame.draw.polygon(a, (180, 255, 220), [(20, 4), (28, 14), (20, 24), (12, 14)])
    out["armor"] = a

    # Ammo: shells (red shotgun box).
    s = _blank(40, 40)
    pygame.draw.rect(s, (150, 30, 30), (6, 14, 28, 18), border_radius=3)
    pygame.draw.rect(s, (220, 200, 60), (6, 14, 28, 5))
    for i in range(3):
        pygame.draw.rect(s, (230, 210, 80), (10 + i * 8, 6, 5, 10))
    out["shells"] = s

    # Ammo: rounds (gray bullet box).
    r = _blank(40, 40)
    pygame.draw.rect(r, (90, 90, 100), (6, 14, 28, 18), border_radius=3)
    pygame.draw.rect(r, (200, 200, 60), (8, 8, 4, 10))
    pygame.draw.rect(r, (200, 200, 60), (16, 8, 4, 10))
    pygame.draw.rect(r, (200, 200, 60), (24, 8, 4, 10))
    out["rounds"] = r

    # Ammo: energy (glowing cyan cell).
    e = _blank(40, 40)
    pygame.draw.rect(e, (20, 80, 120), (10, 8, 20, 26), border_radius=4)
    pygame.draw.rect(e, (120, 240, 255), (14, 12, 12, 18), border_radius=3)
    out["energy"] = e

    # Powerups.
    # Quad Damage (purple skull-fist icon).
    q = _blank(44, 48)
    pygame.draw.circle(q, (150, 40, 220), (22, 24), 18)
    pygame.draw.circle(q, (220, 160, 255), (22, 24), 18, 3)
    pygame.draw.polygon(q, (255, 255, 255), [(22, 12), (28, 24), (22, 36), (16, 24)])   # Spark.
    out["quad"] = q

    # Haste (yellow lightning).
    ha = _blank(44, 48)
    pygame.draw.circle(ha, (40, 40, 60), (22, 24), 18)
    pygame.draw.polygon(ha, (255, 230, 0), [(24, 6), (12, 26), (20, 26), (16, 42), (32, 20), (24, 20)])
    out["haste"] = ha

    # Divine Shield (white halo).
    sh = _blank(44, 48)
    pygame.draw.circle(sh, (200, 230, 255), (22, 24), 16, 4)
    pygame.draw.circle(sh, (255, 255, 255), (22, 16), 5)
    out["shield"] = sh

    # Keycards (red / blue / yellow) — small keys for locked doors.
    for kind, col in (("key_red", (230, 50, 60)), ("key_blue", (60, 110, 240)), ("key_yellow", (235, 200, 50))):
        k = _blank(36, 36)
        pygame.draw.circle(k, col, (12, 18), 8, 3)            # Key bow (ring).
        pygame.draw.line(k, col, (18, 18), (30, 18), 4)       # Key shaft.
        pygame.draw.line(k, col, (28, 18), (28, 24), 4)       # A tooth.
        pygame.draw.line(k, col, (24, 18), (24, 23), 3)       # Another tooth.
        out[kind] = k

    return out
