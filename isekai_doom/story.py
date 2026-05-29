"""story.py — the narrative text for ISEKAI DOOM.

All original writing. The game shows:
  * INTRO_CRAWL  — a scrolling backstory before the first level.
  * LEVEL_INTROS — a couple of lines when each level begins.
  * EPILOGUE     — the closing text on the victory screen.

Cast:
  KAI MORI    — you: an ordinary office worker who died and got isekai'd.
  ARIA        — the goddess who "blessed" you with a second life (and a sword).
  QUEEN LILITH — ruler of the demon-girls who run the labyrinth.
"""

# The scrolling intro shown after you press Start (Star Wars-style crawl).
INTRO_CRAWL = [
    "ISEKAI DOOM",
    "",
    "Reborn in the Demon World",
    "",
    "",
    "Kai Mori was nobody special.",
    "An office worker, thirty-one, tired.",
    "He stepped off a curb without looking...",
    "and a delivery truck did the rest.",
    "",
    "He woke in a hall of white light, before",
    "ARIA, a goddess with too many teeth in",
    "her smile.",
    "",
    "\"Congratulations!\" she sang. \"A second",
    "life awaits — in a world that NEEDS a",
    "hero. Small print: it is a labyrinth, it",
    "is full of demons, and the demons are...",
    "well. You'll see.\"",
    "",
    "She pressed a Holy Sword into his hands",
    "and shoved him through a shimmering door.",
    "",
    "The demons were anime girls.",
    "They giggled. They shouted things he",
    "half-understood. They were trying very,",
    "very hard to kill him.",
    "",
    "At the labyrinth's heart waits their",
    "ruler: QUEEN LILITH.",
    "",
    "Find the exits. Survive the moe.",
    "Cut a path to the throne...",
    "and go HOME.",
    "",
    "",
    "[ Press ENTER to begin ]",
]

# One or two lines shown as each level starts (keyed by level index).
LEVEL_INTROS = {
    0: ["The door slams shut behind you.",
        "A voice giggles in the dark: \"Senpai... play with us?\""],
    1: ["The walls here are warm. Breathing.",
        "Aria whispers: \"Don't think about it too hard, dear.\""],
    2: ["Glowing runes pulse like a heartbeat.",
        "Something older than the demon-girls watched you arrive."],
    3: ["Heat. The floor runs molten gold.",
        "Locked vaults guard the way — find their keys."],
    4: ["A throne of obsidian. Wings unfold.",
        "QUEEN LILITH yawns. \"Oh good. A snack with a sword.\""],
}

# The closing text on the victory screen.
EPILOGUE = [
    "Lilith dissolved into petals and static.",
    "The labyrinth exhaled and let you go.",
    "Aria waited at the final door, applauding.",
    "\"See? You ARE a hero. Encore?\"",
    "Kai walked into the light — and home.",
]
