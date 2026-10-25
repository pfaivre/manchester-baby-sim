# The visual styles of the interface

# Color pairs, as curses color pair numbers
PAIR_STORE = 1  # Bits and registers (green)
PAIR_UI = 2  # Top bar and key legend (blue)

# The characters representing a set (on) and a cleared (off) bit, in the
# order they are cycled through by the D key
BIT_REPRESENTATIONS = (
    ("#", "."),  # High contrast ASCII characters
    ("−", "·"),  # Fancy characters for more accurate display
    ("_", "."),  # ASCII compatible characters
    ("1", "0"),  # 0s and 1s
)
