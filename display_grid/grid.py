"""This module defines the core Grid class and its SubGrid variant.

The Grid class is the fundamental data structure for representing a character-based
display region, using NumPy arrays for efficient manipulation of characters,
colors, and text attributes.
"""
import typing
import contextlib

import numpy as np

import display_grid as dg

class Grid:
    """A Grid represents a rectangular region of characters on a screen.

    It stores characters, foreground/background colors, and display attributes
    as NumPy arrays. The coordinate system originates from the top-left corner (row, col).

    Attributes:
        shape (tuple[int, int]): The dimensions of the grid (rows, cols).
        colors (np.ndarray): A NumPy array of shape (rows, cols, 2, 3) storing
            RGB color data. The third axis is for foreground (0) and background (1).
        chars (np.ndarray): A NumPy array of shape (rows, cols) where each int32
            value is the Unicode ordinal of a character.
        attrs (np.ndarray): A NumPy array of shape (rows, cols) where each uint8
            value is a bitmask of text attributes (e.g., dg.TA_BOLD).
        fg (np.ndarray): A view of the foreground colors of shape (rows, cols, 3).
        bg (np.ndarray): A view of the background colors of shape (rows, cols, 3).
        offset (tuple[int, int]): If this is a SubGrid, the (row, col) offset
            within its parent grid. Otherwise, (0, 0).
    """
    def __init__(
        self,
        colors: np.ndarray[np.uint8],
        chars: np.ndarray[np.int32],
        attrs: np.ndarray[np.uint8],
    ) -> None:
        """Initializes a Grid object with the specified data arrays.

        Args:
            colors: A NumPy array for color data with shape (rows, cols, 2, 3).
            chars: A NumPy array for character data with shape (rows, cols).
            attrs: A NumPy array for attribute data with shape (rows, cols).
        """
        self.shape = chars.shape
        self.colors, self.chars, self.attrs = colors, chars, attrs
        self.offset = 0, 0
        self.fg, self.bg = self.colors[:, :, 0], self.colors[:, :, 1]

    def clear(self) -> None:
        """Resets the grid to a default state.
        
        Sets the foreground to white, background to black, characters to spaces,
        and clears all text attributes.
        """
        self.fill(" ", (255, 255, 255), (0, 0, 0), dg.TA_NONE)

    def print(
        self,
        *values: object,
        pos: tuple[int, int] = (0, 0),
        fg: typing.Optional[tuple[int, int, int]] = None,
        bg: typing.Optional[tuple[int, int, int]] = None,
        attrs: typing.Optional[int] = None,
        sep: str = " ",
    ) -> None:
        """Prints text to the grid, wrapping at the edges.
        
        Args:
            values: One or more objects to print, converted to strings.
            pos: The starting (row, col) position for the text.
            fg: An optional (r, g, b) tuple for the foreground color.
            bg: An optional (r, g, b) tuple for the background color.
            attrs: An optional bitmask of text attributes (e.g., dg.TA_BOLD).
            sep: The separator to use between values.
        """
        text = sep.join(str(val) for val in values)
        start = np.ravel_multi_index(pos, self.shape)
        for i, char in enumerate(text):
            pos = np.unravel_index(start + i, self.shape)
            self.chars[pos] = ord(char)
            if fg is not None:
                self.fg[pos] = fg
            if bg is not None:
                self.bg[pos] = bg
            if attrs is not None:
                self.attrs[pos] = attrs

    def fill(
        self,
        char: typing.Optional[str] = None,
        fg: typing.Optional[tuple[int, int, int]] = None,
        bg: typing.Optional[tuple[int, int, int]] = None,
        attrs: typing.Optional[int] = None,
    ) -> None:
        """Fills the entire grid with a given character, color, and/or attribute.

        To fill a sub-region, create and fill a `SubGrid` instead.

        Args:
            char: The character to fill with. If None, characters are unchanged.
            fg: The (r, g, b) foreground color. If None, color is unchanged.
            bg: The (r, g, b) background color. If None, color is unchanged.
            attrs: The text attribute bitmask. If None, attributes are unchanged.
        """
        if char is not None:
            self.chars[...] = ord(char)
        if fg is not None:
            self.fg[...] = fg
        if bg is not None:
            self.bg[...] = bg
        if attrs is not None:
            self.attrs[...] = attrs

    def stamp(self, name: str, i: int, j: int, ignore_space: bool = False) -> None:
        """Draws a pre-loaded graphic onto the grid.

        The graphic, identified by `name`, is retrieved from the `dg.GRAPHICS`
        dictionary and its character data is copied to the grid, with the
        top-left corner of the graphic positioned at `(i, j)`.

        Args:
            name: The key of the graphic to load from `dg.GRAPHICS`.
            i: The top row for the graphic's position.
            j: The left column for the graphic's position.
        """
        arr = dg.GRAPHICS[name]
        if ignore_space:
            self.chars[i: i + arr.shape[0], j: j + arr.shape[1]][arr != ord(" ")] = arr[arr != ord(" ")]
        else:
            self.chars[i: i + arr.shape[0], j: j + arr.shape[1]] = arr
    
    def draw(self) -> None:
        """Updates the physical screen with the contents of this Grid.
        
        This method is a placeholder in the base class and should be implemented
        by subclasses like `TermGrid` or `PygameGrid`.
        """
        pass

    def get_real_shape(self) -> tuple[int, int]:
        """Returns the actual shape of the display window.
        
        This can be used to check if the user's window is large enough.
        The base Grid class returns its own shape. Subclasses should override this
        to query the actual display size.
        
        Returns:
            A (rows, cols) tuple of the display window's shape.
        """
        return self.shape
    
    def events(self) -> list[dg.Event]:
        """Collects and returns recent user input events.
        
        This method is a placeholder in the base class. Subclasses should
        override it to poll for and return a list of `dg.Event` objects.

        Returns:
            A list of `dg.Event` objects.
        """
        return []

    @classmethod
    @contextlib.contextmanager
    def create(cls, shape: tuple[int, int]) -> typing.Generator[typing.Self, None, None]:
        """Creates a grid of this type and performs any necessary cleanup afterward.

        Args:
            shape: a tuple (rows, cols) for the shape of the resulting Grid.

        Yields:
            A new Grid object.
        """
        yield Grid(
            np.full((*shape, 2, 3), 255, dtype=np.uint8),
            np.full(shape, ord(" "), dtype=np.int32),
            np.full(shape, dg.TA_NONE, dtype=np.uint8),
        )


class SubGrid(Grid):
    """A SubGrid is a view into a rectangular sub-region of another Grid.

    Modifications to the SubGrid's data arrays directly affect the parent Grid.

    Attributes:
        parent (Grid): The Grid object that this SubGrid is a view of.
    """
    def __init__(self, parent: Grid, i1: int, j1: int, i2: int, j2: int) -> None:
        """Constructs a SubGrid from a parent Grid and a bounding box.
        
        Args:
            parent: The parent Grid object.
            i1: The top row of the sub-region.
            j1: The left column of the sub-region.
            i2: The bottom row (exclusive) of the sub-region.
            j2: The right column (exclusive) of the sub-region.
        """
        self.parent = parent
        super().__init__(
            parent.colors[i1:i2, j1:j2],
            parent.chars[i1:i2, j1:j2],
            parent.attrs[i1:i2, j1:j2],
        )
        self.offset = i1, j1

    def draw(self) -> None:
        """Updates the screen by calling the parent's draw method."""
        self.parent.draw()

    @classmethod
    @contextlib.contextmanager
    def create(cls, parent: Grid, i1: int, j1: int, i2: int, j2: int) -> typing.Generator[typing.Self, None, None]:
        """Creates a grid of this type and performs any necessary cleanup afterward.

        This is identical to calling the SubGrid constructor.

        Args:
            parent: The parent Grid object.
            i1: The top row of the sub-region.
            j1: The left column of the sub-region.
            i2: The bottom row (exclusive) of the sub-region.
            j2: The right column (exclusive) of the sub-region.

        Yields:
            A new SubGrid object.
        """
        yield SubGrid(parent, i1, j1, i2, j2)