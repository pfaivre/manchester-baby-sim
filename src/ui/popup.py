import curses


def popup_geometry(height: int, width: int, lines: int, cols: int) -> tuple[int, int, int, int]:
    """Clamp a pop-up to the terminal and center it

    On a small terminal the pop-up is truncated rather than overflowing.
    """
    height, width = min(height, lines), min(width, cols)
    return height, width, max(0, (lines - height) // 2), max(0, (cols - width) // 2)


def draw_box(window):
    """Draw the border of a pop-up window

    The window can fill the whole terminal when clamped: its bottom-right
    corner is then the last cell of the last line, where writing makes
    addstr error, so box() is guarded like every write.
    """
    try:
        window.box()
    except curses.error:
        pass  # Degenerated terminal: keep whatever border was drawn


def popup_line(window, row: int, col: int, text: str, height: int, width: int, attributes=None):
    """Write one line of a pop-up window, clipped to its interior

    On a degenerated terminal the text is truncated (or dropped) rather
    than making addstr return an error.
    """
    if row > height - 2 or col >= width - 1:
        return
    text = text[:width - 2 - col]
    try:
        if attributes:
            window.addstr(row, col, text, attributes)
        else:
            window.addstr(row, col, text)
    except curses.error:
        pass  # Degenerated terminal: draw what fits, ignore the rest
