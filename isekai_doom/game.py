"""game.py — the central state machine that wires the whole game together.

It owns the window, the main loop, and the high-level "screens" (title,
playing, paused, game over, victory). During play it updates the player,
enemies, projectiles, and pickups, resolves combat, advances levels, and
hands everything to the raycaster + HUD for drawing.
"""

import math               # Angle math for the sword arc.
import random             # Random enemy appearances.
import pygame             # Windowing, events, timing.

from . import config      # Tunables.
from . import textures    # Wall texture builder.
from . import sprites     # Sprite builders.
from . import audio       # Synthesized sound bank.
from . import maps        # Levels + catchphrases.
from .input import Input          # Keyboard/mouse abstraction.
from .player import Player        # The hero.
from .raycaster import Raycaster  # 3D renderer.
from .weapon import WeaponSystem  # Weapons + projectiles.
from .enemy import Enemy          # Demon-girl AI.
from .hud import HUD              # On-screen UI.


class Game:
    """Creates everything once, then runs the main loop until the player quits."""

    def __init__(self):
        # Build the sound bank FIRST so its mixer pre_init runs before pygame.init.
        self.audio = audio.SoundBank()
        # Initialize all of pygame's subsystems.
        pygame.init()
        # Create the game window at the configured size.
        self.screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        # Set the window title bar text.
        pygame.display.set_caption("ISEKAI DOOM — Reborn in the Demon World")
        # A clock to cap the frame rate and measure delta-time.
        self.clock = pygame.time.Clock()

        # Synthesize all sound effects now that the mixer is up.
        self.audio.build()

        # Build wall textures (needs the display to exist for Surface conversion).
        self.textures = textures.build_textures()
        # Build the per-palette demon-girl animation sets.
        self.enemy_sprite_sets = sprites.build_enemy_sprite_sets()
        # Build the health/mana pickup sprites.
        self.pickup_sprites = sprites.build_pickup_sprites()
        # Build the single Spirit Bolt projectile sprite.
        self.bolt_sprite = sprites.build_bolt_sprite()

        # The 3D renderer.
        self.raycaster = Raycaster(self.textures)
        # The 2D HUD / menus.
        self.hud = HUD()
        # The input abstraction.
        self.input = Input()
        # The weapon system, given the bolt sprite for projectiles.
        self.weapon = WeaponSystem(self.bolt_sprite)
        # The player (positioned properly when a level loads).
        self.player = Player(1.5, 1.5)

        # High-level game state: "title" | "playing" | "paused" | "gameover" | "victory".
        self.state = "title"
        # Index of the current level within maps.LEVELS.
        self.level_index = 0
        # The active level dict (set by load_level).
        self.level = None

        # Per-run score and total kills.
        self.score = 0
        # Kills in the current level vs the level's total enemy count.
        self.level_kills = 0
        self.level_total = 0
        # Lifetime kills across the whole run (for the end stats).
        self.total_kills = 0

        # Live entity lists for the current level.
        self.enemies = []        # Enemy objects.
        self.pickups = []        # Pickup dicts {x, y, type}.
        self.projectiles = []    # In-flight Spirit Bolts.

        # Transient on-screen message banner + its remaining time.
        self.message = ""
        self.message_timer = 0.0
        # Remaining time for the red damage-flash overlay.
        self.damage_flash = 0.0

        # Whether the mouse is captured for mouse-look.
        self.mouse_locked = False
        # The main loop runs while this stays True.
        self.running = True

    # ----- level + run setup -------------------------------------------------

    def set_message(self, text, seconds=2.0):
        """Show a banner message for a number of seconds."""
        self.message = text              # Store the text.
        self.message_timer = seconds     # Reset its countdown.

    def load_level(self, index):
        """Load the level at `index`, spawning fresh enemies and pickups."""
        # Remember which level we're on.
        self.level_index = index
        # Grab the level dict (grid is shared read-only; entities are copied).
        self.level = maps.LEVELS[index]
        # Move the player to the level's start and refill vitals.
        sx, sy = self.level["start"]
        self.player.reset(sx, sy)
        # Reset the weapon to the sword with no leftover cooldown.
        self.weapon = WeaponSystem(self.bolt_sprite)

        # Spawn an Enemy for each authored demon spawn, with a random look.
        self.enemies = [
            Enemy(ex, ey, random.choice(self.enemy_sprite_sets))
            for (ex, ey) in self.level["enemies"]
        ]
        # Track how many demons this level has and reset the level kill count.
        self.level_total = len(self.enemies)
        self.level_kills = 0

        # Copy the pickup list so collecting one doesn't mutate the level data.
        self.pickups = [dict(p) for p in self.level["pickups"]]
        # No projectiles carry over between levels.
        self.projectiles = []

        # Announce the level.
        self.set_message(self.level["name"], 3.0)

    def start_run(self):
        """Begin a fresh playthrough from the first level."""
        self.score = 0               # Reset score.
        self.total_kills = 0         # Reset lifetime kills.
        self.load_level(0)           # Load the first level.
        self.state = "playing"       # Enter the playing state.
        self.lock_mouse(True)        # Capture the mouse for looking.

    def lock_mouse(self, locked):
        """Capture or release the mouse pointer for mouse-look."""
        self.mouse_locked = locked                  # Remember the state.
        pygame.event.set_grab(locked)               # Confine/free the pointer.
        pygame.mouse.set_visible(not locked)        # Hide cursor while captured.
        # Reset the relative-motion accumulator so we don't get a jump.
        pygame.mouse.get_rel()

    # ----- combat resolution -------------------------------------------------

    def register_kill(self):
        """Update score/kill counters when a demon-girl is defeated."""
        self.score += config.ENEMY_SCORE   # Award points.
        self.level_kills += 1              # Count toward this level.
        self.total_kills += 1              # Count toward the run total.
        self.player.kills += 1             # Track on the player too.
        # If every demon in the level is down, nudge the player toward the exit.
        if self.level_kills >= self.level_total:
            self.set_message("Area cleared! Find the exit portal!", 3.0)

    def resolve_sword(self):
        """Apply the Holy Sword's cone hit to enemies in front of the player."""
        # Play the swing sound regardless of whether we connect.
        self.audio.play("sword")
        # Test every living enemy against the reach + arc cone.
        for e in self.enemies:
            if not e.alive:
                continue                       # Skip already-fainted girls.
            # Vector + distance from player to this enemy.
            dx = e.x - self.player.x
            dy = e.y - self.player.y
            dist = math.hypot(dx, dy)
            # Too far away to reach with the blade?
            if dist > config.SWORD_RANGE:
                continue
            # Angle from the player's facing to the enemy.
            ang = math.atan2(dy, dx) - self.player.angle
            ang = (ang + math.pi) % (2 * math.pi) - math.pi   # Wrap to (-pi, pi].
            # Only hit enemies inside the swing's half-arc.
            if abs(ang) <= config.SWORD_ARC:
                # Deal damage; if it kills her, score it.
                if e.hit(config.SWORD_DAMAGE, self.audio):
                    self.register_kill()

    def update_projectiles(self, dt):
        """Advance bolts, resolve wall + enemy collisions, and cull dead ones."""
        survivors = []                         # Bolts that are still alive after this tick.
        for p in self.projectiles:
            # Move the bolt and check for wall collisions.
            p.update(dt, self.level)
            if not p.alive:
                self.audio.play("impact")      # Wall splash sound.
                continue                       # Drop this bolt.
            # Check the bolt against every living enemy.
            hit = False
            for e in self.enemies:
                if not e.alive:
                    continue                   # Skip fainted girls.
                # Distance from the bolt to the enemy center.
                if math.hypot(e.x - p.x, e.y - p.y) <= config.BOLT_RADIUS + config.ENEMY_RADIUS:
                    # Apply bolt damage; score if it kills.
                    if e.hit(config.BOLT_DAMAGE, self.audio):
                        self.register_kill()
                    hit = True                 # The bolt is spent.
                    break                      # One bolt hits one enemy.
            # Keep the bolt only if it didn't hit anything this tick.
            if not hit:
                survivors.append(p)
        # Replace the list with the survivors.
        self.projectiles = survivors

    def update_pickups(self):
        """Auto-collect any pickup the player is standing close to."""
        remaining = []                         # Pickups not yet collected.
        for p in self.pickups:
            # Distance from the player to the pickup.
            if math.hypot(p["x"] - self.player.x, p["y"] - self.player.y) <= config.PICKUP_RADIUS:
                # Apply the pickup's effect based on its type.
                if p["type"] == "health":
                    self.player.heal(config.PICKUP_HEALTH_AMOUNT)
                    self.set_message("+HP  Genki restored!", 1.5)
                else:
                    self.player.add_mana(config.PICKUP_MANA_AMOUNT)
                    self.set_message("+MP  Mana restored!", 1.5)
                self.audio.play("pickup")      # Cheerful chime.
            else:
                remaining.append(p)            # Keep uncollected pickups.
        self.pickups = remaining

    def check_exit(self):
        """If the player is standing on an exit tile, advance or win."""
        gx, gy = int(self.player.x), int(self.player.y)   # Player's grid cell.
        # Is that cell the exit-portal texture?
        if self.level["grid"][gy][gx] == config.TEX_EXIT:
            self.audio.play("level_clear")     # Fanfare.
            # If there are more levels, load the next one.
            if self.level_index + 1 < len(maps.LEVELS):
                self.load_level(self.level_index + 1)
            else:
                # Otherwise the run is won.
                self.state = "victory"
                self.lock_mouse(False)

    # ----- per-state updates -------------------------------------------------

    def update_playing(self, dt):
        """Advance one frame of actual gameplay."""
        # Refresh input flags (consuming mouse motion only while captured).
        self.input.poll(self.mouse_locked)

        # Remember health so we can detect when the player just took damage.
        prev_health = self.player.health

        # Move/turn the player and regen mana.
        self.player.update(dt, self.input, self.level)

        # Tick weapon cooldown/animation timers.
        self.weapon.update(dt)
        # If the fire control is held and we're allowed to shoot, do it.
        if self.input.fire:
            result = self.weapon.try_fire(self.player)
            if result:                          # Something actually fired.
                kind, payload = result
                if kind == "sword":
                    self.resolve_sword()        # Resolve the melee cone.
                elif kind == "bolt":
                    self.projectiles.append(payload)  # Track the new bolt.
                    self.audio.play("bolt")     # Cast sound.

        # Update every enemy's AI (they may hurt the player here).
        for e in self.enemies:
            e.update(dt, self.player, self.level, self.audio)
            # If she shouted this frame, surface it as a banner and clear it.
            if e.shout:
                self.set_message(e.shout, 1.2)
                e.shout = None

        # Advance bolts and resolve their collisions.
        self.update_projectiles(dt)
        # Collect any pickups underfoot.
        self.update_pickups()
        # Check for the level exit.
        self.check_exit()

        # If health dropped this frame, flash red and play the hurt sound.
        if self.player.health < prev_health:
            self.damage_flash = 0.3
            self.audio.play("hurt")

        # Tick down the message banner timer.
        if self.message_timer > 0:
            self.message_timer = max(0.0, self.message_timer - dt)
        # Tick down the damage-flash timer.
        if self.damage_flash > 0:
            self.damage_flash = max(0.0, self.damage_flash - dt)

        # Did the player die this frame? Transition to the game-over screen.
        if self.player.dead:
            self.audio.play("death")
            self.state = "gameover"
            self.lock_mouse(False)

    # ----- sprite gathering --------------------------------------------------

    def build_sprite_list(self):
        """Collect every billboard (enemies, pickups, bolts) for the renderer."""
        out = []                                # The list we hand to the raycaster.
        # Add each enemy with its current animation frame.
        for e in self.enemies:
            surf, vscale = e.current_sprite()
            out.append({"x": e.x, "y": e.y, "surf": surf, "vscale": vscale})
        # Add each pickup, floating a bit shorter than a wall.
        for p in self.pickups:
            out.append({"x": p["x"], "y": p["y"],
                        "surf": self.pickup_sprites[p["type"]], "vscale": 0.5})
        # Add each in-flight bolt as a small glowing orb.
        for pr in self.projectiles:
            out.append({"x": pr.x, "y": pr.y, "surf": pr.surf, "vscale": 0.3})
        return out

    # ----- event handling ----------------------------------------------------

    def handle_events(self):
        """Process discrete (one-shot) events: quitting, key presses, etc."""
        for event in pygame.event.get():
            # The window's close button or Alt+F4.
            if event.type == pygame.QUIT:
                self.running = False
                return
            # Only react to key-DOWN edges here (held keys are polled elsewhere).
            if event.type == pygame.KEYDOWN:
                # Global mute toggle works in any state.
                if event.key == pygame.K_m:
                    muted = self.audio.toggle_mute()
                    self.set_message("Muted" if muted else "Unmuted", 1.0)

                # State-specific key handling.
                if self.state == "title":
                    # Enter / Space starts the run.
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.start_run()

                elif self.state == "playing":
                    if event.key == pygame.K_ESCAPE:
                        # Pause and release the mouse.
                        self.state = "paused"
                        self.lock_mouse(False)
                    elif event.key == pygame.K_1:
                        self.weapon.switch("sword")     # Equip the Holy Sword.
                    elif event.key == pygame.K_2:
                        self.weapon.switch("bolt")      # Equip the Spirit Bolt.

                elif self.state == "paused":
                    if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                        # Resume and recapture the mouse.
                        self.state = "playing"
                        self.lock_mouse(True)
                    elif event.key == pygame.K_r:
                        # Restart the current level from scratch.
                        self.load_level(self.level_index)
                        self.state = "playing"
                        self.lock_mouse(True)

                elif self.state == "gameover":
                    if event.key == pygame.K_RETURN:
                        # Start a brand-new run.
                        self.start_run()

                elif self.state == "victory":
                    if event.key == pygame.K_RETURN:
                        # Play again from the start.
                        self.start_run()

    # ----- rendering ---------------------------------------------------------

    def render(self):
        """Draw the appropriate screen for the current state."""
        if self.state in ("playing", "paused"):
            # Draw the 3D world from the player's eyes.
            sprite_list = self.build_sprite_list()
            self.raycaster.render(self.screen, self.player, self.level, sprite_list)
            # Draw the first-person weapon over the world.
            self.weapon.draw_viewmodel(self.screen)
            # Draw the HUD on top, using a snapshot of the relevant state.
            self.hud.draw_hud(self.screen, {
                "player": self.player,
                "weapon_name": self.weapon.display_name(),
                "score": self.score,
                "kills": self.level_kills,
                "total_enemies": self.level_total,
                "level_name": self.level["name"],
                "message": self.message,
                "message_timer": self.message_timer,
                "damage_flash": self.damage_flash,
            })
            # If paused, dim everything and draw the pause menu over the frame.
            if self.state == "paused":
                self.hud.draw_pause(self.screen)

        elif self.state == "title":
            # Solid dark background then the title overlay.
            self.screen.fill((8, 3, 6))
            self.hud.draw_title(self.screen)

        elif self.state == "gameover":
            # Keep the last 3D frame visible underneath the overlay for context.
            stats = "Score {}   Demon-girls defeated {}".format(self.score, self.total_kills)
            self.hud.draw_gameover(self.screen, stats)

        elif self.state == "victory":
            # Show the victory overlay with final stats.
            stats = "Score {}   Demon-girls defeated {}".format(self.score, self.total_kills)
            self.hud.draw_victory(self.screen, stats)

        # Flip the back buffer to the screen (show what we drew).
        pygame.display.flip()

    # ----- main loop ----------------------------------------------------------

    def run(self):
        """The main game loop: events -> update -> render, capped to TARGET_FPS."""
        while self.running:
            # Advance the clock and get the elapsed time in seconds.
            dt = self.clock.tick(config.TARGET_FPS) / 1000.0
            # Clamp dt so a hitch (e.g. window drag) can't teleport entities.
            dt = min(dt, config.MAX_DELTA)

            # Handle discrete input + window events.
            self.handle_events()

            # Update simulation only while actively playing.
            if self.state == "playing":
                self.update_playing(dt)

            # Draw the current state.
            self.render()

        # Clean up pygame on exit.
        pygame.quit()
