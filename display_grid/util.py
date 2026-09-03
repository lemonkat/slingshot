"""This module contains miscellaneous utility functions and data classes for the package.

Includes character constants for drawing, time formatting functions, and base classes
for input events.
"""
import os
from dataclasses import dataclass

SUPPORTS_TRUECOLOR = os.environ.get("COLORTERM") in ("truecolor", "24bit")

BLOCKS = " ▁▂▃▄▅▆▇█▀"
HORZ_BLOCKS = " ▏▎▍▌▋▊▉█▐"


def format_time(t: int) -> str:
    """Formats a duration in seconds into a string.

    If the time is less than an hour, the format is MM:SS.
    Otherwise, the format is HH:MM:SS.

    Args:
        t: The duration in seconds.

    Returns:
        The formatted time string.
    """
    t = int(t)
    if t < 3600:
        return f"{t // 60}:{t % 60:02}"
    return f"{t // 3600}:{(t // 60) % 60:02}:{t % 60:02}"


class Event:
    """Represents a user input event.

    This is the base class for specific event types like keyboard and mouse events.
    """

    pass


@dataclass(frozen=True)
class KeyEvent(Event):
    """Represents a keyboard press event.

    Attributes:
        key: The character or name of the key pressed (e.g., 'a', 'KEY_ENTER').
        mod: A bitmask of modifier keys held down (e.g., KM_SHIFT, KM_CTRL).
    """

    key: str = " "
    mod: int = 0


@dataclass(frozen=True)
class MouseEvent(Event):
    """Represents a mouse-related event.

    Attributes:
        button: The mouse button that was pressed or released.
        state: The state of the button (True for pressed, False for released).
        pos: A tuple (row, col) representing the position of the mouse cursor.
        mod: A bitmask of modifier keys held down (e.g., KM_SHIFT, KM_CTRL).
    """

    button: int = 0
    state: bool = True  # True is down
    pos: tuple[int, int] = (0, 0)
    mod: int = 0