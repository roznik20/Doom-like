"""raycaster.py — the core pseudo-3D renderer.

This is the classic Wolfenstein/Doom-style technique:

1. The world is a 2D grid of walls. For every vertical column of the screen we
   shoot one ray from the player into the grid and step through cells (the
   "DDA" algorithm) until it hits a wall.
2. The distance to that wall decides how TALL to draw the wall slice: near
   walls are tall, far walls are short. A 1-pixel strip of the wall's texture
   is stretched to that height and blitted into the column.
3. We remember each column's wall distance in a "z-buffer" so that sprites
   (the demon-girls, pickups, bolts) can be hidden behind closer walls.
4. Sprites are drawn as flat billboards that always face the camera, sorted
   far-to-near, and clipped per-column against the z-buffer.

Everything is drawn at a low internal resolution and then scaled up to the
window for speed and a crunchy retro look.
"""

import math               # Trig for ray directions and fisheye correction.
import pygame             # Surfaces, scaling, and blitting.
from . import config      # Resolution, FOV, colors, depth limits.
from . import textures    # TEX_SIZE for texture-column math.


class Raycaster:
    """Renders the 3D view of a level from the player's viewpoint."""

    def __init__(self, texture_list):
        # The list of wall texture Surfaces (index = wall id; index 0 is None).
        self.textures = texture_list
        # The low-res surface we render the whole 3D scene onto each frame.
        self.surface = pygame.Surface((config.RENDER_WIDTH, config.RENDER_HEIGHT))
        # Per-column wall distance, filled during wall rendering and read by sprites.
        self.zbuffer = [config.MAX_DEPTH] * config.RENDER_WIDTH
        # The screen row that represents the horizon (eye level).
        self.horizon = config.RENDER_HEIGHT // 2
        # Precompute, for each column, the ray's angle offset from straight ahead.
        # Column 0 is the far left of the FOV; the last column is the far right.
        self.col_angles = [
            -config.HALF_FOV + (col / config.RENDER_WIDTH) * config.FOV
            for col in range(config.RENDER_WIDTH)
        ]
        # Precompute the cosine of each offset for fisheye correction (constant per column).
        self.col_cos = [math.cos(a) for a in self.col_angles]

    # ----- wall casting -----------------------------------------------------

    def _cast_column(self, col, player, level):
        """Cast one ray for screen column `col` and draw its wall slice.

        Returns nothing; it writes into self.surface and self.zbuffer.
        """
        # The world-space angle of this ray = player facing + this column's offset.
        ray_angle = player.angle + self.col_angles[col]
        # Unit direction vector of the ray.
        ray_dx = math.cos(ray_angle)        # Ray x component.
        ray_dy = math.sin(ray_angle)        # Ray y component.

        # The grid cell the player currently stands in.
        map_x = int(player.x)               # Integer tile x.
        map_y = int(player.y)               # Integer tile y.

        # Distance the ray travels (along itself) to cross one full grid line.
        # Guard against division by zero when a component is ~0.
        delta_x = abs(1.0 / ray_dx) if ray_dx != 0 else 1e30
        delta_y = abs(1.0 / ray_dy) if ray_dy != 0 else 1e30

        # Decide step direction (+1/-1) per axis and the distance to the FIRST grid line.
        if ray_dx < 0:                      # Ray points left.
            step_x = -1                     # We'll move to smaller x cells.
            side_x = (player.x - map_x) * delta_x   # Dist to the left cell boundary.
        else:                               # Ray points right.
            step_x = 1                      # Move to larger x cells.
            side_x = (map_x + 1.0 - player.x) * delta_x  # Dist to the right boundary.
        if ray_dy < 0:                      # Ray points up.
            step_y = -1                     # Move to smaller y cells.
            side_y = (player.y - map_y) * delta_y
        else:                               # Ray points down.
            step_y = 1                      # Move to larger y cells.
            side_y = (map_y + 1.0 - player.y) * delta_y

        # `side` records which kind of grid line we crossed last (0 = vertical x-line).
        side = 0
        # The wall texture id we eventually hit (0 means "nothing hit").
        hit_tile = 0
        # Step through the grid one boundary at a time until we hit a wall.
        while True:
            # Advance to whichever next grid line is closer (x or y).
            if side_x < side_y:
                side_x += delta_x           # Move past the next vertical line.
                map_x += step_x             # Enter the next cell in x.
                side = 0                    # We crossed a vertical (x) wall face.
            else:
                side_y += delta_y           # Move past the next horizontal line.
                map_y += step_y             # Enter the next cell in y.
                side = 1                    # We crossed a horizontal (y) wall face.

            # Stop if we've left the map bounds (nothing to draw for this column).
            if map_x < 0 or map_y < 0 or map_x >= level["width"] or map_y >= level["height"]:
                break
            # Read the wall id at the new cell.
            tile = level["grid"][map_y][map_x]
            # If it's a wall, record it and stop stepping.
            if tile != 0:
                hit_tile = tile
                break
            # Bail out if the ray has traveled past our maximum render depth.
            if min(side_x, side_y) > config.MAX_DEPTH:
                break

        # If nothing was hit, this column stays as floor/ceiling; record max depth.
        if hit_tile == 0:
            self.zbuffer[col] = config.MAX_DEPTH
            return

        # The Euclidean distance traveled along the ray to the wall face we hit.
        if side == 0:
            euclid = side_x - delta_x       # Back off the last x-step to the face.
        else:
            euclid = side_y - delta_y       # Back off the last y-step to the face.
        # Convert to PERPENDICULAR distance to remove the fisheye bulge.
        perp = max(0.05, euclid * self.col_cos[col])
        # Store this column's wall distance for sprite occlusion later.
        self.zbuffer[col] = perp

        # The on-screen pixel height of the (1-tile-tall) wall slice.
        line_h = int(config.SCREEN_DIST / perp)
        # The top y pixel of the wall slice, centered on the horizon.
        top = self.horizon - line_h // 2

        # --- Work out which texture column to sample (the wall's "u" coord) ---
        # Find the exact world hit point along the ray.
        hit_x = player.x + ray_dx * euclid  # World x of the hit.
        hit_y = player.y + ray_dy * euclid  # World y of the hit.
        # For a vertical (x) wall face we read across using the y fraction; else x.
        wall_u = hit_y if side == 0 else hit_x
        wall_u -= math.floor(wall_u)        # Keep only the fractional part (0..1).
        # Convert that 0..1 position into a texel column index.
        tex_x = int(wall_u * textures.TEX_SIZE)
        # Clamp into valid range to avoid an off-by-one out of the texture.
        tex_x = max(0, min(textures.TEX_SIZE - 1, tex_x))

        # Grab the wall's texture Surface (id maps directly into the list).
        tex = self.textures[hit_tile]
        # Extract a 1-pixel-wide vertical strip of the texture at tex_x.
        strip = tex.subsurface((tex_x, 0, 1, textures.TEX_SIZE))
        # Stretch that strip to the wall slice's pixel height (min 1px tall).
        column = pygame.transform.scale(strip, (1, max(1, line_h)))

        # --- Distance + side shading (fog) ---
        # Compute a brightness factor: closer = brighter, far = fades to fog.
        shade = max(0.15, 1.0 - perp / config.MAX_DEPTH)
        # Darken one wall-face orientation so corners read as 3D.
        if side == 1:
            shade *= 0.7
        # Multiply the column's colors by the shade factor (cheap fog).
        s = int(shade * 255)                # Convert factor to a 0..255 multiplier.
        column.fill((s, s, s), special_flags=pygame.BLEND_RGB_MULT)

        # Blit the finished, shaded wall column into the internal surface.
        self.surface.blit(column, (col, top))

    # ----- sprites ----------------------------------------------------------

    def _draw_sprites(self, player, sprite_list):
        """Billboard-render every sprite, clipped against the wall z-buffer.

        `sprite_list` items are dicts: {"x","y","surf","vscale"} where vscale
        scales the sprite's height relative to a full wall (1.0 = wall height).
        """
        # Precompute the player's facing components used for relative angles.
        # Build a render list annotated with each sprite's distance for sorting.
        renderables = []
        for spr in sprite_list:
            # Vector from the player to the sprite.
            dx = spr["x"] - player.x        # X offset.
            dy = spr["y"] - player.y        # Y offset.
            # Straight-line distance to the sprite.
            dist = math.hypot(dx, dy)
            # Skip degenerate/extremely close sprites (avoids divide-by-zero).
            if dist < 0.2:
                continue
            renderables.append((dist, dx, dy, spr))
        # Sort far-to-near so nearer sprites are drawn last (on top).
        renderables.sort(key=lambda r: r[0], reverse=True)

        # Draw each sprite as a vertical-strip billboard.
        for dist, dx, dy, spr in renderables:
            # World angle from the player to the sprite.
            world_angle = math.atan2(dy, dx)
            # Angle of the sprite relative to where the player is looking.
            rel = world_angle - player.angle
            # Wrap the relative angle into the range (-pi, pi].
            rel = (rel + math.pi) % (2 * math.pi) - math.pi
            # Cull sprites well outside the field of view (with a small margin).
            if abs(rel) > config.HALF_FOV + 0.4:
                continue
            # Perpendicular distance for correct (non-fisheye) sizing.
            perp = max(0.1, dist * math.cos(rel))
            # The horizontal screen column the sprite's center projects to.
            screen_x = (rel / config.FOV + 0.5) * config.RENDER_WIDTH

            # The sprite's source Surface and its native pixel dimensions.
            surf = spr["surf"]
            src_w, src_h = surf.get_size()
            # On-screen height: a full wall is SCREEN_DIST/perp; scale by vscale.
            draw_h = int((config.SCREEN_DIST / perp) * spr.get("vscale", 0.95))
            # Keep the sprite's aspect ratio when computing its width.
            draw_w = int(draw_h * src_w / src_h)
            # Ignore sprites that shrink to nothing.
            if draw_h <= 0 or draw_w <= 0:
                continue

            # Pre-scale the whole sprite once (cheaper than scaling per column).
            scaled = pygame.transform.scale(surf, (draw_w, draw_h))
            # Apply distance fog by multiplying RGB (alpha preserved by RGBA_MULT).
            shade = max(0.3, 1.0 - perp / config.MAX_DEPTH)
            s = int(shade * 255)
            scaled.fill((s, s, s, 255), special_flags=pygame.BLEND_RGBA_MULT)

            # Vertical placement: the sprite's FEET sit on the floor line.
            # The floor line for a full wall at this distance is here:
            floor_y = self.horizon + (config.SCREEN_DIST / perp) / 2
            # Top of the sprite is its height above that floor line.
            top = int(floor_y - draw_h)
            # Leftmost screen column the sprite occupies.
            left = int(screen_x - draw_w / 2)

            # Blit the sprite one column at a time so walls can occlude it.
            for c in range(draw_w):
                col = left + c                       # Target screen column.
                # Skip columns off-screen.
                if col < 0 or col >= config.RENDER_WIDTH:
                    continue
                # Skip if a wall in this column is CLOSER than the sprite.
                if perp >= self.zbuffer[col]:
                    continue
                # Grab the matching 1px-wide strip of the scaled sprite...
                strip = scaled.subsurface((c, 0, 1, draw_h))
                # ...and blit it into the column (alpha handles transparency).
                self.surface.blit(strip, (col, top))

    # ----- public entry point ----------------------------------------------

    def render(self, target, player, level, sprite_list):
        """Render the full 3D frame and blit it (scaled) onto `target`.

        `target`      is the real window Surface.
        `player`      provides the camera position/angle.
        `level`       is the current level dict.
        `sprite_list` is the list of billboards to draw this frame.
        """
        # Fill the ceiling (top half) and floor (bottom half) as flat colors.
        self.surface.fill(config.COLOR_CEILING,
                          (0, 0, config.RENDER_WIDTH, self.horizon))
        self.surface.fill(config.COLOR_FLOOR,
                          (0, self.horizon, config.RENDER_WIDTH,
                           config.RENDER_HEIGHT - self.horizon))

        # Cast a ray and draw a wall slice for every screen column.
        for col in range(config.RENDER_WIDTH):
            self._cast_column(col, player, level)

        # Draw all sprites on top, occluded by the wall z-buffer.
        self._draw_sprites(player, sprite_list)

        # Scale the finished low-res frame up to the full window size and blit.
        pygame.transform.scale(self.surface, target.get_size(), target)
