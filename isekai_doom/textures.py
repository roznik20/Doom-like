"""textures.py — procedurally generated wall textures.

Rather than shipping image files, we paint each wall texture into a small
pygame Surface at startup using numpy math. The raycaster later grabs a
1-pixel-wide vertical strip from the relevant texture and stretches it to the
height of the wall column it is drawing — that is what makes the walls look
textured and "3D".
"""

import numpy as np      # Fast array math for generating per-pixel colors.
import pygame           # We convert the numpy arrays into pygame Surfaces.

# Every wall texture is a square of this many pixels on each side.
# A power of two keeps the wrap-around math (modulo) clean.
TEX_SIZE = 64


def _new_array():
    """Return a blank (TEX_SIZE x TEX_SIZE x 3) RGB array of floats.

    We work in float so we can add noise/brightness freely, then clip to the
    valid 0–255 byte range right before converting to a Surface.
    """
    # Shape is (width, height, 3) to match pygame's surfarray [x][y][channel] layout.
    return np.zeros((TEX_SIZE, TEX_SIZE, 3), dtype=np.float32)


def _to_surface(arr):
    """Convert a float color array into a ready-to-blit pygame Surface."""
    # Clip values into the legal color range so nothing wraps or errors.
    clipped = np.clip(arr, 0, 255).astype(np.uint8)
    # make_surface interprets the array as [x][y][rgb] and builds a Surface.
    surf = pygame.surfarray.make_surface(clipped)
    # convert() matches the display's pixel format for faster future blits.
    return surf.convert()


def _coords():
    """Return two 2D arrays giving the x and y index of every texel.

    Using meshgrid lets us compute the whole texture at once (vectorized)
    instead of looping pixel by pixel in slow Python.
    """
    # A 0..TEX_SIZE-1 ramp for one axis.
    ramp = np.arange(TEX_SIZE)
    # meshgrid broadcasts that ramp into full 2D coordinate grids.
    # indexing="ij" makes xs vary along axis 0 (x) and ys along axis 1 (y).
    xs, ys = np.meshgrid(ramp, ramp, indexing="ij")
    # Return both coordinate grids.
    return xs, ys


def _brick():
    """Texture id 1 — a dark, demonic running-bond brick wall."""
    arr = _new_array()                 # Start from a blank color array.
    xs, ys = _coords()                 # Per-texel x/y coordinate grids.
    # Which 16px-tall brick row each texel belongs to.
    row = ys // 16
    # Shift every other row by half a brick to get the offset "running bond" look.
    offset = (row % 2) * 16
    # Horizontal position within a 32px-wide brick (with the row offset applied).
    bx = (xs + offset) % 32
    # Mortar = the thin grout lines: near a brick's left edge OR a row's top edge.
    mortar = (bx < 2) | (ys % 16 < 2)
    # Deterministic per-texel noise in roughly [-12, 12] for surface variation.
    noise = (np.sin(xs * 7.0 + ys * 31.0) * 0.5 + 0.5) * 24 - 12
    # Default the whole texture to the reddish brick body color (+ noise).
    arr[..., 0] = 120 + noise          # Red channel: strong (brick is red-brown).
    arr[..., 1] = 40 + noise * 0.4     # Green channel: low.
    arr[..., 2] = 50 + noise * 0.4     # Blue channel: low.
    # Now overwrite the mortar texels with a dark gray grout color.
    arr[mortar, 0] = 30 + noise[mortar]   # Grout red.
    arr[mortar, 1] = 24 + noise[mortar]   # Grout green.
    arr[mortar, 2] = 28 + noise[mortar]   # Grout blue.
    return _to_surface(arr)            # Convert to a Surface and return it.


def _flesh():
    """Texture id 2 — an organic, veiny flesh wall for the catacombs."""
    arr = _new_array()                 # Blank color array.
    xs, ys = _coords()                 # Coordinate grids.
    # Overlapping sine/cosine waves create a soft, organic undulation.
    wave = np.sin(xs * 0.4) * np.cos(ys * 0.3) * 30
    # Fine high-frequency noise on top of the waves.
    noise = (np.sin(xs * 3.0 + ys * 17.0) * 0.5 + 0.5) * 20 - 10
    # Pinkish-red flesh tone modulated by waves + noise.
    arr[..., 0] = 150 + wave + noise        # Red: dominant (flesh is pink/red).
    arr[..., 1] = 60 + wave * 0.5 + noise   # Green: moderate.
    arr[..., 2] = 70 + noise                # Blue: low.
    return _to_surface(arr)            # Convert and return.


def _rune():
    """Texture id 3 — cold gray stone with a central glowing rune band."""
    arr = _new_array()                 # Blank color array.
    xs, ys = _coords()                 # Coordinate grids.
    # Subtle noise for the stone body.
    noise = (np.sin(xs * 11.0 + ys * 5.0) * 0.5 + 0.5) * 18 - 9
    # Fill the whole tile with cold gray stone first.
    arr[..., 0] = 70 + noise           # Stone red.
    arr[..., 1] = 70 + noise           # Stone green.
    arr[..., 2] = 80 + noise           # Stone blue (slightly bluish).
    # Boolean mask selecting the vertical band down the middle of the tile.
    band = (xs > 26) & (xs < 38)
    # Brightness along the band varies with y to suggest carved glyphs.
    glow = (np.sin(ys * 0.8) * 0.5 + 0.5) * 160
    # Paint the band with a magenta/cyan glowing rune color.
    arr[band, 0] = 80 + glow[band]     # Glow red.
    arr[band, 1] = 20                  # Glow green (kept low for a cold look).
    arr[band, 2] = 120 + glow[band]    # Glow blue (dominant -> magenta glow).
    return _to_surface(arr)            # Convert and return.


def _exit_portal():
    """Texture id 4 — the swirling green-gold level-exit portal."""
    arr = _new_array()                 # Blank color array.
    xs, ys = _coords()                 # Coordinate grids.
    # Offsets from the tile center, used for a radial/swirl pattern.
    dx = xs - 32                       # Horizontal distance from center.
    dy = ys - 32                       # Vertical distance from center.
    dist = np.sqrt(dx * dx + dy * dy)  # Radial distance from the center texel.
    # A swirl term combining radius and angle for a vortex feel.
    swirl = np.sin(dist * 0.5 - np.arctan2(dy, dx) * 3.0) * 0.5 + 0.5
    # Radial brightness that is strongest near the center.
    radial = np.clip(200 - dist * 4, 0, 255)
    # Compose a glowing green-gold portal color.
    arr[..., 0] = 40 + swirl * 60      # Red: low-moderate (adds gold).
    arr[..., 1] = np.clip(200 - dist * 2, 0, 255)  # Green: dominant (eerie glow).
    arr[..., 2] = 80 + radial * 0.3    # Blue: a little, for depth.
    return _to_surface(arr)            # Convert and return.


def build_textures():
    """Build and return the texture list, indexed by wall id.

    Index 0 is None on purpose: a wall id of 0 means "empty space", so it
    should never be drawn. Indices 1..4 map to the four wall textures.
    Must be called AFTER pygame's display has been created (Surfaces need it).
    """
    return [
        None,            # 0: empty / walkable -> no texture.
        _brick(),        # 1: demonic brick.
        _flesh(),        # 2: organic flesh.
        _rune(),         # 3: glowing rune stone.
        _exit_portal(),  # 4: exit portal.
    ]
