"""ISEKAI DOOM — a Doom-style raycasting FPS written in pure Python + pygame.

You play an ordinary person who died and was *isekai'd* (reborn) into a demon
labyrinth. The "demons" are anime-style girls who shout catchphrases at you.
Fight through three levels with a Holy Sword and Spirit Bolts, and escape.

This package is split into small, single-responsibility modules so each piece
of the engine is easy to read on its own:

    config.py     -> all tunable numbers (speeds, damage, colors, resolution)
    textures.py   -> procedurally generated wall textures (no image files)
    sprites.py    -> procedurally drawn anime-girl demon sprites
    audio.py      -> synthesized sound effects (no copyrighted audio)
    maps.py       -> the three level layouts + demon catchphrases
    player.py     -> player position, movement, collision, vitals
    raycaster.py  -> the core 3D wall + sprite renderer (DDA raycasting)
    weapon.py     -> weapons, projectiles, and the first-person view-model
    enemy.py      -> demon-girl spawning, AI, and combat
    hud.py        -> heads-up display + menu/overlay screens
    game.py       -> the central state machine that ties everything together
"""

# A simple version string so the title screen and README can stay in sync.
__version__ = "1.0.0"
