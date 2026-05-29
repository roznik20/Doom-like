"""config.py — every tunable constant for ISEKAI DOOM lives here.

Keeping the numbers in one place means you can rebalance the whole game
(difficulty, speed, look, weapons, enemies, powerups) without hunting through
the engine code. This file grew a lot when the game was "maximized": it now
also defines difficulty scaling, weapon stats, powerups, armor, ammo, doors,
the minimap, screen shake, and per-theme colors.
"""

import math  # We need pi for the field-of-view, expressed in radians.

# ----------------------------------------------------------------------------
# Window + internal rendering resolution
# ----------------------------------------------------------------------------
# The actual on-screen window size in pixels (what the player sees).
WINDOW_WIDTH = 1024           # Window width in pixels.
WINDOW_HEIGHT = 576           # Window height in pixels (16:9 with the width).

# We render the 3D world at a LOWER internal resolution for speed, then scale
# it up to the window. This gives a crisp retro look AND keeps the pure-Python
# raycaster fast enough for smooth play.
NUM_RAYS = 512                # One ray (and one wall column) per internal pixel-column.
RENDER_HEIGHT = 288           # Internal vertical resolution of the 3D view.
RENDER_WIDTH = NUM_RAYS       # Internal horizontal resolution equals the ray count.

# ----------------------------------------------------------------------------
# Camera / field of view
# ----------------------------------------------------------------------------
FOV = math.pi / 3             # Field of view: 60 degrees expressed in radians.
HALF_FOV = FOV / 2            # Half the FOV, used to build the camera plane.
# The camera "plane" half-length. With the standard dir+plane raycaster model,
# a plane length of tan(HALF_FOV) reproduces our desired field of view.
PLANE_LENGTH = math.tan(HALF_FOV)

# ----------------------------------------------------------------------------
# Frame timing
# ----------------------------------------------------------------------------
TARGET_FPS = 60              # The frame rate we cap the game at.
MAX_DELTA = 0.05             # Clamp per-frame delta-time (seconds) to avoid physics jumps.

# ----------------------------------------------------------------------------
# Player movement
# ----------------------------------------------------------------------------
MOVE_SPEED = 3.2             # Walking speed in map tiles per second.
SPRINT_MULTIPLIER = 1.8      # Sprinting speed multiplier (hold Shift).
TURN_SPEED = 2.8             # Keyboard turn speed in radians per second.
MOUSE_SENSITIVITY = 0.0022   # Radians turned per pixel of horizontal mouse motion.
PLAYER_RADIUS = 0.22         # Collision radius so the player can't slide into walls.
PLAYER_HEIGHT = 0.5          # Eye height fraction (0.5 = halfway up the wall).

# ----------------------------------------------------------------------------
# Player vitals + armor
# ----------------------------------------------------------------------------
MAX_HEALTH = 100             # Starting + maximum health.
MAX_MANA = 100               # Starting + maximum mana (fuel for Spirit Bolts/Beam).
MANA_REGEN = 7.0             # Mana regenerated per second.
MAX_ARMOR = 100              # Maximum armor points.
ARMOR_ABSORB = 0.5           # Fraction of incoming damage soaked by armor (when you have it).

# ----------------------------------------------------------------------------
# Difficulty presets — chosen on the title screen. Each scales enemy threat
# and starting resources. Keys map to a dict of multipliers/values.
# ----------------------------------------------------------------------------
DIFFICULTIES = {
    "Isekai Tutorial": {           # Easiest: forgiving for first-timers.
        "enemy_damage": 0.6,        # Enemies hit softer.
        "enemy_health": 0.8,        # Enemies die faster.
        "enemy_speed": 0.85,        # Enemies move slower.
        "enemy_fire_rate": 0.7,     # Enemies shoot less often.
        "ammo_mult": 1.5,           # More ammo from pickups.
        "start_health": 100,        # Full start health.
    },
    "Reborn Hero": {                # Normal balance.
        "enemy_damage": 1.0,
        "enemy_health": 1.0,
        "enemy_speed": 1.0,
        "enemy_fire_rate": 1.0,
        "ammo_mult": 1.0,
        "start_health": 100,
    },
    "Demon Lord": {                 # Hard: aggressive, tanky enemies.
        "enemy_damage": 1.5,
        "enemy_health": 1.35,
        "enemy_speed": 1.2,
        "enemy_fire_rate": 1.4,
        "ammo_mult": 0.8,
        "start_health": 80,
    },
    "Nightmare Goddess": {          # Brutal: for masochists.
        "enemy_damage": 2.2,
        "enemy_health": 1.7,
        "enemy_speed": 1.4,
        "enemy_fire_rate": 1.8,
        "ammo_mult": 0.7,
        "start_health": 60,
    },
}
# The default difficulty key if the player just presses start.
DEFAULT_DIFFICULTY = "Reborn Hero"

# ----------------------------------------------------------------------------
# Weapons — stats are read by weapon.py. Each weapon has its own behavior kind.
#   kind "melee"   -> instant cone hit
#   kind "projectile" -> spawns a travelling orb (player Projectile)
#   kind "hitscan" -> instant ray; may fire several pellets with spread
#   kind "beam"    -> piercing instant ray that hits everything in a line
# ----------------------------------------------------------------------------
WEAPONS = {
    "sword": {
        "name": "HOLY SWORD",       # HUD label.
        "kind": "melee",            # Behavior type.
        "damage": 50,               # Damage per hit.
        "range": 1.6,               # Reach in tiles.
        "arc": 0.7,                 # Half-angle of the swing cone (radians).
        "cooldown": 0.38,           # Seconds between swings.
        "ammo": None,               # None = no ammo (always usable).
        "anim_len": 0.30,           # View-model animation length.
        "slot": 1,                  # Number key that selects it.
    },
    "bolt": {
        "name": "SPIRIT BOLT",
        "kind": "projectile",
        "damage": 65,
        "speed": 9.0,               # Projectile speed (tiles/sec).
        "cooldown": 0.30,
        "ammo": "mana",             # Spends mana.
        "ammo_cost": 16,
        "radius": 0.35,             # Projectile collision radius.
        "anim_len": 0.25,
        "slot": 2,
    },
    "shotgun": {
        "name": "SERAPH SHOTGUN",
        "kind": "hitscan",
        "damage": 18,               # Damage PER pellet.
        "pellets": 7,               # Pellets per shot.
        "spread": 0.18,             # Random angular spread per pellet (radians).
        "range": 10.0,              # Max hitscan range.
        "cooldown": 0.75,
        "ammo": "shells",           # Uses shotgun shells.
        "ammo_cost": 1,
        "anim_len": 0.35,
        "slot": 3,
    },
    "gatling": {
        "name": "ROSARY GATLING",
        "kind": "hitscan",
        "damage": 14,
        "pellets": 1,
        "spread": 0.05,             # A little inaccuracy.
        "range": 14.0,
        "cooldown": 0.08,           # Very fast fire rate.
        "ammo": "rounds",
        "ammo_cost": 1,
        "anim_len": 0.08,
        "slot": 4,
    },
    "beam": {
        "name": "GODDESS BEAM",
        "kind": "beam",
        "damage": 50,               # Damage to EVERY enemy along the beam.
        "range": 18.0,
        "cooldown": 0.9,
        "ammo": "energy",
        "ammo_cost": 5,
        "anim_len": 0.45,
        "slot": 5,
    },
}
# The order weapons appear in the HUD list / get cycled with the mouse wheel.
WEAPON_ORDER = ["sword", "bolt", "shotgun", "gatling", "beam"]

# ----------------------------------------------------------------------------
# Ammunition — starting amounts and per-type maximums.
# ----------------------------------------------------------------------------
START_AMMO = {"shells": 12, "rounds": 60, "energy": 20}   # What you begin with.
MAX_AMMO = {"shells": 60, "rounds": 300, "energy": 100}   # Hard caps per type.
# How much each ammo pickup grants (before the difficulty ammo multiplier).
AMMO_PICKUP = {"shells": 8, "rounds": 40, "energy": 12}

# ----------------------------------------------------------------------------
# Pickups
# ----------------------------------------------------------------------------
PICKUP_HEALTH_AMOUNT = 25    # Health restored by a health potion.
PICKUP_MANA_AMOUNT = 35      # Mana restored by a mana crystal.
PICKUP_ARMOR_AMOUNT = 35     # Armor restored by an armor shard.
PICKUP_RADIUS = 0.55         # Distance within which the player auto-collects a pickup.

# ----------------------------------------------------------------------------
# Powerups — temporary buffs (durations in seconds).
# ----------------------------------------------------------------------------
POWERUP_QUAD_DURATION = 18.0     # Quad Damage length.
POWERUP_QUAD_MULT = 4.0          # Damage multiplier while Quad is active.
POWERUP_HASTE_DURATION = 15.0    # Haste length.
POWERUP_HASTE_MULT = 1.6         # Speed multiplier while Haste is active.
POWERUP_SHIELD_DURATION = 12.0   # Divine Shield (invulnerability) length.

# ----------------------------------------------------------------------------
# Enemies (base values; per-type multipliers live in enemy.py, difficulty in
# DIFFICULTIES above). These are the "Reborn Hero" baseline numbers.
# ----------------------------------------------------------------------------
ENEMY_SIGHT_RANGE = 14.0     # How far a demon-girl can spot the player.
ENEMY_SCORE = 100            # Base points for killing a demon-girl.
ENEMY_RADIUS = 0.3           # Collision radius used for movement + projectile hits.
ENEMY_PROJECTILE_SPEED = 5.0 # Speed of demon-girl ranged attacks (tiles/sec).
ENEMY_PROJECTILE_DAMAGE = 9  # Base damage of a demon-girl projectile.
ENEMY_PROJECTILE_RADIUS = 0.3# Collision radius of an enemy projectile.

# ----------------------------------------------------------------------------
# Doors — auto-opening sliding doors.
# ----------------------------------------------------------------------------
DOOR_OPEN_RANGE = 1.6        # Player distance that triggers a door to open.
DOOR_SPEED = 1.8             # How fast doors slide open/closed (fraction/sec).
DOOR_STAY_OPEN = 3.0         # Seconds a door stays open after you leave.

# ----------------------------------------------------------------------------
# World scale + render limits
# ----------------------------------------------------------------------------
TILE = 1.0                   # Logical size of one grid cell.
MAX_DEPTH = 22.0             # Maximum ray distance (also the fog fade distance).

# ----------------------------------------------------------------------------
# Effects
# ----------------------------------------------------------------------------
SCREEN_SHAKE_DECAY = 8.0     # How quickly screen shake settles (per second).
MUZZLE_FLASH_TIME = 0.06     # Seconds a weapon muzzle flash is shown.
WEAPON_BOB_SPEED = 9.0       # How fast the weapon bobs while walking.
WEAPON_BOB_AMOUNT = 10.0     # Pixels of weapon bob travel.

# ----------------------------------------------------------------------------
# Minimap
# ----------------------------------------------------------------------------
MINIMAP_TILE = 7             # Pixel size of one map cell on the minimap.
MINIMAP_MARGIN = 12          # Minimap offset from the top-right corner.

# ----------------------------------------------------------------------------
# Colors (R, G, B tuples, 0–255)
# ----------------------------------------------------------------------------
COLOR_FOG = (10, 4, 10)        # Distance fog color (walls/floor fade toward this).

# Per-level visual themes: which floor/ceiling textures and fog to use. The
# index matches the level order in maps.LEVELS.
LEVEL_THEMES = [
    {"floor": "stone", "ceil": "cave",  "fog": (12, 6, 14)},   # Level 1: brick labyrinth.
    {"floor": "blood", "ceil": "flesh", "fog": (20, 4, 8)},    # Level 2: flesh catacombs.
    {"floor": "rune",  "ceil": "void",  "fog": (8, 4, 20)},    # Level 3: rune sanctum.
    {"floor": "stone", "ceil": "cave",  "fog": (26, 8, 4)},    # Level 4: molten vault.
    {"floor": "rune",  "ceil": "void",  "fog": (16, 0, 16)},   # Level 5: boss arena.
]

# ----------------------------------------------------------------------------
# Texture ids -> readable names (index matches textures.build_textures order)
# ----------------------------------------------------------------------------
TEX_EMPTY = 0                # 0 always means "no wall / walkable".
TEX_BRICK = 1                # Demonic brick.
TEX_FLESH = 2                # Organic flesh wall.
TEX_RUNE = 3                 # Glowing rune stone.
TEX_EXIT = 4                 # The level-exit portal.
TEX_DOOR = 5                 # A plain sliding door (auto-opens).
TEX_METAL = 6                # Metal/tech panel wall.
TEX_BOSS = 7                 # Ornate boss-arena wall.
TEX_DOOR_RED = 8             # Locked door (needs the red key).
TEX_DOOR_BLUE = 9            # Locked door (needs the blue key).
TEX_DOOR_YELLOW = 10         # Locked door (needs the yellow key).

# All tile ids that behave like doors (use the door open/close + slide logic).
DOOR_TILES = {TEX_DOOR, TEX_DOOR_RED, TEX_DOOR_BLUE, TEX_DOOR_YELLOW}
# Which key color each locked-door tile requires.
LOCKED_DOOR_KEY = {TEX_DOOR_RED: "red", TEX_DOOR_BLUE: "blue", TEX_DOOR_YELLOW: "yellow"}

# ----------------------------------------------------------------------------
# Hazard floors (lava) — damage the player while standing on them.
# ----------------------------------------------------------------------------
HAZARD_DPS = 14.0            # Damage per second while standing in lava.

# ----------------------------------------------------------------------------
# Score combo — consecutive quick kills multiply the points earned.
# ----------------------------------------------------------------------------
COMBO_WINDOW = 2.5           # Seconds before the kill combo resets.
COMBO_MAX = 8                # Maximum combo multiplier.

# ----------------------------------------------------------------------------
# Default user settings (persisted to settings.json; tweakable in Options).
# ----------------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "mouse_sensitivity": MOUSE_SENSITIVITY,  # Radians per pixel.
    "master_volume": 0.35,                   # 0..1 master mixer volume.
    "music_volume": 0.22,                    # 0..1 music volume.
    "fov_degrees": 60,                       # Field of view in degrees.
    "show_minimap": True,                    # Draw the minimap HUD element.
}
