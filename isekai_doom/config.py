"""config.py — every tunable constant for ISEKAI DOOM lives here.

Keeping the numbers in one place means you can rebalance the whole game
(difficulty, speed, look) without hunting through the engine code.
"""

import math  # We need pi for the field-of-view, expressed in radians.

# ----------------------------------------------------------------------------
# Window + internal rendering resolution
# ----------------------------------------------------------------------------
# The actual on-screen window size in pixels (what the player sees).
WINDOW_WIDTH = 960            # Window width in pixels.
WINDOW_HEIGHT = 540           # Window height in pixels (16:9 with the width).

# We render the 3D world at a LOWER internal resolution for speed, then scale
# it up to the window. This gives a crisp retro look AND keeps the pure-Python
# raycaster fast enough for 60 FPS.
NUM_RAYS = 480                # One ray (and one wall column) per internal pixel-column.
RENDER_HEIGHT = 270           # Internal vertical resolution of the 3D view.
RENDER_WIDTH = NUM_RAYS       # Internal horizontal resolution equals the ray count.

# How much the internal surface is magnified to fill the window (handy for math).
SCALE_X = WINDOW_WIDTH / RENDER_WIDTH    # Horizontal scale factor.
SCALE_Y = WINDOW_HEIGHT / RENDER_HEIGHT  # Vertical scale factor.

# ----------------------------------------------------------------------------
# Camera / field of view
# ----------------------------------------------------------------------------
FOV = math.pi / 3             # Field of view: 60 degrees expressed in radians.
HALF_FOV = FOV / 2            # Half the FOV, used when spreading rays around the center.
# The distance from the camera to the projection plane, in internal pixels.
# Derived so that a wall exactly one unit away fills the screen height correctly.
SCREEN_DIST = (RENDER_WIDTH / 2) / math.tan(HALF_FOV)

# ----------------------------------------------------------------------------
# Frame timing
# ----------------------------------------------------------------------------
TARGET_FPS = 60              # The frame rate we cap the game at.
MAX_DELTA = 0.05             # Clamp per-frame delta-time (seconds) to avoid physics jumps.

# ----------------------------------------------------------------------------
# Player movement
# ----------------------------------------------------------------------------
MOVE_SPEED = 3.0             # Walking speed in map tiles per second.
SPRINT_MULTIPLIER = 1.8      # Sprinting speed multiplier (hold Shift).
TURN_SPEED = 2.6             # Keyboard turn speed in radians per second.
MOUSE_SENSITIVITY = 0.0022   # Radians turned per pixel of horizontal mouse motion.
PLAYER_RADIUS = 0.22         # Collision radius so the player can't slide into walls.

# ----------------------------------------------------------------------------
# Player vitals
# ----------------------------------------------------------------------------
MAX_HEALTH = 100             # Starting + maximum health.
MAX_MANA = 100               # Starting + maximum mana (fuel for Spirit Bolts).
MANA_REGEN = 8.0             # Mana regenerated per second.

# ----------------------------------------------------------------------------
# Weapons
# ----------------------------------------------------------------------------
SWORD_DAMAGE = 45            # Damage of one Holy Sword swing.
SWORD_RANGE = 1.5            # Reach of the sword in map tiles.
SWORD_ARC = 0.7              # Half-angle (radians) of the sword's hit cone.
SWORD_COOLDOWN = 0.40        # Seconds between sword swings.

BOLT_DAMAGE = 65             # Damage of a Spirit Bolt on hit.
BOLT_SPEED = 8.0             # Projectile speed in map tiles per second.
BOLT_COST = 18               # Mana cost per Spirit Bolt.
BOLT_COOLDOWN = 0.30         # Seconds between bolt casts.
BOLT_RADIUS = 0.35           # Collision radius for a bolt hitting an enemy.

# ----------------------------------------------------------------------------
# Enemies (the demon-girls)
# ----------------------------------------------------------------------------
ENEMY_SPEED = 1.5            # Chase speed in tiles per second.
ENEMY_HEALTH = 100           # Hit points per demon-girl.
ENEMY_DAMAGE = 11            # Damage dealt to the player per attack.
ENEMY_ATTACK_RANGE = 1.0     # Distance at which an enemy can hit the player.
ENEMY_ATTACK_COOLDOWN = 1.1  # Seconds between an enemy's attacks.
ENEMY_SIGHT_RANGE = 13.0     # How far a demon-girl can spot the player.
ENEMY_SCORE = 100            # Points for killing a demon-girl.
ENEMY_RADIUS = 0.3           # Collision radius used for movement + projectile hits.

# ----------------------------------------------------------------------------
# Pickups
# ----------------------------------------------------------------------------
PICKUP_HEALTH_AMOUNT = 30    # Health restored by a health pickup.
PICKUP_MANA_AMOUNT = 40      # Mana restored by a mana pickup.
PICKUP_RADIUS = 0.5          # Distance within which the player auto-collects a pickup.

# ----------------------------------------------------------------------------
# World scale + render limits
# ----------------------------------------------------------------------------
TILE = 1.0                   # Logical size of one grid cell.
MAX_DEPTH = 22.0             # Maximum ray distance (also the fog fade distance).

# ----------------------------------------------------------------------------
# Colors (R, G, B tuples, 0–255)
# ----------------------------------------------------------------------------
COLOR_CEILING = (28, 16, 30)   # Solid ceiling color (dim purple).
COLOR_FLOOR = (40, 30, 28)     # Solid floor color (dim brown).
COLOR_FOG = (16, 5, 12)        # Distance fog color (walls fade toward this).

# ----------------------------------------------------------------------------
# Texture id -> readable name (index matches textures.build_textures order)
# ----------------------------------------------------------------------------
TEX_EMPTY = 0                # 0 always means "no wall / walkable".
TEX_BRICK = 1                # Demonic brick.
TEX_FLESH = 2                # Organic flesh wall.
TEX_RUNE = 3                 # Glowing rune stone.
TEX_EXIT = 4                 # The level-exit portal.
