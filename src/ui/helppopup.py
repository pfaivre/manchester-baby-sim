import curses

from src.ui.keymap import KEYMAP, help_key_column
from src.ui.popup import draw_box, popup_geometry, popup_line
from src.ui.theme import PAIR_UI


class HelpPopup:
    """The help pop-up, listing the keys of the interface

    The window is built from KEYMAP, the same table as the bottom bar
    legend, and truncated when the terminal cannot fit it. It is created
    on open and recreated on every resize while open, since its size and
    position depend on the terminal (see open).
    """

    TITLE = "SSEM SIMULATOR"
    FOOTER = "Press H to close"

    def __init__(self):
        self.window = None

    @property
    def is_open(self) -> bool:
        return self.window is not None

    def geometry(self, lines: int, cols: int) -> tuple[int, int, int, int]:
        """Height, width, y and x of the pop-up for a terminal size

        The pop-up is centered, and clamped to the terminal: on a small
        terminal its drawing is truncated rather than overflowing.
        """
        key_column = help_key_column()
        content_width = max(
            len(self.TITLE),
            len(self.FOOTER),
            key_column + 1 + max(len(description) for _, _, description in KEYMAP),
        )
        # 2 border columns, one left margin and one spare column before the
        # right border: no text can then reach the last cell of a line
        width = content_width + 4
        # Interior lines: title, blank, one line per key, blank, footer
        height = len(KEYMAP) + 6
        return popup_geometry(height, width, lines, cols)

    def open(self, stdscr):
        """(Re)create the pop-up window, centered on the terminal

        Called when the pop-up opens and again on every resize while it is
        open, since its size and position depend on the terminal.
        """
        lines, cols = stdscr.getmaxyx()
        height, width, y, x = self.geometry(lines, cols)
        key_column = help_key_column()
        window = curses.newwin(height, width, y, x)
        self.window = window

        draw_box(window)

        def add_line(row, col, text, attributes=None):
            popup_line(window, row, col, text, height, width, attributes)

        # Title, centered on the window
        add_line(1, max(1, (width - len(self.TITLE)) // 2), self.TITLE, curses.A_BOLD)

        # One line per key: the key centered in its box, the description
        # following
        for i, (key, _, description) in enumerate(KEYMAP):
            if 3 + i >= height - 2:
                break  # No interior room left: the rest is truncated away
            add_line(3 + i, 1, f"{key:^{key_column}}", curses.A_REVERSE | curses.color_pair(PAIR_UI))
            add_line(3 + i, 2 + key_column, description)

        if height > 3:
            add_line(height - 2, 1, self.FOOTER)

    def close(self):
        """Erase the pop-up from the virtual screen and drop it

        The pop-up can extend beyond the store pad — to its right, and over
        the bottom bar — and no other window repaints those regions, so its
        rectangle must be blanked by the window itself. The bottom bar and
        the store are the interface's business: closing goes through
        CommandInterface, which touches them back.
        """
        self.window.erase()
        self.window.noutrefresh()
        self.window = None

    def compose(self):
        """Copy the pop-up to the virtual screen, above the store pad

        A refresh only copies the lines touched since the window's last
        refresh, and the pad repaints its own lines at every frame:
        touchwin forces the full copy, keeping the pop-up on top.
        """
        self.window.touchwin()
        self.window.noutrefresh()
