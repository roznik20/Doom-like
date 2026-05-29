"""textures.py — procedurally generated wall AND floor/ceiling textures.

Walls are returned as pygame Surfaces (the raycaster grabs 1px vertical strips
and stretches them). Floors and ceilings are returned as raw numpy arrays
because the raycaster does fast, vectorized "floor casting" — projecting each
horizontal screen row out into the world and sampling the texture per pixel
with numpy index math (a per-pixel Python loop would be far too slow).
"""

import numpy as np      # Fast array math for generating per-pixel colors.
import pygame           # We convert wall arrays into pygame Surfaces.

# Every texture is a square of this many pixels on each side (power of two).
TEX_SIZE = 64


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _new_array():
    """Return a blank (TEX_SIZE x TEX_SIZE x 3) RGB float array."""
    # Shape (width, height, 3) matches pygame's surfarray [x][y][channel] layout.
    return np.zeros((TEX_SIZE, TEX_SIZE, 3), dtype=np.float32)


def _to_surface(arr):
    """Convert a float color array into a ready-to-blit pygame Surface."""
    clipped = np.clip(arr, 0, 255).astype(np.uint8)   # Clamp to legal color range.
    surf = pygame.surfarray.make_surface(clipped)     # Build a Surface from it.
    return surf.convert()                             # Match the display format.


def _coords():
    """Return 2D x/y index grids so we can compute the whole texture at once."""
    ramp = np.arange(TEX_SIZE)                        # 0..TEX_SIZE-1 ramp.
    xs, ys = np.meshgrid(ramp, ramp, indexing="ij")   # Broadcast into 2D grids.
    return xs, ys                                     # xs varies along x, ys along y.


# ---------------------------------------------------------------------------
# Wall textures (returned as Surfaces)
# ---------------------------------------------------------------------------

def _brick():
    """id 1 — dark demonic running-bond brick."""
    arr = _new_array()                       # Blank color array.
    xs, ys = _coords()                       # Coordinate grids.
    row = ys // 16                           # Which 16px brick row each texel is in.
    offset = (row % 2) * 16                  # Offset alternate rows by half a brick.
    bx = (xs + offset) % 32                  # Horizontal position within a brick.
    mortar = (bx < 2) | (ys % 16 < 2)        # Thin grout lines between bricks.
    noise = (np.sin(xs * 7.0 + ys * 31.0) * 0.5 + 0.5) * 24 - 12  # Surface noise.
    arr[..., 0] = 120 + noise                # Red (brick body is red-brown).
    arr[..., 1] = 40 + noise * 0.4           # Green.
    arr[..., 2] = 50 + noise * 0.4           # Blue.
    arr[mortar, 0] = 30 + noise[mortar]      # Grout red.
    arr[mortar, 1] = 24 + noise[mortar]      # Grout green.
    arr[mortar, 2] = 28 + noise[mortar]      # Grout blue.
    return _to_surface(arr)


def _flesh():
    """id 2 — organic veiny flesh wall."""
    arr = _new_array()
    xs, ys = _coords()
    wave = np.sin(xs * 0.4) * np.cos(ys * 0.3) * 30   # Organic undulation.
    noise = (np.sin(xs * 3.0 + ys * 17.0) * 0.5 + 0.5) * 20 - 10
    arr[..., 0] = 150 + wave + noise         # Red dominant (pink flesh).
    arr[..., 1] = 60 + wave * 0.5 + noise    # Green.
    arr[..., 2] = 70 + noise                 # Blue.
    # Add a few darker "veins" as diagonal dark streaks.
    veins = (np.sin((xs + ys) * 0.6) > 0.93)
    arr[veins, 0] *= 0.5                      # Darken veins.
    arr[veins, 1] *= 0.5
    arr[veins, 2] *= 0.5
    return _to_surface(arr)


def _rune():
    """id 3 — cold gray stone with a central glowing rune band."""
    arr = _new_array()
    xs, ys = _coords()
    noise = (np.sin(xs * 11.0 + ys * 5.0) * 0.5 + 0.5) * 18 - 9
    arr[..., 0] = 70 + noise                 # Stone (slightly bluish gray).
    arr[..., 1] = 70 + noise
    arr[..., 2] = 80 + noise
    band = (xs > 26) & (xs < 38)             # Vertical glyph band down the middle.
    glow = (np.sin(ys * 0.8) * 0.5 + 0.5) * 160
    arr[band, 0] = 80 + glow[band]           # Magenta glow.
    arr[band, 1] = 20
    arr[band, 2] = 120 + glow[band]
    return _to_surface(arr)


def _exit_portal(phase=0.0):
    """id 4 — swirling green-gold level-exit portal at a given swirl phase."""
    arr = _new_array()
    xs, ys = _coords()
    dx = xs - 32; dy = ys - 32               # Offsets from center.
    dist = np.sqrt(dx * dx + dy * dy)        # Radial distance.
    # The `phase` rotates the vortex so a sequence of frames animates the swirl.
    swirl = np.sin(dist * 0.5 - np.arctan2(dy, dx) * 3.0 + phase) * 0.5 + 0.5
    radial = np.clip(200 - dist * 4, 0, 255)
    arr[..., 0] = 40 + swirl * 60            # Gold-ish red.
    arr[..., 1] = np.clip(200 - dist * 2, 0, 255)  # Green glow.
    arr[..., 2] = 80 + radial * 0.3 + swirl * 40   # Blue depth pulses with the swirl.
    return _to_surface(arr)


def _exit_portal_frames(n=8):
    """Return a list of `n` portal frames whose swirl rotates over the loop."""
    return [_exit_portal(2 * np.pi * i / n) for i in range(n)]


def _door():
    """id 5 — a metal sliding door with a central seam and warning stripes."""
    arr = _new_array()
    xs, ys = _coords()
    base = 90 + (np.sin(ys * 0.6) * 0.5 + 0.5) * 30   # Brushed-metal vertical sheen.
    arr[..., 0] = base * 0.8                 # Slightly warm gray.
    arr[..., 1] = base * 0.8
    arr[..., 2] = base * 0.9
    seam = np.abs(xs - 32) < 2               # Central vertical seam (door split).
    arr[seam] = 20                           # Dark seam.
    # Hazard stripes along the top and bottom edges.
    stripe = ((xs + ys) % 12 < 6)
    edge = (ys < 10) | (ys > 54)
    mask = stripe & edge
    arr[mask, 0] = 200; arr[mask, 1] = 170; arr[mask, 2] = 0   # Yellow hazard.
    return _to_surface(arr)


def _metal():
    """id 6 — riveted metal tech panel."""
    arr = _new_array()
    xs, ys = _coords()
    arr[..., 0] = 70; arr[..., 1] = 74; arr[..., 2] = 84       # Base steel gray.
    panel = ((xs % 32 < 2) | (ys % 32 < 2))   # Panel division lines.
    arr[panel] = 45
    # Rivets: small bright dots on a grid.
    rivet = ((xs % 32 == 8) | (xs % 32 == 24)) & ((ys % 32 == 8) | (ys % 32 == 24))
    arr[rivet, 0] = 150; arr[rivet, 1] = 155; arr[rivet, 2] = 165
    return _to_surface(arr)


def _boss_wall():
    """id 7 — ornate gold-trimmed obsidian for the boss arena."""
    arr = _new_array()
    xs, ys = _coords()
    arr[..., 0] = 25; arr[..., 1] = 10; arr[..., 2] = 30       # Dark obsidian.
    # Gold diamond lattice.
    diamond = (np.abs(((xs + ys) % 24) - 12) + np.abs(((xs - ys) % 24) - 12)) < 4
    arr[diamond, 0] = 210; arr[diamond, 1] = 170; arr[diamond, 2] = 40   # Gold.
    return _to_surface(arr)


def _locked_door(tint):
    """A metal door painted in a key color (red/blue/yellow) with a keyhole."""
    arr = _new_array()
    xs, ys = _coords()
    base = 70 + (np.sin(ys * 0.6) * 0.5 + 0.5) * 20        # Brushed sheen.
    # Wash the metal toward the key color so it reads as a colored lock door.
    arr[..., 0] = base * 0.4 + tint[0] * 0.5
    arr[..., 1] = base * 0.4 + tint[1] * 0.5
    arr[..., 2] = base * 0.4 + tint[2] * 0.5
    seam = np.abs(xs - 32) < 2                             # Central seam.
    arr[seam] = 15
    # A bright keyhole emblem in the middle of each leaf.
    emblem = (((xs % 32) - 16) ** 2 + ((ys - 30) ** 2)) < 16
    arr[emblem, 0] = min(255, tint[0] + 80)
    arr[emblem, 1] = min(255, tint[1] + 80)
    arr[emblem, 2] = min(255, tint[2] + 80)
    return _to_surface(arr)


def build_textures():
    """Return the wall texture list, indexed by wall id (0 = None/empty)."""
    return [
        None,                              # 0: empty / walkable.
        _brick(),                          # 1: brick.
        _flesh(),                          # 2: flesh.
        _rune(),                           # 3: rune stone.
        _exit_portal_frames(),             # 4: exit portal (animated frame list).
        _door(),                           # 5: sliding door.
        _metal(),                          # 6: metal panel.
        _boss_wall(),                      # 7: boss-arena wall.
        _locked_door((200, 40, 50)),       # 8: red locked door.
        _locked_door((50, 90, 220)),       # 9: blue locked door.
        _locked_door((220, 190, 40)),      # 10: yellow locked door.
    ]


# ---------------------------------------------------------------------------
# Floor + ceiling textures (returned as raw numpy uint8 arrays for casting)
# Each is indexed [y][x] (row, col) so floor-casting code can fancy-index it.
# ---------------------------------------------------------------------------

def _flat_array():
    """Blank float array for a flat (floor/ceiling) texture."""
    return np.zeros((TEX_SIZE, TEX_SIZE, 3), dtype=np.float32)


def _flat_coords():
    """x/y grids with [row][col] indexing for flat textures."""
    ramp = np.arange(TEX_SIZE)
    ys, xs = np.meshgrid(ramp, ramp, indexing="ij")   # ys=row, xs=col.
    return xs, ys


def _floor_stone():
    """Cobblestone floor."""
    arr = _flat_array(); xs, ys = _flat_coords()
    cell = (np.sin(xs * 0.5) * np.cos(ys * 0.5))       # Round cobble bumps.
    noise = (np.sin(xs * 9.0 + ys * 5.0) * 0.5 + 0.5) * 20
    v = 55 + cell * 25 + noise                         # Gray value.
    arr[..., 0] = v; arr[..., 1] = v; arr[..., 2] = v + 6
    grout = ((xs % 16 < 1) | (ys % 16 < 1))            # Dark grout grid.
    arr[grout] = 25
    return np.clip(arr, 0, 255).astype(np.uint8)


def _floor_blood():
    """Wet bloody floor for the flesh catacombs."""
    arr = _flat_array(); xs, ys = _flat_coords()
    pool = (np.sin(xs * 0.3) * np.sin(ys * 0.4) * 0.5 + 0.5)   # Pooling pattern.
    arr[..., 0] = 60 + pool * 90               # Dark red.
    arr[..., 1] = 10 + pool * 15
    arr[..., 2] = 10 + pool * 10
    return np.clip(arr, 0, 255).astype(np.uint8)


def _floor_rune():
    """Polished rune-marble floor for the sanctum."""
    arr = _flat_array(); xs, ys = _flat_coords()
    swirl = np.sin((xs + ys) * 0.2) * np.cos((xs - ys) * 0.2)  # Marble veining.
    v = 45 + swirl * 20
    arr[..., 0] = v; arr[..., 1] = v; arr[..., 2] = v + 25     # Cool bluish marble.
    glyph = (((xs % 32) - 16) ** 2 + ((ys % 32) - 16) ** 2) < 9  # Glowing dots.
    arr[glyph, 0] = 120; arr[glyph, 1] = 40; arr[glyph, 2] = 200
    return np.clip(arr, 0, 255).astype(np.uint8)


def _ceil_cave():
    """Dim rocky cave ceiling."""
    arr = _flat_array(); xs, ys = _flat_coords()
    noise = (np.sin(xs * 4.0 + ys * 7.0) * 0.5 + 0.5) * 30
    v = 30 + noise
    arr[..., 0] = v; arr[..., 1] = v * 0.8; arr[..., 2] = v * 0.9
    return np.clip(arr, 0, 255).astype(np.uint8)


def _ceil_flesh():
    """Pulsing flesh ceiling."""
    arr = _flat_array(); xs, ys = _flat_coords()
    wave = np.sin(xs * 0.4) * np.cos(ys * 0.3) * 20
    arr[..., 0] = 70 + wave; arr[..., 1] = 25 + wave * 0.4; arr[..., 2] = 30
    return np.clip(arr, 0, 255).astype(np.uint8)


def _floor_lava():
    """Glowing molten lava floor (a hazard)."""
    arr = _flat_array(); xs, ys = _flat_coords()
    flow = (np.sin(xs * 0.3 + ys * 0.2) * np.cos(ys * 0.4) * 0.5 + 0.5)   # Molten flow.
    crust = (np.sin(xs * 0.8) * np.sin(ys * 0.8) > 0.4)                    # Dark crust veins.
    arr[..., 0] = 180 + flow * 70           # Hot red-orange.
    arr[..., 1] = 40 + flow * 110
    arr[..., 2] = 10 + flow * 20
    arr[crust, 0] *= 0.35                    # Darken the crust.
    arr[crust, 1] *= 0.25
    arr[crust, 2] *= 0.35
    return np.clip(arr, 0, 255).astype(np.uint8)


def _ceil_void():
    """Starry void ceiling for the sanctum/boss arena."""
    arr = _flat_array(); xs, ys = _flat_coords()
    arr[..., 0] = 8; arr[..., 1] = 4; arr[..., 2] = 24         # Near-black blue.
    stars = (np.sin(xs * 12.9 + ys * 7.7) > 0.985)             # Sparse star dots.
    arr[stars] = 220
    return np.clip(arr, 0, 255).astype(np.uint8)


def build_flats():
    """Return dicts of floor and ceiling numpy textures, keyed by theme name."""
    floors = {
        "stone": _floor_stone(),     # Level 1 floor.
        "blood": _floor_blood(),     # Level 2 floor.
        "rune": _floor_rune(),       # Level 3/4 floor.
        "lava": _floor_lava(),       # Hazard floor (also used as a theme floor).
    }
    ceils = {
        "cave": _ceil_cave(),        # Level 1 ceiling.
        "flesh": _ceil_flesh(),      # Level 2 ceiling.
        "void": _ceil_void(),        # Level 3/4 ceiling.
    }
    return floors, ceils
