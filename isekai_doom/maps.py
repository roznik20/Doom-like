"""maps.py — the three level layouts plus the demon-girl catchphrases.

Each level is authored as a list of equal-length text rows so it's easy to
read and edit by hand. `parse_level` turns those characters into:
    - grid:    2D list of ints (0 = walkable, >0 = wall texture id)
    - start:   (x, y) float spawn position for the player (tile centers)
    - enemies: list of (x, y) demon-girl spawn points
    - pickups: list of dicts {"x","y","type"} for health/mana pickups

Character legend:
    '#' brick wall     'F' flesh wall     'R' rune wall    'E' exit portal
    '.' empty floor    'P' player start   'D' demon spawn
    'H' health pickup  'M' mana pickup
"""

from . import config   # Pull in the texture id constants (TEX_BRICK, etc.).

# Original anime-flavored catchphrases the demon-girls "shout" (shown as text).
CATCHPHRASES = [
    "Baka!",                 # "Idiot!"
    "Kyaa~!",                # Surprised squeal.
    "Senpai, notice me!",    # Classic clingy line.
    "Itadakimasu!",          # "Let's eat!" — she's eyeing you.
    "Nani?!",                # "What?!"
    "Yamete kudasai~",       # "Please stop~"
    "Ara ara~",              # Teasing trope.
    "Daisuki!",              # "I love it!"
    "Sugoi!",                # "Amazing!"
    "Mou~ ikitai!",          # Playful whine.
    "Tasukete!",             # "Help me!"
    "Pyon pyon~",            # Cute hopping sound.
]

# Map each authored character to its wall texture id (only for solid cells).
_CHAR_TO_WALL = {
    "#": config.TEX_BRICK,   # Brick.
    "F": config.TEX_FLESH,   # Flesh.
    "R": config.TEX_RUNE,    # Rune stone.
    "E": config.TEX_EXIT,    # Exit portal.
}


def parse_level(rows, name):
    """Convert authored text rows into a structured level dictionary."""
    grid = []                                  # Numeric wall grid we will build.
    start = (1.5, 1.5)                         # Default player spawn if none marked.
    enemies = []                               # Collected demon spawn points.
    pickups = []                               # Collected pickup spawns.

    # Walk every authored row (y is the vertical grid coordinate).
    for y, line in enumerate(rows):
        grid_row = []                          # The numeric row we are assembling.
        # Walk every character/column in this row (x is horizontal).
        for x, ch in enumerate(line):
            if ch in _CHAR_TO_WALL:            # Solid wall character?
                grid_row.append(_CHAR_TO_WALL[ch])   # Store its texture id.
            else:                              # Otherwise it's walkable (id 0).
                grid_row.append(0)             # Mark the cell as empty floor.
                cx, cy = x + 0.5, y + 0.5      # Tile-center coordinates for entities.
                if ch == "P":                  # Player start marker.
                    start = (cx, cy)           # Remember the spawn position.
                elif ch == "D":                # Demon spawn marker.
                    enemies.append((cx, cy))   # Record an enemy spawn.
                elif ch == "H":                # Health pickup marker.
                    pickups.append({"x": cx, "y": cy, "type": "health"})
                elif ch == "M":                # Mana pickup marker.
                    pickups.append({"x": cx, "y": cy, "type": "mana"})
        grid.append(grid_row)                  # Append the finished row to the grid.

    # Bundle everything into a single dictionary describing the level.
    return {
        "name": name,                          # Display name.
        "grid": grid,                          # Wall layout.
        "width": len(grid[0]),                 # Number of columns.
        "height": len(grid),                   # Number of rows.
        "start": start,                        # Player spawn.
        "enemies": enemies,                    # Enemy spawns.
        "pickups": pickups,                    # Pickup spawns.
    }


# ---------------------------------------------------------------------------
# Level 1 — The Entry Labyrinth (brick maze, gentle introduction)
# ---------------------------------------------------------------------------
LEVEL_1 = parse_level([
    "################",   # Solid top border wall.
    "#P.....#......D#",   # Player start (left), a demon waiting (right).
    "#.####.#.####..#",   # Interior corridor walls.
    "#.#..#.#.#..H#.#",   # A health pickup tucked in a room.
    "#.#.D#...#.##..#",   # A demon in a pocket.
    "#.#..####.#..#.#",   # More maze walls.
    "#.#......M#..#.#",   # A mana pickup.
    "#.######.###.#.#",   # Dividing walls.
    "#......#....#..#",   # Open passage.
    "#.####.####.##.#",   # Walls shaping the route.
    "#.#D.#....#..D.#",   # Two demons guarding the way.
    "#.#.######.###.#",   # Wall block.
    "#.#........#...#",   # Corridor toward the exit.
    "#.########.#.#.#",   # Near-exit walls.
    "#..........#.EE#",   # The exit portal (bottom-right).
    "################",   # Solid bottom border wall.
], "Level 1 — The Entry Labyrinth")

# ---------------------------------------------------------------------------
# Level 2 — The Flesh Catacombs (organic walls, more demons)
# ---------------------------------------------------------------------------
LEVEL_2 = parse_level([
    "FFFFFFFFFFFFFFFF",   # Flesh walls all around.
    "FP...D....M...DF",   # Player start, demons, and a mana pickup.
    "F.FFFF.FFFF.FF.F",   # Flesh corridor walls.
    "F.F..D....D.F..F",   # Demons in the open.
    "F.F.FFFFFF.FF.FF",   # Branching corridors.
    "F...F....H.....F",   # A mid-level health pickup.
    "FFF.F.FF.FFFFF.F",   # Maze walls.
    "F.....F..F...D.F",   # Open room with a demon.
    "F.FFF.FF.F.FFF.F",   # More walls.
    "F.F.D....F.F...F",   # A lurking demon.
    "F.F.FFFF.F.F.FFF",   # Wall block.
    "F.F....M.F.....F",   # Mana pickup in a nook.
    "F.FFFF.FFFFFFF.F",   # Long wall.
    "F....D.......D.F",   # Two demons near the exit.
    "FFFFFFFFFFF.FEEF",   # Exit portal bottom-right.
    "FFFFFFFFFFFFFFFF",   # Bottom flesh wall.
], "Level 2 — The Flesh Catacombs")

# ---------------------------------------------------------------------------
# Level 3 — The Rune Sanctum (the demon-girl horde finale)
# ---------------------------------------------------------------------------
LEVEL_3 = parse_level([
    "RRRRRRRRRRRRRRRR",   # Rune walls — the ritual chamber.
    "RP....R....R..DR",   # Player start, far demon.
    "R.RRR.R.RR.R.RRR",   # Ornate divisions.
    "R.R.D...RM.R...R",   # Demon plus mana.
    "R.R.RRRRRR.RRR.R",   # Walls.
    "R...R....H.....R",   # A health pickup.
    "R.RRR.RR.RRRRR.R",   # Maze.
    "R.....RD.R..DD.R",   # A cluster of demons.
    "R.RRR.RR.R.RRR.R",   # Walls.
    "R.RDD....R.R.M.R",   # Two more demons + mana.
    "R.R.RRRR.R.RRR.R",   # Walls.
    "R.R....R.R....DR",   # Demon near a corner.
    "R.RRRR.R.RRRRR.R",   # Walls.
    "R..D.......DD..R",   # Final wave before the exit.
    "RRRRRRRRRR.REEER",   # Triple-wide exit portal.
    "RRRRRRRRRRRRRRRR",   # Bottom rune wall.
], "Level 3 — The Rune Sanctum")

# The ordered list of levels the game plays through.
LEVELS = [LEVEL_1, LEVEL_2, LEVEL_3]
