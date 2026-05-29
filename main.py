#!/usr/bin/env python3
"""main.py — the launcher you run to play ISEKAI DOOM.

Usage:
    python main.py

All the real work lives in the `isekai_doom` package; this file just creates
the Game object and starts its main loop, with a friendly error if pygame
isn't installed yet.
"""

import sys     # Used to print a clean message and exit on a missing dependency.


def main():
    """Create the game and run it, guiding the user if pygame is missing."""
    try:
        # Import here (not at module top) so we can catch a missing dependency.
        from isekai_doom.game import Game
    except ImportError as exc:
        # Most likely cause: pygame/numpy aren't installed yet.
        print("Failed to import the game:", exc)
        print("Install the dependencies first with:")
        print("    pip install -r requirements.txt")
        # Exit with a non-zero status to signal failure to the shell.
        sys.exit(1)

    # Build the game (window, assets, sounds) and enter the main loop.
    Game().run()


# Only run main() when this file is executed directly, not when imported.
if __name__ == "__main__":
    main()
