# Keys of the interface: (key, bottom bar legend, help description), in
# the order they appear in the legend and in the help pop-up. Both are
# built from this table, so they cannot drift apart. Keys whose legend
# is None (the arrow keys) only appear in the pop-up.
KEYMAP = (
    ("Q", "QUIT", "Quit the simulator"),
    ("P", "RUN/STOP", "Run the program or pause it"),
    ("F10", "STEP", "Execute one instruction"),
    ("↑/↓", None, "Scroll the store view"),
    ("I", "SPEED UP", "Increase the execution speed"),
    ("K", "SPEED DOWN", "Decrease the execution speed"),
    ("D", "DISPLAY", "Cycle the bit representations"),
    ("B", "BREAKPT", "Open the breakpoint pop-up"),
    ("H", "HELP", "Toggle this help pop-up"),
)


def legend_segments():
    """The bottom bar segments built from KEYMAP: (text, highlighted)

    Single-character keys are padded like " Q ", longer ones ("F10")
    are drawn as-is.
    """
    segments = []
    for key, legend, _ in KEYMAP:
        if legend is None:
            continue
        key_text = f" {key} " if len(key) == 1 else key
        segments.append((key_text, True))
        segments.append((f" {legend}  ", False))
    return segments


def help_key_column() -> int:
    """Width of the highlighted key column in the help pop-up

    The widest key plus one space on each side, so every label sits
    centered in its reverse box, away from the description.
    """
    return max(len(key) for key, _, _ in KEYMAP) + 2
