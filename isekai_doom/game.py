"""game.py — the central state machine that wires the whole game together.

It owns the window, the main loop, and the high-level screens (title with
difficulty select, playing, paused, game over, victory). During play it
updates the player, enemies, projectiles (player + enemy), particles, doors,
pickups, and powerups; resolves melee/projectile/hitscan/beam combat; runs the
boss; shakes the screen; plays music; and hands everything to the raycaster +
HUD for drawing.
"""

import math               # Angle math for cones/hitscans.
import random             # Random spread, summon jitter, screen shake.
import pygame             # Windowing, events, timing.

from . import config      # Tunables.
from . import textures    # Wall + flat texture builders.
from . import sprites     # Sprite builders.
from . import audio       # Synthesized sound bank.
from . import maps        # Levels + catchphrases.
from .input import Input
from .player import Player
from .raycaster import Raycaster
from .weapon import WeaponSystem, Projectile
from .enemy import Enemy
from .particles import ParticleSystem
from .hud import HUD


class Game:
    """Creates everything once, then runs the main loop until the player quits."""

    def __init__(self):
        # Build the sound bank FIRST so its mixer pre_init runs before pygame.init.
        self.audio = audio.SoundBank()
        pygame.init()                                        # Init all subsystems.
        self.screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        pygame.display.set_caption("ISEKAI DOOM — Reborn in the Demon World")
        self.clock = pygame.time.Clock()

        # Synthesize sounds + music now that the mixer is up.
        self.audio.build()
        self.audio.build_music()

        # Build all assets (textures need the display to exist).
        self.textures = textures.build_textures()
        self.floors, self.ceils = textures.build_flats()
        self.enemy_sprite_sets = sprites.build_all_enemy_sprites()
        self.pickup_sprites = sprites.build_pickup_sprites()
        self.proj_sprites = sprites.build_projectile_sprites()

        # Core systems. Start the raycaster on level 1's theme.
        theme0 = config.LEVEL_THEMES[0]
        self.raycaster = Raycaster(self.textures, self.floors[theme0["floor"]], self.ceils[theme0["ceil"]])
        self.hud = HUD()
        self.input = Input()
        self.weapon = WeaponSystem(self.proj_sprites)
        self.player = Player(1.5, 1.5)
        self.particles = ParticleSystem()

        # An off-screen surface we render the world into so we can shake it.
        self.world_surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))

        # High-level state.
        self.state = "title"                                 # title|playing|paused|gameover|victory.
        self.level_index = 0
        self.level = None

        # Difficulty selection.
        self.difficulty_names = list(config.DIFFICULTIES.keys())
        self.menu_index = self.difficulty_names.index(config.DEFAULT_DIFFICULTY)
        self.difficulty = config.DIFFICULTIES[config.DEFAULT_DIFFICULTY]

        # Run stats.
        self.score = 0
        self.level_kills = 0
        self.level_total = 0
        self.total_kills = 0

        # Live entity lists.
        self.enemies = []
        self.projectiles = []          # Both player + enemy projectiles (owner-tagged).
        self.pickups = []
        self.boss = None               # Reference to the boss enemy, if any.
        self.boss_roared = False       # Whether the boss intro roar has played.

        # Door bookkeeping: per-cell "stay open" timers.
        self.door_timer = {}

        # Effects.
        self.message = ""
        self.message_timer = 0.0
        self.damage_flash = 0.0
        self.shake = 0.0               # Current screen-shake magnitude (pixels).

        # Misc.
        self.mouse_locked = False
        self.running = True

        # Start the menu music.
        self.audio.play_music("menu")

    # ----- messaging / effects ----------------------------------------------

    def set_message(self, text, seconds=2.0):
        """Show a banner message for a number of seconds."""
        self.message = text
        self.message_timer = seconds

    def add_shake(self, amount):
        """Add screen-shake magnitude (decays over time)."""
        self.shake = min(24.0, self.shake + amount)

    # ----- level + run setup -------------------------------------------------

    def load_level(self, index):
        """Load the level at `index`, spawning fresh entities + doors."""
        self.level_index = index
        self.level = maps.LEVELS[index]

        # Apply the level's visual theme to the raycaster.
        theme = config.LEVEL_THEMES[min(index, len(config.LEVEL_THEMES) - 1)]
        self.raycaster.set_theme(self.floors[theme["floor"]], self.ceils[theme["ceil"]], theme["fog"])

        # Reset the player to the start with difficulty-based health.
        sx, sy = self.level["start"]
        self.player.reset(sx, sy, self.difficulty["start_health"])

        # Keep the player's current weapon between levels, but refresh timers.
        self.weapon = WeaponSystem(self.proj_sprites)

        # Spawn enemies of each authored type with a random palette/look.
        self.enemies = []
        self.boss = None
        self.boss_roared = False
        for (etype, ex, ey) in self.level["enemies"]:
            sset = random.choice(self.enemy_sprite_sets[etype])
            e = Enemy(etype, ex, ey, sset, self.difficulty)
            self.enemies.append(e)
            if e.is_boss:
                self.boss = e
        self.level_total = sum(1 for e in self.enemies)
        self.level_kills = 0

        # Copy pickups so collecting them doesn't mutate the level data.
        self.pickups = [dict(p) for p in self.level["pickups"]]

        # Reset projectiles + particles + doors.
        self.projectiles = []
        self.particles.clear()
        self.level["door_frac"] = {cell: 0.0 for cell in self.level["doors"]}
        self.door_timer = {cell: 0.0 for cell in self.level["doors"]}

        self.set_message(self.level["name"], 3.0)
        # If this level has a boss, play a roar on entry.
        if self.boss is not None:
            self.audio.play("boss_roar")
            self.add_shake(10)

    def start_run(self):
        """Begin a fresh playthrough at the selected difficulty."""
        self.difficulty = config.DIFFICULTIES[self.difficulty_names[self.menu_index]]
        self.score = 0
        self.total_kills = 0
        self.load_level(0)
        self.state = "playing"
        self.lock_mouse(True)
        self.audio.play_music("battle")

    def quit_to_title(self):
        """Return to the title screen."""
        self.state = "title"
        self.lock_mouse(False)
        self.audio.play_music("menu")

    def lock_mouse(self, locked):
        """Capture or release the mouse pointer for mouse-look."""
        self.mouse_locked = locked
        pygame.event.set_grab(locked)
        pygame.mouse.set_visible(not locked)
        pygame.mouse.get_rel()                              # Flush the delta.

    # ----- spawning helpers (called by enemies) -----------------------------

    def spawn_enemy_projectile(self, x, y, angle, damage, kind):
        """Spawn an enemy projectile (caster heart / boss fireball)."""
        sx = x + math.cos(angle) * 0.5                      # Start just ahead of the enemy.
        sy = y + math.sin(angle) * 0.5
        surf = self.proj_sprites.get(kind, self.proj_sprites["heart"])
        color = (255, 120, 60) if kind == "fireball" else (255, 120, 180)
        radius = 0.4 if kind == "fireball" else config.ENEMY_PROJECTILE_RADIUS
        self.projectiles.append(Projectile(sx, sy, angle, config.ENEMY_PROJECTILE_SPEED,
                                           damage, radius, surf, "enemy", trail_color=color))

    def spawn_minion(self, etype, x, y):
        """Boss summon: spawn a minion at a nearby free tile, already aggroed."""
        # Try a few nearby offsets to find open floor.
        for ox, oy in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)]:
            tx, ty = int(x) + ox, int(y) + oy
            if 0 <= tx < self.level["width"] and 0 <= ty < self.level["height"] and self.level["grid"][ty][tx] == 0:
                sset = random.choice(self.enemy_sprite_sets[etype])
                e = Enemy(etype, tx + 0.5, ty + 0.5, sset, self.difficulty)
                e.aggroed = True                            # Immediately hostile.
                e.state = "chase"
                self.enemies.append(e)
                self.level_total += 1                       # Keep the counter consistent.
                return

    # ----- combat resolution -------------------------------------------------

    def register_kill(self, enemy):
        """Update score/kills and spawn a celebratory burst for a defeated foe."""
        self.score += int(enemy.score)
        self.level_kills += 1
        self.total_kills += 1
        self.player.kills += 1
        self.particles.kill_burst(enemy.x, enemy.y)
        if enemy.is_boss:
            self.set_message("THE DEMON QUEEN FALLS! To the exit!", 4.0)
            self.add_shake(16)
            self.audio.play("level_clear")
        elif self.level_kills >= self.level_total:
            self.set_message("Area cleared! Find the exit portal!", 3.0)

    def resolve_melee(self, descriptor):
        """Apply a melee cone hit (Holy Sword) to enemies in front of the player."""
        self.audio.play("sword")
        dmg = descriptor["damage"] * self.player.damage_multiplier()
        for e in self.enemies:
            if not e.alive:
                continue
            dx = e.x - self.player.x; dy = e.y - self.player.y
            dist = math.hypot(dx, dy)
            if dist > descriptor["range"] + e.radius:
                continue
            ang = math.atan2(dy, dx) - self.player.angle
            ang = (ang + math.pi) % (2 * math.pi) - math.pi
            if abs(ang) <= descriptor["arc"]:
                self.particles.blood(e.x, e.y)
                if e.hit(dmg, self.audio):
                    self.register_kill(e)

    def resolve_hitscan(self, descriptor, pierce=False):
        """Resolve a hitscan weapon (shotgun pellets / gatling / beam).

        Steps a ray per pellet; the first enemy along it takes damage (or every
        enemy if `pierce` is True, for the beam).
        """
        dmg = descriptor["damage"] * self.player.damage_multiplier()
        rng = descriptor["range"]
        pellets = descriptor.get("pellets", 1)
        spread = descriptor.get("spread", 0.0)
        for _ in range(pellets):
            ang = self.player.angle + random.uniform(-spread, spread)
            rdx, rdy = math.cos(ang), math.sin(ang)
            hit_enemies = set()
            cx, cy = self.player.x, self.player.y
            steps = int(rng / 0.08)
            for _s in range(steps):
                cx += rdx * 0.08; cy += rdy * 0.08
                gx, gy = int(cx), int(cy)
                # Stop at a wall (open doors don't block).
                if gx < 0 or gy < 0 or gx >= self.level["width"] or gy >= self.level["height"]:
                    break
                tile = self.level["grid"][gy][gx]
                if tile != 0 and not (tile == config.TEX_DOOR and self.level["door_frac"].get((gx, gy), 0) >= 1.0):
                    self.particles.sparks(cx, cy)
                    break
                # Check enemies near this ray point.
                for e in self.enemies:
                    if not e.alive or id(e) in hit_enemies:
                        continue
                    if math.hypot(e.x - cx, e.y - cy) <= e.radius:
                        hit_enemies.add(id(e))
                        self.particles.blood(e.x, e.y)
                        if e.hit(dmg, self.audio):
                            self.register_kill(e)
                        if not pierce:
                            break
                if hit_enemies and not pierce:
                    break

    def update_projectiles(self, dt):
        """Advance every projectile and resolve wall/enemy/player collisions."""
        survivors = []
        for p in self.projectiles:
            p.update(dt, self.level)
            # Leave a glowing trail.
            if p.trail_color:
                self.particles.trail(p.x, p.y, p.trail_color)
            if not p.alive:
                self.particles.sparks(p.x, p.y, p.trail_color or (255, 230, 120))
                continue
            hit = False
            if p.owner == "player":
                dmg = p.damage * self.player.damage_multiplier()
                for e in self.enemies:
                    if not e.alive:
                        continue
                    if math.hypot(e.x - p.x, e.y - p.y) <= p.radius + e.radius:
                        self.particles.blood(e.x, e.y)
                        if e.hit(dmg, self.audio):
                            self.register_kill(e)
                        hit = True
                        break
            else:  # enemy projectile -> can hurt the player.
                if math.hypot(self.player.x - p.x, self.player.y - p.y) <= p.radius + config.PLAYER_RADIUS:
                    self.player.take_damage(p.damage)
                    self.particles.sparks(p.x, p.y, p.trail_color)
                    hit = True
            if not hit:
                survivors.append(p)
        self.projectiles = survivors

    def update_pickups(self):
        """Auto-collect pickups; apply health/mana/armor/ammo/powerup effects."""
        remaining = []
        for p in self.pickups:
            if math.hypot(p["x"] - self.player.x, p["y"] - self.player.y) <= config.PICKUP_RADIUS:
                self._apply_pickup(p["kind"])
            else:
                remaining.append(p)
        self.pickups = remaining

    def _apply_pickup(self, kind):
        """Apply one collected pickup of the given kind."""
        if kind == "health":
            self.player.heal(config.PICKUP_HEALTH_AMOUNT); self.set_message("+HP  Genki restored!", 1.4); self.audio.play("pickup")
        elif kind == "mana":
            self.player.add_mana(config.PICKUP_MANA_AMOUNT); self.set_message("+MP  Mana restored!", 1.4); self.audio.play("pickup")
        elif kind == "armor":
            self.player.add_armor(config.PICKUP_ARMOR_AMOUNT); self.set_message("+ARMOR", 1.4); self.audio.play("pickup")
        elif kind in ("shells", "rounds", "energy"):
            amt = int(config.AMMO_PICKUP[kind] * self.difficulty["ammo_mult"])
            self.player.add_ammo(kind, amt); self.set_message("+{} {}".format(amt, kind.upper()), 1.4); self.audio.play("pickup")
        elif kind == "quad":
            self.player.quad_timer = config.POWERUP_QUAD_DURATION; self.set_message("QUAD DAMAGE!", 2.0); self.audio.play("powerup"); self.add_shake(6)
        elif kind == "haste":
            self.player.haste_timer = config.POWERUP_HASTE_DURATION; self.set_message("HASTE!", 2.0); self.audio.play("powerup")
        elif kind == "shield":
            self.player.shield_timer = config.POWERUP_SHIELD_DURATION; self.set_message("DIVINE SHIELD!", 2.0); self.audio.play("powerup")

    def update_doors(self, dt):
        """Open doors the player approaches; close them again after a delay."""
        door_frac = self.level["door_frac"]
        for cell in self.level["doors"]:
            cx, cy = cell[0] + 0.5, cell[1] + 0.5
            dist = math.hypot(self.player.x - cx, self.player.y - cy)
            opening = dist <= config.DOOR_OPEN_RANGE
            if opening:
                self.door_timer[cell] = config.DOOR_STAY_OPEN          # Keep it open.
                target = 1.0
            else:
                self.door_timer[cell] = max(0.0, self.door_timer[cell] - dt)
                target = 1.0 if self.door_timer[cell] > 0 else 0.0
            frac = door_frac[cell]
            if target > frac:
                if frac < 0.02:                                        # Just starting to open.
                    self.audio.play("door")
                door_frac[cell] = min(1.0, frac + config.DOOR_SPEED * dt)
            elif target < frac:
                door_frac[cell] = max(0.0, frac - config.DOOR_SPEED * dt)

    def check_exit(self):
        """Advance to the next level (or win) if standing on the exit tile."""
        gx, gy = int(self.player.x), int(self.player.y)
        if self.level["grid"][gy][gx] == config.TEX_EXIT:
            self.audio.play("level_clear")
            if self.level_index + 1 < len(maps.LEVELS):
                self.load_level(self.level_index + 1)
            else:
                self.state = "victory"
                self.lock_mouse(False)
                self.audio.play_music("menu")

    # ----- per-state updates -------------------------------------------------

    def update_playing(self, dt):
        """Advance one frame of actual gameplay."""
        self.input.poll(self.mouse_locked)

        # Move/turn the player.
        self.player.just_hurt = False
        self.player.update(dt, self.input, self.level)

        # Weapon timers + bob (bob only while walking).
        self.weapon.update(dt, getattr(self.player, "moving", False))

        # Fire if the control is held and allowed.
        if self.input.fire:
            result = self.weapon.try_fire(self.player)
            if result == ("noammo", None):
                self.audio.play("no_ammo")
            elif isinstance(result, dict):
                kind = result["kind"]
                if kind == "melee":
                    self.resolve_melee(result)
                elif kind == "projectile":
                    self.projectiles.append(result["proj"]); self.audio.play("bolt")
                elif kind == "hitscan":
                    cur = self.weapon.current
                    self.resolve_hitscan(result)
                    self.audio.play("shotgun" if cur == "shotgun" else "gatling")
                    if cur == "shotgun":
                        self.add_shake(7)
                elif kind == "beam":
                    self.resolve_hitscan(result, pierce=True)
                    self.audio.play("beam"); self.add_shake(10)

        # Update enemies (they may damage the player or spawn projectiles/minions).
        for e in self.enemies:
            e.update(dt, self.player, self.level, self)
            if e.shout:
                self.set_message(e.shout, 1.2)
                e.shout = None

        # Boss intro roar the first time it wakes.
        if self.boss is not None and self.boss.aggroed and not self.boss_roared:
            self.boss_roared = True
            self.audio.play("boss_roar"); self.add_shake(12)
            self.set_message("THE DEMON QUEEN AWAKENS!", 3.0)

        # Projectiles, particles, pickups, doors, exit.
        self.update_projectiles(dt)
        self.particles.update(dt)
        self.update_pickups()
        self.update_doors(dt)
        self.check_exit()

        # React to the player taking damage this frame.
        if self.player.just_hurt:
            self.damage_flash = 0.3
            self.add_shake(6)
            self.audio.play("hurt")

        # Decay timers.
        if self.message_timer > 0:
            self.message_timer = max(0.0, self.message_timer - dt)
        if self.damage_flash > 0:
            self.damage_flash = max(0.0, self.damage_flash - dt)
        if self.shake > 0:
            self.shake = max(0.0, self.shake - config.SCREEN_SHAKE_DECAY * dt)

        # Player death.
        if self.player.dead:
            self.audio.play("death")
            self.state = "gameover"
            self.lock_mouse(False)
            self.audio.play_music("menu")

    # ----- sprite gathering --------------------------------------------------

    def build_sprite_list(self):
        """Collect every billboard (enemies, pickups, projectiles) for the renderer."""
        out = []
        for e in self.enemies:
            surf, vscale = e.current_sprite()
            out.append({"x": e.x, "y": e.y, "surf": surf, "vscale": vscale})
        for p in self.pickups:
            vs = 0.6 if p["kind"] in ("quad", "haste", "shield") else 0.5
            out.append({"x": p["x"], "y": p["y"], "surf": self.pickup_sprites[p["kind"]], "vscale": vs})
        for pr in self.projectiles:
            out.append({"x": pr.x, "y": pr.y, "surf": pr.surf, "vscale": 0.35})
        return out

    # ----- event handling ----------------------------------------------------

    def handle_events(self):
        """Process discrete (one-shot) events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            # Mouse wheel cycles weapons while playing.
            if event.type == pygame.MOUSEWHEEL and self.state == "playing":
                self.weapon.cycle(1 if event.y < 0 else -1)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:
                    muted = self.audio.toggle_mute()
                    self.set_message("Muted" if muted else "Unmuted", 1.0)

                if self.state == "title":
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.menu_index = (self.menu_index - 1) % len(self.difficulty_names)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.menu_index = (self.menu_index + 1) % len(self.difficulty_names)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.start_run()

                elif self.state == "playing":
                    if event.key == pygame.K_ESCAPE:
                        self.state = "paused"; self.lock_mouse(False)
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                        slot = event.key - pygame.K_0          # Map key to slot number.
                        self.weapon.switch_slot(slot)

                elif self.state == "paused":
                    if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                        self.state = "playing"; self.lock_mouse(True)
                    elif event.key == pygame.K_r:
                        self.load_level(self.level_index); self.state = "playing"; self.lock_mouse(True); self.audio.play_music("battle")
                    elif event.key == pygame.K_t:
                        self.quit_to_title()

                elif self.state == "gameover":
                    if event.key == pygame.K_RETURN:
                        self.start_run()

                elif self.state == "victory":
                    if event.key == pygame.K_RETURN:
                        self.start_run()

    # ----- rendering ---------------------------------------------------------

    def render(self):
        """Draw the appropriate screen for the current state."""
        if self.state in ("playing", "paused"):
            # Render the world (+ weapon) into the off-screen surface so we can shake it.
            sprite_list = self.build_sprite_list()
            self.raycaster.render(self.world_surface, self.player, self.level, sprite_list, self.particles)
            self.weapon.draw_viewmodel(self.world_surface)
            # Apply screen shake by blitting the world at a random small offset.
            ox = random.uniform(-self.shake, self.shake)
            oy = random.uniform(-self.shake, self.shake)
            self.screen.fill((0, 0, 0))
            self.screen.blit(self.world_surface, (ox, oy))
            # HUD on top (steady).
            self.hud.draw_hud(self.screen, {
                "player": self.player,
                "weapon_name": self.weapon.display_name(),
                "weapon_current": self.weapon.current,
                "score": self.score,
                "kills": self.level_kills,
                "total_enemies": self.level_total,
                "level_name": self.level["name"],
                "message": self.message,
                "message_timer": self.message_timer,
                "damage_flash": self.damage_flash,
                "level": self.level,
                "enemies": self.enemies,
                "pickups": self.pickups,
                "boss": self.boss,
            })
            if self.state == "paused":
                self.hud.draw_pause(self.screen)

        elif self.state == "title":
            self.screen.fill((8, 3, 6))
            self.hud.draw_title(self.screen, self.difficulty_names, self.menu_index)

        elif self.state == "gameover":
            stats = "Score {}   Demon-girls defeated {}".format(self.score, self.total_kills)
            self.hud.draw_gameover(self.screen, stats)

        elif self.state == "victory":
            stats = "Score {}   Demon-girls defeated {}".format(self.score, self.total_kills)
            self.hud.draw_victory(self.screen, stats)

        pygame.display.flip()

    # ----- main loop ----------------------------------------------------------

    def run(self):
        """The main loop: events -> update -> render, capped to TARGET_FPS."""
        while self.running:
            dt = self.clock.tick(config.TARGET_FPS) / 1000.0
            dt = min(dt, config.MAX_DELTA)
            self.handle_events()
            if self.state == "playing":
                self.update_playing(dt)
            self.render()
        pygame.quit()
