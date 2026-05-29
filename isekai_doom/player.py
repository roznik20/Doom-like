"""player.py — the isekai'd hero: position, facing, movement, and vitals.

The player is represented by a position (x, y) on the tile grid and a facing
`angle` in radians. The raycaster reads these to draw the world from the
player's eyes. Movement is collision-checked against walls with simple
axis-separated "wall sliding" so you glide along walls instead of sticking.
"""

import math                # Trig for converting the facing angle into motion.
from . import config       # Speeds, radius, and vital caps.


class Player:
    """Holds all mutable state for the hero and updates it each frame."""

    def __init__(self, x, y):
        # World position on the tile grid (floats; tile centers are X.5).
        self.x = x                       # Horizontal position.
        self.y = y                       # Vertical position (grid row direction).
        # Facing direction in radians (0 = +x axis). Increases turning right.
        self.angle = 0.0
        # Current and max health.
        self.health = config.MAX_HEALTH  # Start at full health.
        # Current and max mana.
        self.mana = config.MAX_MANA      # Start at full mana.
        # Set to True by combat code when the player dies.
        self.dead = False
        # Counts how many demon-girls this player has defeated (for stats).
        self.kills = 0

    def reset(self, x, y):
        """Reposition and fully restore the player (used when entering a level)."""
        self.x = x                       # Place at the new spawn x.
        self.y = y                       # Place at the new spawn y.
        self.angle = 0.0                 # Reset facing.
        self.health = config.MAX_HEALTH  # Refill health.
        self.mana = config.MAX_MANA      # Refill mana.
        self.dead = False                # No longer dead.

    def _is_wall(self, level, x, y):
        """Return True if world position (x, y) lies inside a solid wall cell."""
        # Convert the float world coordinate to integer grid indices.
        gx, gy = int(x), int(y)
        # Treat anything outside the grid bounds as solid (so you can't escape).
        if gx < 0 or gy < 0 or gx >= level["width"] or gy >= level["height"]:
            return True
        # A non-zero grid value means a wall texture id -> solid.
        return level["grid"][gy][gx] != 0

    def _blocked(self, level, x, y):
        """Check the player's collision circle (radius) around (x, y) for walls."""
        r = config.PLAYER_RADIUS         # The player's collision radius.
        # Sample the four cardinal edges of the collision circle for wall overlap.
        return (self._is_wall(level, x - r, y) or   # Left edge.
                self._is_wall(level, x + r, y) or   # Right edge.
                self._is_wall(level, x, y - r) or   # Top edge.
                self._is_wall(level, x, y + r))     # Bottom edge.

    def update(self, dt, inp, level):
        """Advance the player's facing and position for one frame.

        `dt`    is the frame time in seconds.
        `inp`   is the Input helper exposing which keys are held + mouse delta.
        `level` is the current level dict (for collision).
        """
        # --- Turning (keyboard arrows + mouse) ---
        # Arrow keys rotate at a fixed angular speed.
        if inp.left:
            self.angle -= config.TURN_SPEED * dt    # Turn left (counter-clockwise).
        if inp.right:
            self.angle += config.TURN_SPEED * dt    # Turn right (clockwise).
        # Mouse horizontal movement adds a proportional turn.
        self.angle += inp.mouse_dx * config.MOUSE_SENSITIVITY

        # --- Compute the movement speed for this frame ---
        speed = config.MOVE_SPEED                    # Base walking speed.
        if inp.sprint:
            speed *= config.SPRINT_MULTIPLIER        # Faster while sprinting.
        # Distance the player can travel this frame.
        step = speed * dt

        # Precompute the forward direction vector from the facing angle.
        fwd_x = math.cos(self.angle)                 # Forward x component.
        fwd_y = math.sin(self.angle)                 # Forward y component.
        # The strafe (sideways) vector is the forward vector rotated 90 degrees.
        strafe_x = math.cos(self.angle + math.pi / 2)
        strafe_y = math.sin(self.angle + math.pi / 2)

        # Accumulate the desired movement from all pressed movement keys.
        dx = 0.0                                     # Total intended x movement.
        dy = 0.0                                     # Total intended y movement.
        if inp.forward:
            dx += fwd_x * step                       # Move forward.
            dy += fwd_y * step
        if inp.back:
            dx -= fwd_x * step                       # Move backward.
            dy -= fwd_y * step
        if inp.strafe_left:
            dx -= strafe_x * step                    # Strafe left.
            dy -= strafe_y * step
        if inp.strafe_right:
            dx += strafe_x * step                    # Strafe right.
            dy += strafe_y * step

        # --- Apply movement with axis-separated collision (wall sliding) ---
        # Try the x movement alone; only accept it if the new spot is clear.
        if not self._blocked(level, self.x + dx, self.y):
            self.x += dx                             # Slide along x.
        # Try the y movement alone; this lets us slide when one axis is blocked.
        if not self._blocked(level, self.x, self.y + dy):
            self.y += dy                             # Slide along y.

        # --- Passive mana regeneration ---
        # Slowly refill mana up to the maximum each frame.
        self.mana = min(config.MAX_MANA, self.mana + config.MANA_REGEN * dt)

    def take_damage(self, amount):
        """Apply incoming damage and flag death if health hits zero."""
        self.health -= amount                        # Subtract the damage.
        if self.health <= 0:                         # If health is depleted...
            self.health = 0                          # Clamp so it never goes negative.
            self.dead = True                         # Mark the player as dead.

    def heal(self, amount):
        """Restore health, never exceeding the maximum."""
        self.health = min(config.MAX_HEALTH, self.health + amount)

    def add_mana(self, amount):
        """Restore mana, never exceeding the maximum."""
        self.mana = min(config.MAX_MANA, self.mana + amount)
