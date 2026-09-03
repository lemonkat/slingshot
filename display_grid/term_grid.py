"""This module provides a Grid implementation for terminal-based applications.

It uses the `urwid` library as a backend to handle terminal control codes,
mouse tracking, and color rendering.
"""
import typing
import unicodedata
import contextlib

import numpy as np
import urwid

import display_grid as dg


# KEY_MAP = {
#     # "\n": "KEY_RETURN",
#     # "\t": "KEY_TAB",
#     # " ": " ",
#     "\x1b": "KEY_ESCAPE",
#     "\x7f": "KEY_BACKSPACE",
# }

KEY_MAP = {
    "enter": "\n",
    "tab": "\t",
}

def _color_to_hex(r: int, g: int, b: int) -> str:
    """Formats RGB values as a hexadecimal code of the form #RRGGBB.
    
    Args:
        r: Red color value from 0 to 255.
        g: Green color value from 0 to 255.
        b: Blue color value from 0 to 255.

    Returns:
        A string of the form #RRGGBB.
    """
    return f"#{r:02x}{g:02x}{b:02x}"

_TEXT_ATTR_LOOKUP = {}
def _get_text_attr(fg: tuple[int, int, int], bg: tuple[int, int, int], attrs: int) -> urwid.AttrSpec:
    """Converts color and attribute data into a cached `urwid.AttrSpec` object.
    
    Args:
        fg: An (r, g, b) tuple for the foreground color.
        bg: An (r, g, b) tuple for the background color.
        attrs: A bitmask of text attributes (e.g., dg.TA_BOLD).

    Returns:
        An `urwid.AttrSpec` object for rendering.
    """
    key = *fg, *bg, attrs
    if key not in _TEXT_ATTR_LOOKUP:
        fg_str = _color_to_hex(*fg)
        if attrs & dg.TA_BOLD:
            fg_str += ",bold"
        # if attrs & dg.TA_FAINT:
        #     fg_str += ",faint"
        if attrs & dg.TA_ITALIC:
            fg_str += ",italics"
        if attrs & dg.TA_UNDERLINE:
            fg_str += ",underline"
        if attrs & dg.TA_BLINK:
            fg_str += ",blink"
        if attrs & dg.TA_INVERT:
            fg_str += ",standout"
        if attrs & dg.TA_STRIKETHROUGH:
            fg_str += ",strikethrough"
        _TEXT_ATTR_LOOKUP[key] = urwid.AttrSpec(
            fg_str,
            _color_to_hex(*bg),
            2**24 if dg.SUPPORTS_TRUECOLOR else 256
        )
    return _TEXT_ATTR_LOOKUP[key]

def _split_mod_event(event: str) -> tuple[int, str]:
    """Splits modifier prefixes from an urwid key event string.
    
    Args:
        event: An input string from urwid, e.g., "shift f1".

    Returns:
        A tuple containing the modifier bitmask and the remaining key string.
    """
    mod = dg.KM_NONE
    if event.startswith("shift "):
        mod |= dg.KM_SHIFT
        event = event[6:]
    if event.startswith("meta "):
        mod |= dg.KM_META
        event = event[5:]
    if event.startswith("ctrl "):
        mod |= dg.KM_CTRL
        event = event[5:]
    return mod, event

class TermGrid(dg.Grid):
    """A Grid that displays its contents in a terminal using `urwid`.
    
    This class handles rendering the grid's data to a terminal screen and
    translating terminal input into `display_grid` events.
    
    Attributes:
        scr (urwid.display.raw.Screen): The urwid screen object for output.
    """
    def __init__(
        self,
        scr: urwid.display.raw.Screen,
        shape: typing.Optional[tuple[int, int]] = None,
    ) -> None:
        """Constructs a TermGrid.
        
        Args:
            scr: An `urwid.display.raw.Screen` to draw on.
            shape: A (rows, cols) tuple for the grid's shape. If None, it
                defaults to the screen size.
        """
        
        self.scr = scr
        scr.set_mouse_tracking(True)
        scr.clear()
        
        if shape is None:
            shape = self.get_real_shape()

        colors = np.empty((*shape, 2, 3), dtype=np.uint8)
        chars = np.empty(shape, dtype=np.int32)
        attrs = np.empty(shape, dtype=np.uint8)

        super().__init__(colors, chars, attrs)   

    def draw(self) -> None:
        """Renders the grid's contents to the terminal screen."""
        markup = []
        for chars, fg, bg, attrs in zip(self.chars, self.fg, self.bg, self.attrs):
            i = 0
            while i < len(chars):
                markup.append((_get_text_attr(fg[i], bg[i], attrs[i]), chr(chars[i])))
                i += 2 if unicodedata.east_asian_width(chr(chars[i])) in "WF" else 1
            markup.append("\n")
        self.scr.draw_screen(self.shape[::-1], urwid.Text(markup[:-1], wrap="clip").render(self.shape[1:]) )

    def get_real_shape(self) -> tuple[int, int]:
        """Gets the current size of the terminal window.
        
        Returns:
            A (rows, cols) tuple of the terminal size.
        """
        return self.scr.get_cols_rows()[::-1]
    
    def events(self) -> list[dg.Event]:
        """Polls and processes input events from the terminal.
        
        Returns:
            A list of `dg.Event` objects.
        """
        out = []
        for event in self.scr.get_input():
            if isinstance(event, str):
                mod, key = _split_mod_event(event)
                out.append(dg.KeyEvent(KEY_MAP.get(key, key), mod))
            else:
                action, button, x, y = event
                mod, action = _split_mod_event(action)
                out.append(dg.MouseEvent(button, "press" in action, (y, x), mod))
        return out

    @classmethod
    @contextlib.contextmanager
    def create(
        cls,
        shape: tuple[int, int],
    ) -> typing.Generator[typing.Self, None, None]:
        """Creates a grid of this type and performs any necessary cleanup afterward.

        This creates and manages the lifetime of the Urwid screen.

        Args:
            shape: A (rows, cols) tuple for the grid's shape.
            
        Yields:
            A new TermGrid object.
        """
        try:
            scr = urwid.display.raw.Screen()
            scr.start()
            scr.set_input_timeouts(max_wait=0)
            scr.set_mouse_tracking()
            yield dg.TermGrid(scr, shape)
        finally:
            scr.stop()