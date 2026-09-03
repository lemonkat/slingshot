"""This module provides a component-based architecture for building applications.

The core class is `Module`, which represents a rectangular region of the screen
with its own drawing, event handling, and update logic. Applications are built
by composing Modules and Sub-Modules. Several pre-built modules for common UI
elements like buttons, text input, and FPS meters are also included.
"""
import time
import typing

import numpy as np

import display_grid as dg

M = typing.TypeVar("M", bound="Module")

class Module:
    """A hierarchical component for managing a region of a grid.
    
    Modules provide a layer of abstraction over Grid objects. They can be nested
    to create complex UIs. A module manages its own sub-region of a parent grid,
    handles its own drawing and event logic, and can contain child modules.
    
    Event propagation flows from parent to child. Update ticks and drawing calls
    also propagate down the hierarchy.
    
    Attributes:
        parent (Module | None): The parent module, or None if this is a root module.
        grid (dg.Grid): The Grid or SubGrid this module draws to.
        submodules (list[Module]): A list of child modules.
        paused (bool): If True, the module is inactive (ignores events, drawing,
            and ticks).
        shape (tuple[int, int]): The (rows, cols) shape of the module's grid.
        box (tuple[int, int, int, int]): The (i0, j0, i1, j1) bounding box of
            this module's grid within its parent's grid.
    """
    
    def __init__(
        self, 
        parent: typing.Optional[M] = None, 
        box: typing.Optional[tuple[int, int, int, int]] = None, 
        grid: typing.Optional[dg.Grid] = None,
    ) -> None:
        """Constructs a Module.

        Args:
            parent: The parent Module. If provided, this module becomes a child
                of the parent and uses a SubGrid of the parent's grid.
            box: A tuple (i0, j0, i1, j1) for the module's bounding box within
                the parent's grid. Ignored if `parent` is None. Negative
                coordinates are relative to the parent's far edge.
            grid: The Grid to draw to. Ignored if `parent` is not None.
        """

        self.parent = parent
        if parent:
            self.grid = parent.grid if box is None else dg.SubGrid(parent.grid, *box)
            parent.submodules.append(self)
        else:
            self.grid = grid if box is None else dg.SubGrid(grid, *box)


        self.submodules: list[M] = []
        self.paused = False
        self.shape = self.grid.shape
        bound = self.parent.shape if parent else self.shape
        if box is None:
            self.box = 0, 0, *self.shape
        else:
            self.box = box[0] % bound[0], box[1] % bound[1], box[2] % bound[0], box[3] % bound[1]

    def start(self) -> None:
        """Activates the module, allowing it to be drawn and updated."""
        self.paused = False

    def stop(self) -> None:
        """Deactivates the module. It will not be drawn or updated."""
        self.paused = True

    def draw(self) -> None:
        """Draws this module and its submodules to the grid.
        
        The module's own `_draw` method is called first, followed by the `draw`
        method of each of its submodules.
        """
        if not self.paused:
            self._draw()
            for module in reversed(self.submodules):
                module.draw()
            
    def _draw(self) -> None:
        """The specific drawing logic for this module. Should be overridden."""
        pass

    def tick(self) -> None:
        """Updates this module and its submodules.
        
        The `tick` method of each submodule is called first, followed by this
        module's own `_tick` method.
        """
        if not self.paused:
            for module in self.submodules:
                module.tick()
            self._tick()
            
    def _tick(self) -> None:
        """The specific update logic for this module. Should be overridden."""
        pass

    def handle_event(self, event: dg.Event) -> bool:
        """Handles a user input event, propagating it to submodules first.

        Args:
            event: The `dg.Event` to handle.

        Returns:
            True if the event was handled by this module or one of its
            submodules, False otherwise.
        """
        if self.paused:
            return False
        for module in self.submodules:
            if isinstance(event, dg.MouseEvent):
                i, j = event.pos
                i0, j0, i1, j1 = module.box
                if i0 <= i < i1 and j0 <= j < j1 and module.handle_event(dg.MouseEvent(event.button, event.state, (i - i0, j - j0), event.mod)):
                    return True
            elif isinstance(event, dg.KeyEvent):
                if module.handle_event(event):
                    return True
        return self._handle_event(event)
    
    def _handle_event(self, event: dg.Event) -> bool:
        """The specific event handling logic for this module. Should be overridden.

        Args:
            event: The `dg.Event` to handle.

        Returns:
            True if the event was handled, False otherwise.
        """
        return False

class MainModule(Module):
    """The root module for an application.
    
    This module serves as the main entry point for the application's lifecycle
    (tick, draw, events). It can also enforce a specific window size. Display
    backend setup is handled by the Grid subclass's ``create`` classmethod.
    """
    def __init__(
        self, 
        grid: dg.Grid,
        enforce_shape: bool = True, 
    ) -> None:
        """Constructs the MainModule.

        Args:
            grid: The Grid object to display on.
            enforce_shape: If True, displays a warning if the window size does
                not match `shape` and pauses updates.
        """
        super().__init__(grid=grid)
        self.grid.clear()
        self.enforce_shape = enforce_shape

    def draw(self) -> None:
        """Draws this module and its submodules to the grid, clearing the grid first.
        
        The module's own `_draw` method is called first, followed by the `draw`
        method of each of its submodules.
        """

        self.grid.clear()
        real_shape = self.grid.get_real_shape()
        if self.enforce_shape and real_shape != self.shape:
            self.grid.clear()
            self.grid.chars[:] = ord("█")
            self.grid.chars[1:-1, 2:-2] = ord(" ")
            
            self.grid.print(
                f"Please ensure the window size is {self.shape[0]}x{self.shape[1]}.", pos=(2, 4), 
                fg=(255, 255, 0), 
                bg=(0, 0, 0),
            )
            self.grid.print(
                f"The current window size is {real_shape[0]}x{real_shape[1]}.", 
                pos=(3, 4), 
                fg=(255, 255, 0), 
                bg=(0, 0, 0),
            )
            self.grid.draw()
        else:
            super().draw()
            self.grid.draw()
            
    def _tick(self) -> None:
        """Polls for events if the window shape is correct."""
        if not self.enforce_shape or self.grid.get_real_shape() == self.shape:
            for event in self.grid.events():
                self.handle_event(event)
        else:
            self.grid.events()


class ArrayDrawModule(Module):
    """A module for displaying a NumPy array of RGB data as colored blocks."""
    def __init__(
        self, 
        parent: Module, 
        box: typing.Optional[tuple[int, int, int, int]] = None, 
        res: int = 1,
    ) -> None:
        """Constructs an ArrayDrawModule.

        Args:
            parent: The parent module.
            box: The bounding box within the parent.
            res: An integer scaling factor for the array.
        """
        super().__init__(parent, box)
        self.res = res
        
    def update(self, arr: np.ndarray[np.uint8]) -> None:
        """Updates the module's display with a new array.

        The top half of each character cell gets its color from one row of the
        array, and the bottom half gets its color from the next row.

        Args:
            arr: A NumPy array of shape (height, width, 3) with RGB data.
        """
        arr = np.tile(arr, (self.res, self.res))
        self.grid.chars[:] = ord(dg.BLOCKS[9]) # "▀" character
        self.grid.fg[:] = arr[::2, :, :]
        self.grid.bg[:] = arr[1::2, :, :]

class BarModule(Module):
    """A module for drawing a single horizontal or vertical bar."""
    def __init__(
        self,
        parent: Module,
        box: typing.Optional[tuple[int, int, int, int]] = None,
        direction: int = 0, # 0=+i, 1=+j, 2=-i, 3=-j
    ) -> None:
        """Constructs a BarModule.

        Args:
            parent: The parent module.
            box: The bounding box within the parent.
            direction: The orientation of the bar (0: down, 1: right, 2: up, 3: left).
        """
        super().__init__(parent, box)
        horz, inv = direction % 2, direction // 2

        self.blocks = [dg.BLOCKS, dg.HORZ_BLOCKS][horz][:-1][::2 * (inv != horz) - 1]
        fg, bg = (self.grid.fg, self.grid.bg)[::2 * (inv == horz) - 1]
        self.fg, self.bg, self.chars, self.attrs = [np.moveaxis(a, horz, 0)[::1 - 2 * inv] for a in [fg, bg, self.grid.chars, self.grid.attrs]]

        self.length = self.box[2 + horz] - self.box[horz]
        self.data = np.zeros((self.length * 8, 3), dtype=np.uint8)
        self.nonempty = np.zeros(self.length, dtype=bool)

    def update(self, p0: float, p1: float, color: tuple[int, int, int]) -> None:
        """Sets a segment of the bar to a specific color.

        Args:
            p0: The starting position along the bar's length.
            p1: The ending position along the bar's length.
            color: The (r, g, b) color for the segment.
        """
        p0, p1 = np.clip([min(p0, p1), max(p0, p1)], 0, self.length)
        self.data[int(p0 * 8): int(p1 * 8)] = color
        self.nonempty[int(p0): int(np.ceil(p1))] = True
    
    def reset(self) -> None:
        """Clears all data from the bar."""
        self.data[:] = 0
        self.nonempty[:] = False

    def _draw(self) -> None:
        """Draws the bar to the grid using sub-character blocks."""
        self.fg[self.nonempty] = self.data[7::8, None][self.nonempty]
        self.bg[self.nonempty] = self.data[::8, None][self.nonempty]
        self.chars[self.nonempty] = np.array([ord(b) for b in self.blocks])[np.argmax(np.all(self.data.reshape(-1, 8, 3) == self.data[7::8, None], axis=2), axis=1)][self.nonempty, None]
        self.attrs[self.nonempty] = dg.TA_NONE
        
class ButtonTrigger(Module):
    """A clickable, invisible module that triggers functions on mouse events."""
    def __init__(
        self,
        parent: Module,
        box: typing.Optional[tuple[int, int, int, int]] = None,
        button: int = 0,
        mod: int = dg.KM_NONE,
        down_fn: typing.Callable[[], None] = lambda: None,
        up_fn: typing.Callable[[], None] = lambda: None,
    ) -> None:
        """Constructs a ButtonTrigger.

        Args:
            parent: The parent module.
            box: The bounding box for the clickable area.
            button: The mouse button to react to.
            mod: The required keyboard modifier mask.
            down_fn: The function to call on mouse button down.
            up_fn: The function to call on mouse button up.
        """
        super().__init__(parent, box)
        self.down_fn = down_fn
        self.up_fn = up_fn
        self.button = button
        self.mod = mod
    
    def _handle_event(self, event: dg.Event) -> bool:
        """Handles mouse events and triggers the appropriate function."""
        if isinstance(event, dg.MouseEvent) and event.button == self.button and event.mod == self.mod:
            if event.state:
                self.down_fn()
            else:
                self.up_fn()
            return True
        return False
    
class KeyTrigger(Module):
    """An invisible module that triggers a function on a specific key press."""
    def __init__(
        self,
        parent: Module,
        box: typing.Optional[tuple[int, int, int, int]] = None,
        key: str = " ",
        mod: int = dg.KM_NONE,
        fn: typing.Callable[[], None] = lambda: None,
    ) -> None:
        """Constructs a KeyTrigger.

        Args:
            parent: The parent module.
            box: The bounding box (not used for key triggers, but part of the API).
            key: The key to react to (e.g., "a", "KEY_ENTER").
            mod: The required keyboard modifier mask.
            fn: The function to call when the key is pressed.
        """
        super().__init__(parent, box)
        self.fn = fn
        self.key = key
        self.mod = mod
    
    def _handle_event(self, event: dg.Event) -> bool:
        """Handles key events and triggers the function if it matches."""
        if isinstance(event, dg.KeyEvent) and event.key == self.key and event.mod == self.mod:
            self.fn()
            return True
        return False
    
class TextInputModule(Module):
    """A single-line text input field.
    
    Handles basic text entry, cursor movement, and backspace.
    """
    def __init__(
        self, 
        parent: Module,
        box: typing.Optional[tuple[int, int, int, int]] = None,
        start_text: str = "", 
        empty_text: str = "",
        fg_color: tuple[int, int, int] = [255, 255, 255],
        bg_color: tuple[int, int, int] = [0, 0, 0],
        empty_color: tuple[int, int, int] = [127, 127, 127],
    ) -> None:
        """Constructs a TextInputModule.

        Args:
            parent: The parent module.
            box: The bounding box for the text field.
            start_text: The initial text in the field.
            empty_text: Placeholder text to display when the field is empty.
            fg_color: The color of the text.
            bg_color: The background color of the field.
            empty_color: The color of the placeholder text.
        """
        super().__init__(parent, box)
        self.text = list(start_text)
        self.scroll_pos = max(0, len(start_text) - self.shape[1])
        self.cursor_pos = len(start_text)
        self.empty_text = empty_text
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.empty_color = empty_color

    def _draw(self) -> None:
        """Draws the text field, cursor, and placeholder text."""
        self.grid.fill(" ", self.bg_color, self.bg_color)
        if self.text:
            text = "".join(self.text[self.scroll_pos:self.scroll_pos + self.shape[1]])
            if self.scroll_pos > 0:
                text = "<" + text[1:]
            if len(self.text) > self.shape[1] + self.scroll_pos:
                text = text[:-1] + ">"
            
            self.grid.print(text, (0, 0), self.fg_color, self.bg_color)
            self.grid.fg[0, self.cursor_pos - self.scroll_pos] = self.bg_color
            self.grid.bg[0, self.cursor_pos - self.scroll_pos] = self.fg_color

        else:
            self.grid.print(self.empty_text, (0, 0), self.empty_color, self.bg_color)
        
    def _handle_event(self, event: dg.Event) -> bool:
        """Handles key and mouse events for text input and cursor control."""
        if isinstance(event, dg.MouseEvent):
            self.cursor_pos = event.pos[1] + self.scroll_pos
            return True
        elif isinstance(event, dg.KeyEvent):
            if event.key == "KEY_BACKSPACE":
                if self.cursor_pos > 0:
                    self.text.pop(self.cursor_pos - 1)
                    self.cursor_pos -= 1
                    if self.cursor_pos < self.scroll_pos:
                        self.scroll_pos = max(0, self.scroll_pos - 1)
                return True
            elif event.key == "KEY_LEFT":
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
                    if self.cursor_pos < self.scroll_pos:
                        self.scroll_pos = max(0, self.scroll_pos - 1)
                return True
            elif event.key == "KEY_RIGHT":
                if self.cursor_pos < len(self.text):
                    self.cursor_pos += 1
                    if self.cursor_pos >= self.shape[1] + self.scroll_pos:
                        self.scroll_pos += 1
                return True
            elif len(event.key) == 1 and event.key.isprintable():
                self.text.insert(self.cursor_pos, event.key)
                self.cursor_pos += 1
                if self.cursor_pos >= self.shape[1] + self.scroll_pos:
                    self.scroll_pos += 1
                return True
            return False

    def __str__(self) -> str:
        """Returns the current text content of the module."""
        return "".join(self.text)

class FPSMeter(Module):
    """A module that displays the current frames per second."""
    def __init__(
        self, 
        parent: Module, 
        box: typing.Optional[tuple[int, int, int, int]] = None,
    ) -> None:
        """Constructs an FPSMeter.

        Args:
            parent: The parent module.
            box: The bounding box for the meter. Recommended shape is 1x8.
        """
        super().__init__(parent, box)
        self.avg = 60
        self.last_time = time.time()

    def _tick(self) -> None:
        """Calculates the FPS based on the time since the last tick."""
        cur_time = time.time()
        fps = 1 / (cur_time - self.last_time)
        self.last_time = cur_time
        self.avg = 0.9 * self.avg + 0.1 * fps

    def _draw(self) -> None:
        """Displays the calculated FPS."""
        if self.shape[0] == 1:
            self.grid.print("FPS:" + str(int(self.avg)).rjust(self.shape[1] - 4))
        else:
            self.grid.print("FPS:")
            self.grid.print(str(int(self.avg)).ljust(self.shape[1]), (1, 0))
        
class BorderModule(Module):
    """A module that draws a border around its perimeter."""
    def __init__(
        self, 
        parent: Module, 
        box: typing.Optional[tuple[int, int, int, int]] = None, 
        depth: int = 1.0,
    ) -> None:
        """Constructs a BorderModule.

        Args:
            parent: The parent module.
            box: The bounding box for the border.
            depth: The thickness of the border in characters.
        """
        super().__init__(parent, box)
        self.depth = depth
        self.inner_box = int(np.ceil(depth / 2)), depth, self.shape[0] - int(np.ceil(depth / 2)), self.shape[1] - depth

    def _draw(self) -> None:
        """Draws the border using block characters."""
        self.grid.chars[:self.depth // 2, :] = ord("█")
        self.grid.chars[-(self.depth // 2):, :] = ord("█")
        
        if self.depth % 2 == 1:
            self.grid.chars[self.depth // 2, :] = ord("▀")
            self.grid.chars[-(self.depth // 2) - 1, :] = ord("▄") 

        self.grid.chars[:, :self.depth] = ord("█")
        self.grid.chars[:, -self.depth:] = ord("█")

class TabModule(Module):
    """A container module that manages a list of other modules as tabs.
    
    Only one tab is active (visible and interactive) at a time.
    """
    def __init__(
        self, 
        parent: Module, 
        box: typing.Optional[tuple[int, int, int, int]] = None,
        tabs: typing.Optional[list[Module]] = None,
    ) -> None:
        """Constructs a TabModule.

        Args:
            parent: The parent module.
            box: The bounding box for the tab content area.
            tabs: A list of modules to be used as tabs.
        """
        super().__init__(parent, box)
        self.tabs = []
        self._index = None
        if tabs:
            self.tabs = tabs
            for tab in self.tabs:
                tab.stop()
            self.index = 0
            
    @property
    def index(self) -> int:
        """The index of the currently active tab."""
        return self._index
    
    @index.setter
    def index(self, value: typing.Optional[int]) -> None:
        """Sets the active tab by its index."""
        if self._index is not None:
            self.tabs[self._index].stop()
        self._index = value
        if self._index is not None:
            self.tabs[self._index].start()

    @property
    def tab(self) -> typing.Optional[Module]:
        """The currently active tab module."""
        return self.tabs[self._index]
    
    @tab.setter
    def tab(self, value: typing.Optional[Module]) -> None:
        """Sets the active tab by its module instance."""
        if value is None:
            self.index = None
        else:
            self.index = self.tabs.index(value)