# ISEKAI DOOM — Reborn in the Demon World

A complete, from-scratch **Doom-style raycasting FPS written in pure Python**
(only `pygame` + `numpy`). You died, got *isekai'd* by a goddess, and woke up in
a labyrinth full of **anime demon-girls** who shout catchphrases at you. Fight
through four levels with **five holy weapons**, survive ranged casters, tanky
brutes, fast swarmers, and finally the **Demon Queen** boss — then escape.

Every line of code is commented so you can follow exactly how the engine works.

![engine](https://img.shields.io/badge/engine-raycasting-ff3b6b) ![python](https://img.shields.io/badge/python-3.8%2B-blue)

---

## Quick start

```bash
pip install -r requirements.txt   # pygame + numpy
python main.py                    # opens the window on the title screen
```

On the title screen, pick a difficulty with **↑/↓** and press **Enter**.

> **Headless servers:** the game needs a real display + audio device. Without
> one it still imports and runs its logic (used for automated testing) but
> won't show a window.

---

## Controls

| Input | Action |
|-------|--------|
| `W` `A` `S` `D` | Move / strafe |
| `←` `→` or **Mouse** | Turn / look |
| **Left-Click** / `Space` | Fire |
| `1` `2` `3` `4` `5` | Select weapon |
| **Mouse Wheel** | Cycle weapons |
| `Shift` | Sprint |
| `M` | Mute / unmute |
| `Esc` | Pause |
| In pause: `Enter` resume · `R` restart level · `T` quit to title |
| `Enter` | Confirm on menus |

---

## Arsenal (5 weapons)

| # | Weapon | Type | Ammo | Notes |
|---|--------|------|------|-------|
| 1 | **Holy Sword** | Melee cone | — | Fast, free, short reach |
| 2 | **Spirit Bolt** | Projectile | Mana | Travelling magic orb, leaves a trail |
| 3 | **Seraph Shotgun** | Hitscan spread | Shells | 7 pellets, big knock, screen shake |
| 4 | **Rosary Gatling** | Hitscan rapid | Rounds | Very high fire rate |
| 5 | **Goddess Beam** | Piercing beam | Energy | Hits *every* enemy in a line |

Damage is multiplied while **Quad Damage** is active.

---

## Enemies (anime demon-girls)

| Type | Behavior |
|------|----------|
| **Imp-chan** | Basic, fairly quick melee chibi |
| **Caster-chan** | Floats, keeps her distance, throws heart projectiles |
| **Brute-chan** | Huge, slow, very tanky, heavy melee |
| **Dasher-chan** | Tiny, winged, extremely fast swarmer |
| **Demon Queen** | The boss: melee + fireball volleys + summons dashers |

Each shouts original anime-style catchphrases when she spots you, attacks, or
faints. Difficulty (4 presets) scales their health, damage, speed, and fire rate.

---

## Powerups & pickups

- **Health** potions, **Mana** crystals, **Armor** shards (armor soaks part of
  incoming damage).
- **Ammo**: shells, rounds, energy.
- **Quad Damage** (×4 damage), **Haste** (move faster), **Divine Shield**
  (temporary invulnerability) — all with on-screen countdown chips.

---

## How the engine works

This is the classic **raycasting** technique, fully built up:

1. The world is a 2-D grid of wall cells (`maps.py`).
2. For every screen column, `raycaster.py` casts a ray with the **DDA**
   algorithm (camera-plane model — no fisheye) and stretches a 1px texture
   strip to the wall's distance. Near walls are tall, far walls short.
3. **Floors and ceilings are textured** via vectorized numpy "floor casting":
   each screen row is projected into the world and the texture is sampled per
   pixel in one numpy fancy-index (fast enough for 60+ FPS in pure Python).
4. A per-column **z-buffer** lets sprites *and* particles be correctly hidden
   behind nearer walls. Sprites are billboards; a fast path blits unoccluded
   sprites whole, and scaled sprites are cached.
5. **Sliding doors** open as you approach and retract into the ceiling.
6. **Particles** (blood, sparks, kill bursts, projectile trails), **distance
   fog**, **screen shake**, weapon **bob**, and **muzzle flashes** add polish.

### No external art or audio files — everything is generated

- **Wall + floor + ceiling textures**: procedural numpy (`textures.py`).
- **All sprites** (5 enemy types, the boss, projectiles, pickups, powerups):
  drawn at runtime with pygame primitives (`sprites.py`).
- **All sound effects + two looping music tracks**: synthesized from raw
  waveforms (`audio.py`). No copyrighted anime audio — the "voices" are
  synthesized blips paired with **original** catchphrase text.

---

## Project structure

```
Doom-like/
├── main.py                 # Launcher — creates the Game and runs it
├── requirements.txt        # pygame + numpy
├── README.md               # This file
└── isekai_doom/
    ├── __init__.py         # Package docs + version
    ├── config.py           # Every tunable: resolution, weapons, enemies,
    │                       #   powerups, doors, difficulty, colors, themes
    ├── textures.py         # Procedural wall + floor/ceiling textures (numpy)
    ├── sprites.py          # 5 enemy types, boss, projectiles, pickups, powerups
    ├── particles.py        # Blood/spark/trail/burst particle system
    ├── audio.py            # Synthesized SFX + looping music
    ├── maps.py             # Four level layouts + catchphrases + parser
    ├── input.py            # Keyboard/mouse -> named actions
    ├── player.py           # Position, movement, vitals, ammo, armor, powerups
    ├── raycaster.py        # 3-D renderer: walls, floor/ceiling, sprites, particles
    ├── weapon.py           # 5 weapons, projectiles, bob, muzzle flash, view-models
    ├── enemy.py            # Enemy archetypes, AI, ranged attacks, boss, summons
    ├── hud.py              # HUD, minimap, boss bar, powerup chips, menus
    └── game.py             # State machine + main loop (combat, doors, fx, music)
```

---

## Tuning & modding

Open `isekai_doom/config.py` — movement, weapon stats, enemy archetypes,
powerup durations, difficulty multipliers, field of view, render resolution,
and per-level color themes all live there. Edit the plain-text grids in
`isekai_doom/maps.py` to design your own levels (the legend is at the top of
the file), and add enemy types in `enemy.py`'s `ENEMY_TYPES` table.

---

## Credits

A self-contained educational example of a raycasting FPS. All art, sound, and
text are generated/written from scratch — no third-party assets.
