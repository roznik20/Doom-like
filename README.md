# ISEKAI DOOM — Reborn in the Demon World

A complete, from-scratch **Doom-style raycasting FPS written in pure Python**
(only `pygame` + `numpy`). You play an ordinary person who died, got
*isekai'd* (reincarnated) by a goddess, and woke up in a labyrinth full of
**anime demon-girls** who shout catchphrases at you. Fight through three
levels with a **Holy Sword** and **Spirit Bolts**, and escape.

Every line of code is commented so you can follow exactly how the engine works.

![ISEKAI DOOM](https://img.shields.io/badge/engine-raycasting-ff3b6b) ![python](https://img.shields.io/badge/python-3.8%2B-blue)

---

## Quick start

```bash
# 1. Install the two dependencies
pip install -r requirements.txt

# 2. Run the game
python main.py
```

A window opens on the title screen. Press **Enter** to begin.

> **Headless servers:** the game needs a real display + audio device. On a
> machine without one it still imports and runs logic (used for testing) but
> won't show a window.

---

## Controls

| Input | Action |
|-------|--------|
| `W` / `S` | Move forward / back |
| `A` / `D` | Strafe left / right |
| `←` / `→` or **Mouse** | Turn / look |
| **Left-Click** / `Space` | Attack |
| `1` / `2` | Switch weapon (Holy Sword / Spirit Bolt) |
| `Shift` | Sprint |
| `M` | Mute / unmute |
| `Esc` | Pause (in pause: `Enter` resume, `R` restart level) |
| `Enter` | Start / continue on menus |

---

## Gameplay

- **Holy Sword** — instant short-range cone melee. No ammo, just a cooldown.
- **Spirit Bolt** — spends **MP** to launch a magic orb that flies until it
  hits a wall or a demon-girl. MP regenerates over time.
- **Pickups** — red potions restore **HP**, blue crystals restore **MP**.
- **Demon-girls** — wander until they see you (with line of sight), then chase
  and attack in melee, shouting anime catchphrases. Defeat them all and reach
  the glowing **exit portal** to advance. Clear all three levels to win.

---

## How the engine works

This is the classic **raycasting** technique (Wolfenstein 3D / Doom-era):

1. The world is a 2-D grid of wall cells (`maps.py`).
2. For every vertical column of the screen, `raycaster.py` shoots one ray and
   uses the **DDA** algorithm to step through grid cells until it hits a wall.
3. The wall's distance decides how tall to draw that column: a 1-pixel-wide
   strip of the wall's texture is stretched to that height. Near walls look
   tall, far walls look short — that's the 3-D illusion.
4. Each column's distance is stored in a **z-buffer** so **sprites** (the
   demon-girls, pickups, and bolts) can be billboarded into the scene and
   correctly hidden behind closer walls.
5. Everything is rendered at a low internal resolution (480×270) and scaled up
   to the window for speed and a crunchy retro look.

### No external art or audio files

To keep the repo self-contained and avoid any copyright issues:

- **Wall textures** are generated procedurally with `numpy` (`textures.py`).
- **Demon-girl sprites, pickups, and the bolt** are drawn at runtime with
  pygame vector primitives (`sprites.py`).
- **All sound effects** are synthesized from raw waveforms at startup
  (`audio.py`). We ship **no copyrighted anime audio**; the "anime voices" are
  high-pitched synthesized blips paired with **original** on-screen catchphrase
  text (`maps.py`).

---

## Project structure

```
Doom-like/
├── main.py                 # Launcher — creates the Game and runs it
├── requirements.txt        # pygame + numpy
├── README.md               # This file
└── isekai_doom/            # The game package
    ├── __init__.py         # Package docs + version
    ├── config.py           # Every tunable constant (speeds, damage, colors)
    ├── textures.py         # Procedural wall textures (numpy)
    ├── sprites.py          # Procedural anime demon-girl + item sprites
    ├── audio.py            # Synthesized sound effects (numpy + pygame.mixer)
    ├── maps.py             # The three level layouts + catchphrases
    ├── input.py            # Keyboard/mouse -> named actions
    ├── player.py           # Player position, movement, collision, vitals
    ├── raycaster.py        # The 3-D wall + sprite renderer (DDA)
    ├── weapon.py           # Weapons, projectiles, first-person view-model
    ├── enemy.py            # Demon-girl spawning, AI, and combat
    ├── hud.py              # HUD + title/pause/game-over/victory screens
    └── game.py             # The central state machine + main loop
```

---

## Tuning the game

Open `isekai_doom/config.py` — almost everything you'd want to change lives
there: movement speed, weapon damage, enemy difficulty, field of view, render
resolution, and colors. Edit the level layouts in `isekai_doom/maps.py` (they
are plain text grids) to design your own maps.

---

## Credits

Built as a self-contained educational example of a raycasting FPS. All art,
sound, and text are generated/written from scratch — no third-party assets.
