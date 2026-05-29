"""sprites.py — procedurally drawn sprites (no image assets needed).

Everything you see that is *not* a wall (the demon-girls, pickups, and the
Spirit Bolt projectile) is drawn here at startup using pygame's vector drawing
primitives. Drawing them in code keeps the project a single self-contained
repo with zero binary art files, and lets us generate color variations cheaply.

A "sprite set" for an enemy is a small dictionary of animation frames:
    {"walk": [frameA, frameB], "attack": frame, "dead": frame}
Each frame is a transparent pygame Surface that the raycaster billboards into
the world (always facing the camera).
"""

import math      # For the wavy tail curve and a little trig.
import pygame     # All drawing happens onto pygame Surfaces.

# The pixel canvas size for one demon-girl sprite (width, height).
SPR_W = 96       # Sprite width in pixels.
SPR_H = 128      # Sprite height in pixels (taller than wide — she's standing).

# A handful of hair/dress/horn palettes so the demon-girls aren't all identical.
# Each entry: hair, dress, horn, skin, eye colors as RGB tuples.
PALETTES = [
    {"hair": (255, 80, 140), "dress": (60, 20, 60),  "horn": (40, 0, 30),  "skin": (255, 224, 200), "eye": (120, 0, 200)},   # Pink twintail
    {"hair": (120, 200, 255), "dress": (20, 30, 70),  "horn": (10, 20, 60), "skin": (255, 224, 200), "eye": (0, 120, 220)},   # Blue idol
    {"hair": (210, 180, 255), "dress": (50, 10, 70),  "horn": (30, 0, 50),  "skin": (255, 228, 206), "eye": (200, 40, 220)},  # Lavender
    {"hair": (40, 40, 50),    "dress": (90, 0, 20),   "horn": (20, 0, 0),   "skin": (255, 220, 195), "eye": (220, 20, 40)},   # Crimson goth
    {"hair": (255, 220, 120), "dress": (70, 50, 10),  "horn": (50, 30, 0),  "skin": (255, 226, 202), "eye": (210, 160, 0)},   # Golden
]


def _blank():
    """Create a fully transparent sprite-sized Surface to draw onto."""
    # SRCALPHA gives the surface a per-pixel alpha channel (so corners stay clear).
    return pygame.Surface((SPR_W, SPR_H), pygame.SRCALPHA)


def _draw_girl(pal, pose):
    """Draw one chibi anime demon-girl frame and return the Surface.

    `pal`  is one of the PALETTES dicts (her color scheme).
    `pose` is "idle", "step", "attack", or "dead" — it tweaks limbs/expression.
    """
    surf = _blank()                       # Start with a transparent canvas.

    # Convenient horizontal center of the sprite.
    cx = SPR_W // 2

    # If she is defeated, draw a "fainted" pose and bail out early.
    if pose == "dead":
        # A soft puff/cloud ellipse on the floor where she collapsed.
        pygame.draw.ellipse(surf, (220, 220, 240, 180), (10, SPR_H - 34, SPR_W - 20, 28))
        # A small fainted head with spiral "X" eyes lying on the puff.
        pygame.draw.circle(surf, pal["skin"], (cx, SPR_H - 26), 18)
        # Left swirl eye (two short crossing lines = the classic KO eye).
        pygame.draw.line(surf, (60, 0, 0), (cx - 10, SPR_H - 30), (cx - 2, SPR_H - 22), 2)
        pygame.draw.line(surf, (60, 0, 0), (cx - 2, SPR_H - 30), (cx - 10, SPR_H - 22), 2)
        # Right swirl eye.
        pygame.draw.line(surf, (60, 0, 0), (cx + 2, SPR_H - 30), (cx + 10, SPR_H - 22), 2)
        pygame.draw.line(surf, (60, 0, 0), (cx + 10, SPR_H - 30), (cx + 2, SPR_H - 22), 2)
        # A tiny dizzy "@" of stars above her head.
        pygame.draw.circle(surf, (255, 230, 120), (cx + 18, SPR_H - 44), 3)
        return surf                        # Done — return the fainted frame.

    # --- Legs (drawn first so the dress overlaps their tops) ---
    # When taking a "step" pose, splay the legs slightly for a walk cycle.
    leg_spread = 8 if pose == "step" else 4
    # Left leg as a thin vertical rectangle.
    pygame.draw.rect(surf, pal["skin"], (cx - leg_spread - 5, 96, 8, 26), border_radius=4)
    # Right leg.
    pygame.draw.rect(surf, pal["skin"], (cx + leg_spread - 3, 96, 8, 26), border_radius=4)

    # --- Devil tail with a heart-shaped tip (drawn behind the body) ---
    # Sample points along a sine curve to make a wiggly tail.
    tail_pts = []
    for i in range(10):                    # Ten segments along the tail.
        t = i / 9.0                        # Normalized 0..1 progress along the tail.
        tx = cx + 26 + math.sin(t * 3.0) * 8   # X wiggles as it goes out to the side.
        ty = 92 + t * 28                   # Y descends toward the floor.
        tail_pts.append((tx, ty))          # Collect the point.
    # Draw the tail as a connected line strip.
    if len(tail_pts) > 1:
        pygame.draw.lines(surf, pal["horn"], False, tail_pts, 3)
    # Heart tip: two small circles + a triangle make a little heart.
    htx, hty = tail_pts[-1]                # The tail's end point.
    pygame.draw.circle(surf, (255, 60, 120), (int(htx - 3), int(hty)), 4)   # Left lobe.
    pygame.draw.circle(surf, (255, 60, 120), (int(htx + 3), int(hty)), 4)   # Right lobe.
    pygame.draw.polygon(surf, (255, 60, 120),
                        [(htx - 6, hty + 1), (htx + 6, hty + 1), (htx, hty + 9)])  # Point.

    # --- Dress (a trapezoid skirt + a torso block) ---
    # Skirt as a triangle/trapezoid widening toward the bottom.
    pygame.draw.polygon(surf, pal["dress"],
                        [(cx - 8, 70), (cx + 8, 70), (cx + 22, 102), (cx - 22, 102)])
    # Torso block above the skirt.
    pygame.draw.rect(surf, pal["dress"], (cx - 9, 58, 18, 16), border_radius=3)

    # --- Arms ---
    if pose == "attack":
        # In the attack pose both arms reach upward/forward with little claws.
        pygame.draw.line(surf, pal["skin"], (cx - 8, 62), (cx - 24, 44), 6)   # Left arm up.
        pygame.draw.line(surf, pal["skin"], (cx + 8, 62), (cx + 24, 44), 6)   # Right arm up.
        pygame.draw.circle(surf, pal["skin"], (cx - 24, 44), 5)               # Left hand.
        pygame.draw.circle(surf, pal["skin"], (cx + 24, 44), 5)               # Right hand.
        # Tiny red claws on each hand.
        pygame.draw.polygon(surf, (200, 0, 0), [(cx - 27, 40), (cx - 24, 33), (cx - 21, 40)])
        pygame.draw.polygon(surf, (200, 0, 0), [(cx + 21, 40), (cx + 24, 33), (cx + 27, 40)])
    else:
        # Relaxed arms resting at her sides.
        pygame.draw.line(surf, pal["skin"], (cx - 8, 62), (cx - 16, 82), 6)   # Left arm down.
        pygame.draw.line(surf, pal["skin"], (cx + 8, 62), (cx + 16, 82), 6)   # Right arm down.
        pygame.draw.circle(surf, pal["skin"], (cx - 16, 82), 4)               # Left hand.
        pygame.draw.circle(surf, pal["skin"], (cx + 16, 82), 4)               # Right hand.

    # --- Hair behind the head (twin tails) ---
    pygame.draw.circle(surf, pal["hair"], (cx - 22, 40), 12)   # Left twin-tail puff.
    pygame.draw.circle(surf, pal["hair"], (cx + 22, 40), 12)   # Right twin-tail puff.

    # --- Head ---
    pygame.draw.circle(surf, pal["skin"], (cx, 36), 22)        # The face/head circle.

    # --- Bangs (hair over the forehead) ---
    pygame.draw.polygon(surf, pal["hair"],
                        [(cx - 22, 30), (cx + 22, 30), (cx + 18, 18), (cx, 12), (cx - 18, 18)])

    # --- Horns (this is what makes her a demon-girl) ---
    pygame.draw.polygon(surf, pal["horn"], [(cx - 16, 18), (cx - 22, -2), (cx - 8, 14)])  # Left horn.
    pygame.draw.polygon(surf, pal["horn"], [(cx + 16, 18), (cx + 22, -2), (cx + 8, 14)])  # Right horn.

    # --- Big anime eyes ---
    # White of each eye (large for that anime look).
    pygame.draw.ellipse(surf, (255, 255, 255), (cx - 16, 32, 12, 14))   # Left eye white.
    pygame.draw.ellipse(surf, (255, 255, 255), (cx + 4, 32, 12, 14))    # Right eye white.
    # Colored iris.
    pygame.draw.circle(surf, pal["eye"], (cx - 10, 39), 4)              # Left iris.
    pygame.draw.circle(surf, pal["eye"], (cx + 10, 39), 4)              # Right iris.
    # Tiny white highlight dot in each eye for that sparkly look.
    pygame.draw.circle(surf, (255, 255, 255), (cx - 11, 37), 1)         # Left highlight.
    pygame.draw.circle(surf, (255, 255, 255), (cx + 9, 37), 1)          # Right highlight.

    # --- Mouth ---
    if pose == "attack":
        # Open "fanged" mouth when attacking.
        pygame.draw.ellipse(surf, (120, 0, 30), (cx - 6, 46, 12, 8))    # Open mouth.
        pygame.draw.polygon(surf, (255, 255, 255), [(cx - 5, 47), (cx - 2, 47), (cx - 3, 51)])  # Fang.
        pygame.draw.polygon(surf, (255, 255, 255), [(cx + 2, 47), (cx + 5, 47), (cx + 3, 51)])  # Fang.
    else:
        # A small closed cat-smile.
        pygame.draw.arc(surf, (150, 0, 40), (cx - 5, 44, 10, 8), math.pi, 2 * math.pi, 2)

    # --- Blush marks for extra anime charm ---
    pygame.draw.circle(surf, (255, 150, 170), (cx - 14, 44), 3)        # Left cheek blush.
    pygame.draw.circle(surf, (255, 150, 170), (cx + 14, 44), 3)        # Right cheek blush.

    return surf                            # Return the finished frame.


def build_enemy_sprite_sets():
    """Return a list of animation-frame dicts, one per palette.

    enemy.py picks a random index into this list so different demon-girls look
    different. Each dict has the keys: "walk" (2 frames), "attack", "dead".
    """
    sets = []                              # Will hold one dict per palette.
    for pal in PALETTES:                   # Build a sprite set for every palette.
        sets.append({
            "walk": [_draw_girl(pal, "idle"), _draw_girl(pal, "step")],  # 2-frame walk cycle.
            "attack": _draw_girl(pal, "attack"),                          # Single attack frame.
            "dead": _draw_girl(pal, "dead"),                              # Single fainted frame.
        })
    return sets                            # Hand back all the sprite sets.


def build_pickup_sprites():
    """Return a dict of pickup sprites: {"health": Surface, "mana": Surface}."""
    # --- Health pickup: a red potion bottle ---
    health = pygame.Surface((40, 48), pygame.SRCALPHA)   # Small transparent canvas.
    pygame.draw.rect(health, (180, 180, 200), (16, 4, 8, 8))             # Cork/neck.
    pygame.draw.ellipse(health, (220, 40, 60), (6, 12, 28, 32))         # Round red body.
    pygame.draw.ellipse(health, (255, 120, 140), (12, 16, 8, 10))       # Glass highlight.
    pygame.draw.line(health, (255, 255, 255), (20, 22), (20, 30), 2)    # White cross (heal symbol).
    pygame.draw.line(health, (255, 255, 255), (16, 26), (24, 26), 2)    # White cross horizontal.

    # --- Mana pickup: a glowing blue crystal ---
    mana = pygame.Surface((40, 48), pygame.SRCALPHA)     # Transparent canvas.
    pygame.draw.polygon(mana, (60, 140, 255),                            # Diamond crystal body.
                        [(20, 4), (34, 24), (20, 44), (6, 24)])
    pygame.draw.polygon(mana, (160, 210, 255),                           # Lighter facet for shine.
                        [(20, 4), (27, 24), (20, 24)])
    pygame.draw.polygon(mana, (20, 80, 200),                             # Darker facet for depth.
                        [(20, 24), (20, 44), (6, 24)])

    return {"health": health, "mana": mana}   # Return both pickup sprites.


def build_bolt_sprite():
    """Return the glowing orb sprite used for the Spirit Bolt projectile."""
    size = 24                              # The orb is 24x24 pixels.
    surf = pygame.Surface((size, size), pygame.SRCALPHA)   # Transparent canvas.
    center = size // 2                     # Center coordinate for the circles.
    # Draw concentric circles from dim/large to bright/small for a glow effect.
    pygame.draw.circle(surf, (80, 160, 255, 90), (center, center), 12)   # Outer faint halo.
    pygame.draw.circle(surf, (120, 200, 255, 160), (center, center), 8)  # Mid glow.
    pygame.draw.circle(surf, (220, 240, 255, 255), (center, center), 4)  # Bright core.
    return surf                            # Return the bolt sprite.
