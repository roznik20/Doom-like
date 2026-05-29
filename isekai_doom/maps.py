"""maps.py — level layouts, the demon-girl catchphrases, and the parser.

Levels are authored as lists of text rows. The parser turns them into a
numeric wall grid plus lists of entities (player start, enemies by type,
pickups, ammo, powerups, doors). Rows are auto-padded with a fill wall
character so a miscounted row can never crash the game.

Character legend
  Walls:    '#' brick   'F' flesh   'R' rune   'B' boss-wall   'T' tech-metal
            '|' door     'X' exit portal
  Space:    '.' empty floor          'P' player start
  Enemies:  'i' imp   'c' caster   'b' brute   'd' dasher   'Q' boss
  Pickups:  'h' health   'm' mana   'a' armor
  Ammo:     's' shells   'r' rounds   'e' energy
  Powerups: 'q' quad damage   'z' haste   'g' divine shield (guardian)
"""

from . import config   # Texture id constants.

# Original anime-flavored catchphrases the demon-girls "shout" (shown as text).
CATCHPHRASES = [
    "Baka!", "Kyaa~!", "Senpai, notice me!", "Itadakimasu!", "Nani?!",
    "Yamete kudasai~", "Ara ara~", "Daisuki!", "Sugoi!", "Mou~ ikitai!",
    "Tasukete!", "Pyon pyon~", "Ehehe~ gotcha!", "Uso da!", "Maji?!",
    "Kowai~", "Hidoi!", "Gomen ne~ not really!", "Ganbatte... not!",
]

# Map each authored wall character to its wall texture id.
_CHAR_TO_WALL = {
    "#": config.TEX_BRICK, "F": config.TEX_FLESH, "R": config.TEX_RUNE,
    "X": config.TEX_EXIT, "|": config.TEX_DOOR, "T": config.TEX_METAL,
    "B": config.TEX_BOSS,
    "J": config.TEX_DOOR_RED, "K": config.TEX_DOOR_BLUE, "N": config.TEX_DOOR_YELLOW,
}
# Map enemy characters to archetype keys.
_CHAR_TO_ENEMY = {
    "i": "imp", "c": "caster", "b": "brute", "d": "dasher", "Q": "boss",
    "o": "bomber", "y": "healer",
}
# Map pickup/ammo/powerup/key characters to the kind the game understands.
_CHAR_TO_PICKUP = {
    "h": "health", "m": "mana", "a": "armor",
    "s": "shells", "r": "rounds", "e": "energy",
    "q": "quad", "z": "haste", "g": "shield",
    "j": "key_red", "k": "key_blue", "n": "key_yellow",
}


def parse_level(rows, name, fill="#"):
    """Convert authored text rows into a structured, padded level dictionary."""
    width = max(len(r) for r in rows)            # Widest row defines the width.
    rows = [r.ljust(width, fill) for r in rows]  # Pad every row to that width.

    grid = []                                    # Numeric wall grid.
    start = (1.5, 1.5)                           # Default player spawn.
    enemies = []                                 # (etype, x, y) spawns.
    pickups = []                                 # {x, y, kind} pickups.
    doors = []                                   # (x, y) door cells (incl. locked).
    hazards = []                                 # (x, y) lava floor cells.

    for y, line in enumerate(rows):
        grid_row = []
        for x, ch in enumerate(line):
            if ch in _CHAR_TO_WALL:
                wall_id = _CHAR_TO_WALL[ch]
                grid_row.append(wall_id)
                if wall_id in config.DOOR_TILES:
                    doors.append((x, y))         # Remember every door cell.
            else:
                grid_row.append(0)               # Walkable floor.
                cx, cy = x + 0.5, y + 0.5        # Entity center.
                if ch == "P":
                    start = (cx, cy)
                elif ch == "L":
                    hazards.append((x, y))       # Lava hazard floor.
                elif ch in _CHAR_TO_ENEMY:
                    enemies.append((_CHAR_TO_ENEMY[ch], cx, cy))
                elif ch in _CHAR_TO_PICKUP:
                    pickups.append({"x": cx, "y": cy, "kind": _CHAR_TO_PICKUP[ch]})
        grid.append(grid_row)

    return {
        "name": name,
        "grid": grid,
        "width": len(grid[0]),
        "height": len(grid),
        "start": start,
        "enemies": enemies,
        "pickups": pickups,
        "doors": doors,
        "hazards": hazards,
    }


# ---------------------------------------------------------------------------
# Level 1 — The Entry Labyrinth (brick + doors; imps; teaches the basics)
# ---------------------------------------------------------------------------
LEVEL_1 = parse_level([
    "########################",
    "#P...i.....|....h....#.X#",
    "#.####.###.#.####.#.#.|.#",
    "#.#..#...#.#....#.#.#.#.#",
    "#.#.s#.#.#.#.##.#.#.###.#",
    "#.#..#.#.#...##...#...i.#",
    "#.####.#.#########.####.#",
    "#....i.#.....h...#....#.#",
    "####.#.#####.###.#.##.#.#",
    "#....#.....#.#.i.#..#.#.#",
    "#.######.#.#.#.###.#.#.#.",
    "#.#......#.#.#...#.#.#m#.",
    "#.#.####.#.#.###.#.#.#.#.",
    "#...#..i.#.....|...#...#.",
    "#.###.##########.#######.",
    "#.........a.....|...i...#",
    "########################",
], "Level 1 — The Entry Labyrinth", fill="#")

# ---------------------------------------------------------------------------
# Level 2 — The Flesh Catacombs (casters + brutes; metal doors; shotgun ammo)
# ---------------------------------------------------------------------------
LEVEL_2 = parse_level([
    "FFFFFFFFFFFFFFFFFFFFFFFF",
    "FP...c....F....s...c...F",
    "F.FFFF.FF.|.FFFF.FF.FF.F",
    "F.F..b...F....F.h.F..b.F",
    "F.F.FFF.FF.FF.F.FF.FF.FF",
    "F...c.....FF..|.....c..F",
    "FFFF.FFFF.F.FF.FFFF.FF.F",
    "F....F..a.F.s..F....F..F",
    "F.FF.F.FF.|.FF.|.FF.F.FF",
    "F.F..b....F....F..b.F..F",
    "F.F.FFFF.FFFF.FFFF.FF.FF",
    "F.F....c.F..m.F....c...F",
    "F.FFFF.FF.FF.FF.FFFFFF.F",
    "F....b....|.....|....b.X",
    "FFFFFFFFFFFFFFFFF.FFFF|FF",
    "F....h.....e.....c....mF",
    "FFFFFFFFFFFFFFFFFFFFFFFF",
], "Level 2 — The Flesh Catacombs", fill="F")

# ---------------------------------------------------------------------------
# Level 3 — The Rune Sanctum (dashers + casters + brutes; powerups; energy)
# ---------------------------------------------------------------------------
LEVEL_3 = parse_level([
    "RRRRRRRRRRRRRRRRRRRRRRRR",
    "RP...d...R....q....R..cR",
    "R.RRR.RR.R.RRRR.RR.R.R.R",
    "R.R.c...R....R.h.R..d.R.",
    "R.R.RRR.RR.RR.R.RR.RR.RR",
    "R...d.....RR..|...z.d..R",
    "RRRR.RRRR.R.RR.RRRR.RR.R",
    "R..b.R.dd.R.e..R..b.R..R",
    "R.RR.R.RR.|.RR.|.RR.R.RR",
    "R.R..c....R....R..c.R..R",
    "R.R.RRRR.RRRR.RRRR.RR.RR",
    "R.R..d.g.R..a.R....d...R",
    "R.RRRR.RR.RR.RR.RRRRRR.R",
    "R..b......|..d..|...b..X",
    "RRRRRRRRRRRRRRRRR.RRRR|RR",
    "R...h....e....q....d..mR",
    "RRRRRRRRRRRRRRRRRRRRRRRR",
], "Level 3 — The Rune Sanctum", fill="R")

# ---------------------------------------------------------------------------
# Level 4 — The Molten Vault (lava hazards, bombers, healers, keys + a locked
# vault). Designed as an open pillared hall so the exit is always reachable.
# ---------------------------------------------------------------------------
LEVEL_MOLTEN = parse_level([
    "TTTTTTTTTTTTTTTTTTTTTTTT",
    "TP...o......LL......o..T",
    "T..TT...TT......TT..TT.T",
    "T...n.......j.........aT",
    "T.TT...LLL...LLL...TT..T",
    "T....y.....q.....y....T",
    "T..TT...TT...TT...TT..T",
    "T.......|........|....T",
    "T..o..LL....d...LL..o.T",
    "T.TT.....TT...TT.....TT",
    "T....g.......s....z...T",
    "T..TT...LLL...LLL..TT.T",
    "T.......o.....o.....e.T",
    "T..TT..........JTT...gT",
    "T....h....e....q....m.T",
    "T........|.........d.XT",
    "TTTTTTTTTTTTTTTTTTTTTTTT",
], "Level 4 — The Molten Vault", fill="T")

# ---------------------------------------------------------------------------
# Level 5 — The Throne of the Demon Queen (BOSS arena + adds + powerups)
# ---------------------------------------------------------------------------
LEVEL_4 = parse_level([
    "BBBBBBBBBBBBBBBBBBBBBBBB",
    "BP......a....e....h....B",
    "B.BB.BB.........BB.BB...B",
    "B.B...........q.....B..B",
    "B...BB...........BB....B",
    "B.B......d.....d......B.B",
    "B.BB.................BB.B",
    "B........BBB.BBB........B",
    "B...g....B.....B....z...B",
    "B........BB.Q.BB........B",
    "B.BB.....B.....B.....BB.B",
    "B.B......BBB.BBB......B.B",
    "B...BB...........BB....B",
    "B.B.....d.....d......B.B",
    "B.BB.....s....r....BB..B",
    "B......h....m....a.....X",
    "BBBBBBBBBBBBBBBBBBBBBBBB",
], "Level 5 — Throne of the Demon Queen", fill="B")

# The ordered list of levels the game plays through.
LEVELS = [LEVEL_1, LEVEL_2, LEVEL_3, LEVEL_MOLTEN, LEVEL_4]
