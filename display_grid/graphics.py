"""This module handles loading character-based graphics from text files.

The graphics are stored as NumPy arrays of Unicode ordinals in a global
dictionary for easy access throughout the application.
"""
import os

import numpy as np

GRAPHICS: dict[str, np.ndarray[np.int32]] = {}

def load_graphics(path: str = "assets/") -> None:
    """Loads all `.txt` files from a directory into the `GRAPHICS` dictionary.

    Each file is parsed into a NumPy array of character ordinals. The graphic
    is stored in the `GRAPHICS` dictionary under a key corresponding to its
    filename without the `.txt` extension. Lines in the file are padded with
    spaces to ensure all rows in the array have the same length.

    Args:
        path: The path to the directory containing the graphic files.
    """
    for file_path in os.listdir(path):
        if file_path.endswith(".txt"):
            with open(path + file_path, "r") as file:
                raw = file.read().splitlines()
                if not raw:
                    GRAPHICS[file_path[:-4]] = np.array([[]], dtype=np.int32)
                    continue
                max_len = max(len(line) for line in raw)
                padded_raw = [line.ljust(max_len) for line in raw]
                GRAPHICS[file_path[:-4]] = np.array(
                    [[ord(c) for c in line] for line in padded_raw],
                    dtype=np.int32,
                )