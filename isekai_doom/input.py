"""input.py — turns raw keyboard/mouse state into named game actions.

The rest of the engine never asks pygame "is the W key down?" directly.
Instead it reads friendly flags like `inp.forward`. This keeps the control
mapping in exactly one place and makes it trivial to rebind keys later.
"""

import pygame             # Reading the keyboard and mouse state.


class Input:
    """Holds the current frame's movement/aim/fire intentions."""

    def __init__(self):
        # Movement intents (set fresh every frame in poll()).
        self.forward = False        # Hold to walk forward.
        self.back = False           # Hold to walk backward.
        self.strafe_left = False    # Hold to sidestep left.
        self.strafe_right = False   # Hold to sidestep right.
        # Turning intents (keyboard).
        self.left = False           # Turn camera left.
        self.right = False          # Turn camera right.
        # Modifiers / actions.
        self.sprint = False         # Hold to run faster.
        self.fire = False           # Hold/press to attack.
        # Horizontal mouse movement since last frame (radians applied in player).
        self.mouse_dx = 0.0

    def poll(self, mouse_locked):
        """Refresh all action flags from the current input device state.

        `mouse_locked` says whether the pointer is captured for mouse-look;
        only then do we consume relative mouse motion for turning.
        """
        # Snapshot of every key's pressed/released state this frame.
        keys = pygame.key.get_pressed()

        # --- Movement (WASD) ---
        self.forward = keys[pygame.K_w]                 # W -> forward.
        self.back = keys[pygame.K_s]                    # S -> backward.
        self.strafe_left = keys[pygame.K_a]             # A -> strafe left.
        self.strafe_right = keys[pygame.K_d]            # D -> strafe right.

        # --- Turning (arrow keys) ---
        self.left = keys[pygame.K_LEFT]                 # Left arrow -> turn left.
        self.right = keys[pygame.K_RIGHT]               # Right arrow -> turn right.

        # --- Modifiers / actions ---
        # Either Shift key enables sprinting.
        self.sprint = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        # Space OR the left mouse button fires the equipped weapon.
        mouse_buttons = pygame.mouse.get_pressed()      # (left, middle, right).
        self.fire = keys[pygame.K_SPACE] or mouse_buttons[0]

        # --- Mouse-look ---
        if mouse_locked:
            # get_rel returns motion since the last call; we only want the x part.
            self.mouse_dx = pygame.mouse.get_rel()[0]
        else:
            # When not captured, ignore mouse motion (e.g. while in a menu).
            self.mouse_dx = 0.0
            # Still call get_rel to keep its internal delta from accumulating.
            pygame.mouse.get_rel()
