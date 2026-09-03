"""This package provides tools for creating grid-based terminal and Pygame applications.

It exports key classes and constants for easy access, including Grid implementations 
(Grid, TermGrid, PygameGrid), Modules for application structure (Module, MainModule), 
and various constants and utility functions.
"""


from display_grid.locals import TA_NONE, TA_BOLD, TA_ITALIC, TA_UNDERLINE, TA_BLINK, TA_INVERT, TA_STRIKETHROUGH, KM_NONE, KM_SHIFT, KM_META, KM_CTRL
from display_grid.util import SUPPORTS_TRUECOLOR, BLOCKS, HORZ_BLOCKS, format_time, KeyEvent, MouseEvent, Event
from display_grid.graphics import GRAPHICS, load_graphics
from display_grid.grid import Grid, SubGrid
from display_grid.modules import Module, MainModule
from display_grid import locals, util, graphics, grid, modules


__all__ = [
    "locals",
    "TA_NONE",
    "TA_BOLD",
    "TA_ITALIC",
    "TA_UNDERLINE",
    "TA_BLINK",
    "TA_INVERT",
    "TA_STRIKETHROUGH",
    "KM_NONE",
    "KM_SHIFT",
    "KM_META",
    "KM_CTRL",
    "util",
    "SUPPORTS_TRUECOLOR",
    "BLOCKS",
    "HORZ_BLOCKS",
    "format_time",
    "KeyEvent",
    "MouseEvent",
    "Event",
    "graphics",
    "GRAPHICS",
    "load_graphics",
    "grid",
    "Grid",
    "SubGrid",
    "modules",
    "Module",
    "MainModule",
]

try:
    from display_grid import term_grid
    from display_grid.term_grid import TermGrid
    __all__ += ["term_grid", "TermGrid"]

except ImportError:
    pass

try:
    from display_grid import pygame_grid
    from display_grid.pygame_grid import PygameGrid
    __all__ += ["pygame_grid", "PygameGrid"]

except ImportError:
    pass