"""This module provides a Grid implementation for Pygame-based applications.

It uses a `pygame.Surface` as a canvas, rendering characters and colors
using a specified font (either a system font name or a file path).
"""

import os

import time
import itertools
import typing
import contextlib

import numpy as np
import pygame as pg

import display_grid as dg


BLINK_RATE = 1

DEFAULT_FONT = "hacknerdfontmono"

KEY_ATTRS = {
    getattr(pg, key): "KEY_" + key[2:] for key in dir(pg) if key.startswith("K_")
}

KEY_MAP = {
    # " ": "KEY_SPACE",
    "KEY_RETURN": "\n",
    "KEY_TAB": "\t",
}

def _get_font(font: str, size: int) -> pg.font.Font:
    """Creates a Font object using either the system fonts or a file.

    Args:
        font (str): The system name or file path of the font.
        size (int): The point size of the font.
    """
    if font in pg.font.get_fonts():
        return pg.font.SysFont(font, size)
    elif os.path.exists(font):
        return pg.font.Font(font, size)

class PygameGrid(dg.Grid):
    """A Grid that displays its contents in a `pygame.Surface`.
    
    This class handles rendering the grid's data to a Pygame window and
    translating Pygame input into `display_grid` events. It performs
    differential rendering, only updating parts of the screen that have changed.
    
    Attributes:
        surf (pg.Surface): The Pygame surface to draw on.
        font (pg.font.Font): The font used for rendering text.
        prev (dg.Grid): A copy of the grid's state from the last draw call,
            used to determine which cells need updating.
    """
    
    def __init__(
        self,
        surf: pg.Surface,
        font: str = DEFAULT_FONT,
        font_size: int = 24,
        shape: typing.Optional[tuple[int, int]] = None,
    ) -> None:
        """Constructs a PygameGrid.
        
        Args:
            surf: The `pygame.Surface` to draw on.
            font: The name or file path of the font to use.
            font_size: The point size of the font.
            shape: A (rows, cols) tuple for the grid's shape. If None, it
                is calculated based on the surface and font size.
        """
        self.surf = surf

        self.font = _get_font(font, font_size)

        if shape is None:
            shape = self.get_real_shape()

        colors = np.empty((*shape, 2, 3), dtype=np.uint8)
        chars = np.empty(shape, dtype=np.int32)
        attrs = np.empty(shape, dtype=np.uint8)

        super().__init__(colors, chars, attrs)

    @classmethod
    def get_char_shape(
        cls,
        font: typing.Optional[pg.font.Font] = None,
        font_name: str = DEFAULT_FONT,
        font_size: int = 24,
    ) -> tuple[int, int, int, int]:
        """Determines the pixel bounding box of a character in a given font.
        
        Args:
            font: A `pygame.Font` object. If None, a new font is created.
            font_name: The font name to use if `font` is None.
            font_size: The font size to use if `font` is None.

        Returns:
            A (min_x, min_y, max_x, max_y) tuple for the character's
            pixel bounding box.
        """

        if font is None:
            font = _get_font(font_name, font_size)
        arr = pg.surfarray.array_red(font.render("█", False, [1, 0, 0], [0, 0, 0])) > 0
        min_x = np.argmax(np.any(arr, axis=0))
        min_y = np.argmax(np.any(arr, axis=1))
        max_x = arr.shape[0] - np.argmax(np.any(arr[::-1], axis=0))
        max_y = arr.shape[1] - np.argmax(np.any(arr[:, ::-1], axis=1))
        return min_x, min_y, max_x, max_y

    @classmethod
    def get_surf_shape(
        cls,
        shape: tuple[int, int],
        font_name: str = DEFAULT_FONT,
        font_size: int = 24,
    ) -> tuple[int, int]:
        """Calculates the required surface dimensions in pixels for a given grid shape.
        
        Args:
            shape: The (rows, cols) of the grid.
            font_name: The name or file path of the font to be used.
            font_size: The size of the font to be used.

        Returns:
            A (width, height) tuple of the required pixel dimensions.
        """
        min_x, min_y, max_x, max_y = cls.get_char_shape(font_name=font_name, font_size=font_size)
        font_w, font_h = max_x - min_x, max_y - min_y
        return font_w * shape[1], font_h * shape[0]

    def get_real_shape(self) -> tuple[int, int]:
        """Gets the grid shape that can fit on the current surface.
        
        Returns:
            A (rows, cols) tuple of the maximum grid size.
        """
        surf_w, surf_h = self.surf.get_size()
        min_x, min_y, max_x, max_y = self.get_char_shape(font=self.font)
        font_w, font_h = max_x - min_x, max_y - min_y
        return surf_h // font_h, surf_w // font_w

    def draw(self) -> None:
        """Renders changed portions of the grid to the Pygame surface."""
        
        min_x, min_y, max_x, max_y = self.get_char_shape(font=self.font)
        font_w, font_h = max_x - min_x, max_y - min_y

        do_blink = (time.time() * BLINK_RATE) % 1 > 0.5

        blits = []

        for i, (row_chars, row_fg, row_bg, row_attrs) in enumerate(zip(self.chars, self.fg, self.bg, self.attrs)):
            j = 0
            for (fg, bg, attr), group in itertools.groupby(
                zip(row_chars, row_fg, row_bg, row_attrs), 
                key=(lambda x: (tuple(x[1]), tuple(x[2]), x[3])),
            ):
                text = "".join(chr(item[0]) for item in group)
                self.font.set_bold(dg.TA_BOLD & attr)
                self.font.set_italic(dg.TA_ITALIC & attr)
                self.font.set_underline(dg.TA_UNDERLINE & attr)
                self.font.set_strikethrough(dg.TA_STRIKETHROUGH & attr)

                if do_blink and (dg.TA_BLINK & attr):
                    text = " " * len(text)

                if dg.TA_INVERT & attr:
                    fg, bg = bg, fg

                surf = self.font.render(text, True, fg)
                blits.append((surf, (font_w * j, font_h * i)))
                self.surf.fill(bg, (font_w * j, font_h * i, font_w * len(text), font_h))
                
                j += len(text)
                
        self.surf.blits(reversed(blits))
        
        pg.display.flip()
    
    def events(self) -> list[dg.Event]:
        """Polls and processes input events from Pygame.
        
        Returns:
            A list of `dg.Event` objects.
        """
        min_r, min_c, max_r, max_c = self.get_char_shape(font=self.font)
        font_w, font_h = max_c - min_c, max_r - min_r
        out = []
        mod_raw = pg.key.get_mods()
        mod = dg.KM_NONE
        if mod_raw & pg.KMOD_SHIFT:
            mod |= dg.KM_SHIFT
        if mod_raw & pg.KMOD_META:
            mod |= dg.KM_META
        if mod_raw & pg.KMOD_CTRL:
            mod |= dg.KM_CTRL

        for event in pg.event.get():
            if event.type == pg.QUIT:
                quit()
            elif event.type == pg.KEYDOWN:
                if event.unicode and event.unicode.isprintable():
                    key = event.unicode
                else:
                    key = KEY_ATTRS.get(event.key, event.key)
                out.append(dg.KeyEvent(KEY_MAP.get(key, key), mod))
                
            elif event.type == pg.MOUSEBUTTONDOWN:
                i = event.pos[1] // font_h
                j = event.pos[0] // font_w
                out.append(dg.MouseEvent(event.button, True, (i, j), mod))
            elif event.type == pg.MOUSEBUTTONUP:
                i = event.pos[1] // font_h
                j = event.pos[0] // font_w
                out.append(dg.MouseEvent(event.button, False, (i, j), mod))
        return out

    @classmethod
    @contextlib.contextmanager
    def create(
        cls,
        shape: tuple[int, int],
        font: str = DEFAULT_FONT,
        font_size: int = 24,
    ) -> typing.Generator[typing.Self, None, None]:
        """Creates a grid of this type and performs any necessary cleanup afterward.

        This creates and manages the lifetime of the Pygame window.

        Args:
            shape: A (rows, cols) tuple for the grid's shape.
            font: The name or file path of the font to use.
            font_size: The point size of the font.
            
        Yields:
            A new PygameGrid object.
        """
        try:
            pg.init()
            scr = pg.display.set_mode(cls.get_surf_shape(shape, font, font_size))
            yield dg.PygameGrid(
                scr,
                font, 
                font_size, 
                shape,
            )
        finally:
            pg.quit()
