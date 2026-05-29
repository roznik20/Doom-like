"""raycaster.py — the core pseudo-3D renderer (now greatly expanded).

The classic Wolfenstein/Doom technique, upgraded:

  * Camera-plane ray model (dir + plane) so wall, floor, and sprite maths all
    agree perfectly and there is no fisheye distortion.
  * TEXTURED floors and ceilings via vectorized numpy "floor casting": every
    horizontal screen row is projected out into the world and the floor/ceiling
    texture is sampled per pixel with numpy index math (a Python per-pixel loop
    would be far too slow).
  * Distance fog applied to walls, floors, and sprites for depth.
  * A per-column z-buffer so sprites AND particles are correctly hidden behind
    nearer walls.
  * Sliding doors that retract upward as they open.

Everything is drawn at a low internal resolution and scaled up to the window.
"""

import math               # Trig for the camera vectors.
import pygame             # Surfaces, scaling, blitting, surfarray.
import numpy as np        # Vectorized floor/ceiling casting.
from . import config      # Resolution, FOV, colors, depth limits.
from . import textures    # TEX_SIZE + texture data.


class Raycaster:
    """Renders the 3D view of a level from the player's viewpoint."""

    def __init__(self, texture_list, floor_tex, ceil_tex):
        # Wall textures (index = wall id; index 0 is None).
        self.textures = texture_list
        # The current floor + ceiling numpy textures (set per level theme).
        self.floor_tex = floor_tex          # numpy (TEX_SIZE, TEX_SIZE, 3).
        self.ceil_tex = ceil_tex            # numpy (TEX_SIZE, TEX_SIZE, 3).
        # The low-res surface we render the whole 3D scene onto each frame.
        self.surface = pygame.Surface((config.RENDER_WIDTH, config.RENDER_HEIGHT))
        # Per-column wall (perpendicular) distance, read by sprites + particles.
        self.zbuffer = np.full(config.RENDER_WIDTH, config.MAX_DEPTH, dtype=np.float32)
        # The screen row that represents the horizon (eye level).
        self.horizon = config.RENDER_HEIGHT // 2
        # A reusable column index array for vectorized floor casting.
        self._cols = np.arange(config.RENDER_WIDTH)
        # A reusable RGB image buffer for the floor/ceiling background.
        self._bg = np.zeros((config.RENDER_WIDTH, config.RENDER_HEIGHT, 3), dtype=np.uint8)
        # The fog color as a numpy array for quick blending.
        self._fog = np.array(config.COLOR_FOG, dtype=np.float32)
        # Cache of scaled sprite surfaces keyed by (sprite id, width, height).
        self._sprite_cache = {}
        # Lava texture used for hazard floor cells (set by the game).
        self.lava_tex = None

    def set_theme(self, floor_tex, ceil_tex, fog):
        """Swap the floor/ceiling textures and fog color (called per level)."""
        self.floor_tex = floor_tex          # New floor texture.
        self.ceil_tex = ceil_tex            # New ceiling texture.
        self._fog = np.array(fog, dtype=np.float32)   # New fog color.

    # ----- floor + ceiling casting ------------------------------------------

    def _cast_floor_ceiling(self, player, level, dirx, diry, planex, planey):
        """Fill the background buffer with textured floor + ceiling, then blit it.

        Fully vectorized: instead of looping over rows in Python, we build 2D
        (column x row) coordinate arrays and sample the textures in a single
        numpy fancy-index, which is dramatically faster. Hazard (lava) cells are
        overlaid by sampling the lava texture only where the floor cell is a
        hazard (via a precomputed boolean grid on the level).
        """
        H = config.RENDER_HEIGHT
        W = config.RENDER_WIDTH
        ts = textures.TEX_SIZE
        horizon = self.horizon                  # May be shifted by the look pitch.
        # Leftmost (camera x=-1) and rightmost (camera x=+1) ray directions.
        ray0x = dirx - planex; ray0y = diry - planey
        ray1x = dirx + planex; ray1y = diry + planey
        posZ = 0.5 * H                          # Vertical camera height term.
        bg = self._bg
        fog = self._fog
        maxd = config.MAX_DEPTH
        cols = self._cols.reshape(W, 1).astype(np.float32)   # (W,1) column indices.
        hazard_grid = level.get("hazard_grid") if level else None

        def cast_region(p_vals, rows, tex, is_floor):
            """Sample one horizontal band (floor or ceiling) and write it to bg."""
            P = len(p_vals)
            if P <= 0:
                return
            row_dist = posZ / p_vals                          # (P,) distances.
            rd = row_dist.reshape(1, P)
            fx = player.x + rd * ray0x + cols * (rd * (ray1x - ray0x) / W)
            fy = player.y + rd * ray0y + cols * (rd * (ray1y - ray0y) / W)
            tx = (fx * ts).astype(np.int32) % ts
            ty = (fy * ts).astype(np.int32) % ts
            shade = np.clip(1.0 - row_dist / maxd, 0.12, 1.0).reshape(1, P, 1)
            px = tex[ty, tx].astype(np.float32) * shade + fog * (1 - shade)
            # Lava overlay only applies to the floor band.
            if is_floor and hazard_grid is not None and self.lava_tex is not None:
                gh, gw = hazard_grid.shape
                cellx = np.clip(fx.astype(np.int32), 0, gw - 1)
                celly = np.clip(fy.astype(np.int32), 0, gh - 1)
                mask = hazard_grid[celly, cellx]
                if mask.any():
                    lava_shade = np.clip(shade + 0.4, 0, 1)
                    lava_px = self.lava_tex[ty, tx].astype(np.float32) * lava_shade + fog * (1 - lava_shade)
                    px = np.where(mask[..., None], lava_px, px)
            # Scatter the computed colors into their (arbitrary) screen rows.
            bg[:, rows, :] = px.astype(np.uint8)

        # Floor band: screen rows below the horizon (horizon+1 .. H-1).
        if horizon < H - 1:
            pf = np.arange(1, H - horizon, dtype=np.float32)
            cast_region(pf, (horizon + pf).astype(np.int32), self.floor_tex, True)
        # Ceiling band: screen rows above the horizon (0 .. horizon-1).
        if horizon > 0:
            pc = np.arange(1, horizon + 1, dtype=np.float32)
            cast_region(pc, (horizon - pc).astype(np.int32), self.ceil_tex, False)
        # Paint the seam row at the horizon (if on-screen) with fog.
        if 0 <= horizon < H:
            bg[:, horizon, :] = fog.astype(np.uint8)

        # Blit the whole background image to the render surface in one call.
        pygame.surfarray.blit_array(self.surface, bg)

    # ----- wall casting -----------------------------------------------------

    def _cast_walls(self, player, level, dirx, diry, planex, planey):
        """DDA-cast every column and draw textured (optionally sliding) walls."""
        W = config.RENDER_WIDTH
        H = config.RENDER_HEIGHT
        ts = textures.TEX_SIZE
        grid = level["grid"]
        gw, gh = level["width"], level["height"]
        # Per-cell door open fractions (0 closed .. 1 fully open). May be empty.
        door_frac = level.get("door_frac", {})

        for col in range(W):
            # cameraX runs from -1 (left edge) to +1 (right edge) across the screen.
            cameraX = 2.0 * col / W - 1.0
            # This column's ray direction = forward + plane * cameraX.
            rdx = dirx + planex * cameraX
            rdy = diry + planey * cameraX

            # Current map cell.
            mapx = int(player.x)
            mapy = int(player.y)
            # Distance the ray travels to cross one full grid line on each axis.
            ddx = abs(1.0 / rdx) if rdx != 0 else 1e30
            ddy = abs(1.0 / rdy) if rdy != 0 else 1e30
            # Step direction and initial side distances.
            if rdx < 0:
                stepx = -1
                sidex = (player.x - mapx) * ddx
            else:
                stepx = 1
                sidex = (mapx + 1.0 - player.x) * ddx
            if rdy < 0:
                stepy = -1
                sidey = (player.y - mapy) * ddy
            else:
                stepy = 1
                sidey = (mapy + 1.0 - player.y) * ddy

            side = 0                         # Which face we last crossed.
            hit_tile = 0                     # The wall id we hit.
            hit_door_frac = 0.0              # Open fraction if it was a door.
            # Step through cells until we hit a (non-open) wall or run out of range.
            while True:
                if sidex < sidey:
                    sidex += ddx
                    mapx += stepx
                    side = 0
                else:
                    sidey += ddy
                    mapy += stepy
                    side = 1
                if mapx < 0 or mapy < 0 or mapx >= gw or mapy >= gh:
                    break                    # Left the map.
                tile = grid[mapy][mapx]
                if tile != 0:
                    # A fully-open door is see-through: keep stepping past it.
                    if tile == config.TEX_DOOR:
                        frac = door_frac.get((mapx, mapy), 0.0)
                        if frac >= 1.0:
                            continue         # Walk the ray through the open door.
                        hit_door_frac = frac
                    hit_tile = tile
                    break
                if min(sidex, sidey) > config.MAX_DEPTH:
                    break                    # Past render distance.

            # Nothing hit: this column is all floor/ceiling; record far depth.
            if hit_tile == 0:
                self.zbuffer[col] = config.MAX_DEPTH
                continue

            # Perpendicular distance (no fisheye) straight from the DDA sides.
            if side == 0:
                perp = sidex - ddx
            else:
                perp = sidey - ddy
            perp = max(0.02, perp)
            self.zbuffer[col] = perp          # Save for sprite/particle occlusion.

            # On-screen wall slice height (a 1-tile wall fills the screen at dist 1).
            line_h = int(H / perp)
            # Centered on the horizon.
            top = self.horizon - line_h // 2
            # Doors slide UP as they open: shift the slice upward by its fraction.
            if hit_tile == config.TEX_DOOR and hit_door_frac > 0:
                top -= int(hit_door_frac * line_h)

            # Which texture column to sample (the wall's horizontal "u").
            if side == 0:
                wall_u = player.y + perp * rdy
            else:
                wall_u = player.x + perp * rdx
            wall_u -= math.floor(wall_u)
            tex_x = int(wall_u * ts)
            tex_x = max(0, min(ts - 1, tex_x))

            # Grab + stretch a 1px texture strip to the wall height. Some texture
            # entries are a list of animation frames; pick the current frame.
            tex = self.textures[hit_tile]
            if isinstance(tex, list):
                tex = tex[self._anim_idx % len(tex)]
            strip = tex.subsurface((tex_x, 0, 1, ts))
            column = pygame.transform.scale(strip, (1, max(1, line_h)))

            # Distance + side fog shading.
            shade = max(0.15, 1.0 - perp / config.MAX_DEPTH)
            if side == 1:
                shade *= 0.7                  # Darken one orientation for 3D feel.
            s = int(shade * 255)
            column.fill((s, s, s), special_flags=pygame.BLEND_RGB_MULT)

            # Blit the finished wall column.
            self.surface.blit(column, (col, top))

    # ----- sprite + particle billboards -------------------------------------

    def _draw_sprites(self, player, sprite_list, dirx, diry, planex, planey):
        """Billboard-render every sprite, clipped against the wall z-buffer."""
        W = config.RENDER_WIDTH
        H = config.RENDER_HEIGHT
        # Inverse of the camera matrix [plane | dir], used to project sprites.
        det = planex * diry - dirx * planey
        if abs(det) < 1e-9:
            return                            # Degenerate camera; skip.
        inv = 1.0 / det

        # Annotate each sprite with its camera-space depth, then sort far->near.
        renderables = []
        for spr in sprite_list:
            sx = spr["x"] - player.x          # Sprite x relative to player.
            sy = spr["y"] - player.y          # Sprite y relative to player.
            # transformY is the perpendicular depth; transformX the lateral pos.
            tX = inv * (diry * sx - dirx * sy)
            tY = inv * (-planey * sx + planex * sy)
            if tY <= 0.05:
                continue                      # Behind the camera; skip.
            renderables.append((tY, tX, spr))
        renderables.sort(key=lambda r: r[0], reverse=True)

        for tY, tX, spr in renderables:
            surf = spr["surf"]
            src_w, src_h = surf.get_size()
            # Screen column the sprite center projects to.
            screen_x = int((W / 2) * (1 + tX / tY))
            # On-screen height scaled by the sprite's vscale (1.0 = wall height).
            draw_h = int((H / tY) * spr.get("vscale", 0.95))
            if draw_h <= 1:
                continue
            # Clamp the height so an extremely close sprite can't trigger a
            # gigantic (slow) scale operation.
            draw_h = min(draw_h, H * 3)
            draw_w = max(1, int(draw_h * src_w / src_h))
            # Reuse a cached scaled copy when the same sprite+size recurs
            # (e.g. a stationary boss), avoiding a costly rescale every frame.
            key = (id(surf), draw_w, draw_h)
            base = self._sprite_cache.get(key)
            if base is None:
                base = pygame.transform.scale(surf, (draw_w, draw_h))
                if len(self._sprite_cache) > 256:
                    self._sprite_cache.clear()    # Keep the cache bounded.
                self._sprite_cache[key] = base
            # Fog shade: skip it entirely for bright (close) sprites; otherwise
            # work on a copy so the cached original is never darkened twice.
            shade = max(0.3, 1.0 - tY / config.MAX_DEPTH)
            if shade >= 0.92:
                scaled = base
            else:
                scaled = base.copy()
                s = int(shade * 255)
                scaled.fill((s, s, s, 255), special_flags=pygame.BLEND_RGBA_MULT)
            # Feet rest on the floor line for a full wall at this depth.
            floor_y = self.horizon + (H / tY) / 2
            top = int(floor_y - draw_h)
            left = int(screen_x - draw_w / 2)
            # The on-screen column span this sprite covers, clipped to the view.
            c0 = max(0, left)
            c1 = min(W, left + draw_w)
            if c0 >= c1:
                continue                      # Entirely off-screen.
            # Fast path: if NO wall column in the span is closer than the sprite,
            # blit the whole sprite in one call (huge win for big unoccluded
            # sprites like the boss in an open arena).
            if np.all(self.zbuffer[c0:c1] > tY):
                self.surface.blit(scaled, (left, top))
                # Jiggle physics: bounce ONLY the chest sub-region of the sprite.
                self._jiggle_chest(scaled, spr, left, top, draw_w, draw_h)
            else:
                # Otherwise blit column-by-column so nearer walls occlude it.
                for colx in range(c0, c1):
                    if tY >= self.zbuffer[colx]:
                        continue              # A wall is closer here.
                    strip = scaled.subsurface((colx - left, 0, 1, draw_h))
                    self.surface.blit(strip, (colx, top))

    def _jiggle_chest(self, scaled, spr, left, top, draw_w, draw_h):
        """Re-draw just the chest region of an enemy with a squash-and-stretch.

        We crop the chest rectangle from the already-scaled sprite, scale that
        small patch by the enemy's jiggle value (wider+shorter, anchored at its
        underside so it bounces), and blit it back over the same spot. Only the
        bust moves; the rest of the figure is untouched.
        """
        rect = spr.get("chest")
        jig = spr.get("jiggle", 0.0)
        # Skip when there's no chest rect (pickups/projectiles) or negligible wobble.
        if rect is None or abs(jig) < 0.02:
            return
        rx = int(rect[0] * draw_w)            # Chest patch left within the sprite.
        ry = int(rect[1] * draw_h)            # Chest patch top.
        rw = max(1, int(rect[2] * draw_w))    # Chest patch width.
        rh = max(1, int(rect[3] * draw_h))    # Chest patch height.
        # Keep the patch inside the sprite bounds.
        if rx + rw > draw_w or ry + rh > draw_h:
            return
        patch = scaled.subsurface((rx, ry, rw, rh))
        # Quantize the wobble so a stationary enemy reuses a few patch sizes.
        jq = round(jig * 4) / 4.0
        cw = max(1, int(rw * (1.0 + jq * 0.22)))   # Bulge wider on the bounce.
        ch = max(1, int(rh * (1.0 - jq * 0.10)))   # Squash a touch shorter.
        patch_s = pygame.transform.scale(patch, (cw, ch))
        # Anchor the patch's bottom-center where the chest's was, so it bounces.
        bx = left + rx + rw // 2
        by = top + ry + rh
        self.surface.blit(patch_s, (bx - cw // 2, by - ch))

    def _draw_particles(self, player, particle_system, dirx, diry, planex, planey):
        """Draw every particle as a small distance-scaled, occluded dot."""
        if particle_system is None:
            return
        W = config.RENDER_WIDTH
        H = config.RENDER_HEIGHT
        det = planex * diry - dirx * planey
        if abs(det) < 1e-9:
            return
        inv = 1.0 / det
        for pt in particle_system.particles:
            sx = pt.x - player.x
            sy = pt.y - player.y
            tX = inv * (diry * sx - dirx * sy)
            tY = inv * (-planey * sx + planex * sy)
            if tY <= 0.05:
                continue                      # Behind camera.
            screen_x = int((W / 2) * (1 + tX / tY))
            if screen_x < 0 or screen_x >= W:
                continue
            if tY >= self.zbuffer[screen_x]:
                continue                      # Behind a wall.
            # Vertical screen position from the particle's height fraction.
            full = H / tY                     # Full wall height at this depth.
            floor_y = self.horizon + full / 2
            py = int(floor_y - pt.h * full)
            # Size shrinks with distance; fade by life via a smaller radius.
            radius = max(1, int(pt.size * full * (pt.life / pt.max_life)))
            # Draw the dot (a couple of pixels), clipped to the surface.
            pygame.draw.circle(self.surface, pt.color, (screen_x, py), radius)

    # ----- public entry point ------------------------------------------------

    def render(self, target, player, level, sprite_list, particle_system=None):
        """Render the full 3D frame and blit it (scaled) onto `target`."""
        # Build the camera basis vectors from the player's facing angle.
        dirx = math.cos(player.angle)
        diry = math.sin(player.angle)
        planex = -math.sin(player.angle) * config.PLANE_LENGTH
        planey = math.cos(player.angle) * config.PLANE_LENGTH

        # Shift the horizon by the look pitch (vertical mouse-look), clamped so
        # there's always some floor and ceiling band to draw.
        base = config.RENDER_HEIGHT // 2
        pitch = int(getattr(player, "pitch", 0.0))
        self.horizon = max(24, min(config.RENDER_HEIGHT - 24, base + pitch))

        # Current animation frame index for animated wall textures (time-based).
        self._anim_idx = int(pygame.time.get_ticks() * 0.006)

        # 1) Textured floor + ceiling background.
        self._cast_floor_ceiling(player, level, dirx, diry, planex, planey)
        # 2) Textured walls over the background.
        self._cast_walls(player, level, dirx, diry, planex, planey)
        # 3) Sprites (enemies, pickups, projectiles) with z-buffer occlusion.
        self._draw_sprites(player, sprite_list, dirx, diry, planex, planey)
        # 4) Particles on top, also z-buffer occluded.
        self._draw_particles(player, particle_system, dirx, diry, planex, planey)

        # 5) Scale the finished low-res frame up to the window and blit it.
        pygame.transform.scale(self.surface, target.get_size(), target)
