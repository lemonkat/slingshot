"""This file contains constants used throughout the display_grid package.

TA_* constants represent text attributes (e.g., bold, italic) and are used
as bitmasks.

KM_* constants represent keyboard modifiers (e.g., shift, ctrl) and are used
as bitmasks.
"""
TA_NONE = 0
TA_BOLD = 1
# TA_FAINT = 2
TA_ITALIC = 4
TA_UNDERLINE = 8
TA_BLINK = 16
TA_INVERT = 32
TA_STRIKETHROUGH = 64

KM_NONE = 0
KM_SHIFT = 1
KM_META = 2
KM_CTRL = 4