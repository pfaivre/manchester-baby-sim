import curses

from src.machines.breakpoints import CiValue, WordValue
from src.ui.popup import draw_box, popup_geometry, popup_line
from src.ui.theme import PAIR_UI


class BreakpointPopup:
    """The breakpoint pop-up: the list of the machine's breakpoints and an input line

    While open the pop-up is rebuilt at every frame (see rebuild): its
    geometry depends on the terminal size and on the number of
    breakpoints. The machine's breakpoints are appended and removed here,
    from the interface thread, while the machine reads them after every
    cycle.
    """

    TITLE = "BREAKPOINTS"
    EXPLANATION = "Pause the machine when a condition is met"
    FOOTER = "ENTER add · T type · ↑/↓ select · X delete · ESC close"

    # Condition types of a new breakpoint, cycled with the T key: the word
    # value takes an address then a value, the CI value only an address
    KIND_WORD = 0
    KIND_CI = 1

    # Fields of the input line, typed one after the other
    ADDRESS = 0
    VALUE = 1

    def __init__(self, machine):
        self.machine = machine
        self.is_open = False
        self.window = None  # The pop-up window, rebuilt at every frame while open
        # Edition state: the condition type, the field being typed, the
        # digits typed so far, the address accepted for the current
        # breakpoint, the selected line of the list, and a message line
        self.kind = self.KIND_WORD
        self.field = self.ADDRESS
        self.buffer = ""
        self.address = 0
        self.selected = 0
        self.message = ""

    def open(self):
        """Open the pop-up, resetting its edition state

        The window itself is built by the next frame: its geometry depends
        on the terminal size and on the number of breakpoints.
        """
        self.is_open = True
        self.kind = self.KIND_WORD
        self.field = self.ADDRESS
        self.buffer = ""
        self.message = ""

    def close(self):
        """Erase the pop-up from the virtual screen and drop it

        Same rationale as HelpPopup.close: no other window repaints the
        regions beyond the store pad, so the pop-up blanks its own
        rectangle. The bottom bar and the store are the interface's
        business: closing goes through CommandInterface, which touches
        them back.
        """
        self.is_open = False
        if self.window is not None:
            self.window.erase()
            self.window.noutrefresh()
            self.window = None

    def handle_key(self, c: int):
        """Handle an edition key press while the pop-up is open

        Digits and minus build the current field, Enter validates it, and
        the arrows and X manage the existing breakpoints. The close keys
        are handled by the interface.
        """
        if c in (curses.KEY_BACKSPACE, 8, 127):
            self.buffer = self.buffer[:-1]
            self.message = ""

        elif c in (10, 13, curses.KEY_ENTER):
            self._validate_field()

        elif c == ord("t"):
            # Cycle the condition type of the new breakpoint: the typed
            # fields differ between types, so the input restarts
            self.kind = self.KIND_CI if self.kind == self.KIND_WORD else self.KIND_WORD
            self.field = self.ADDRESS
            self.buffer = ""
            self.message = ""

        elif c == curses.KEY_UP:
            self.selected = max(0, self.selected - 1)

        elif c == curses.KEY_DOWN:
            self.selected = min(len(self.machine.breakpoints) - 1, self.selected + 1)

        elif c in (ord("x"), curses.KEY_DC):
            self._delete_selected()

        elif c == ord("-") and self.field == self.VALUE and not self.buffer:
            self.buffer = "-"

        elif ord("0") <= c <= ord("9"):
            # The buffer is capped well beyond the maximum of each field,
            # so typing never overflows the pop-up's input line
            if len(self.buffer) < 11:
                self.buffer += chr(c)
            self.message = ""

    def _validate_field(self):
        """Validate the typed field: move to the next one, or add the breakpoint

        On a validation error the buffer is cleared: the field is retyped
        from scratch, the address already accepted being kept while the
        value is typed.
        """
        buffer, self.buffer = self.buffer, ""

        try:
            number = int(buffer)
        except ValueError:
            self.message = "TYPE A NUMBER"
            return

        if self.field == self.ADDRESS:
            if not 0 <= number < self.machine.store.word_count:
                self.message = f"ADDRESS MUST BE 0 TO {self.machine.store.word_count - 1}"
                return
            self.address = number

            # The CI condition only takes an address: the breakpoint is
            # complete once it is typed
            if self.kind == self.KIND_CI:
                self._add(CiValue(self.address))
                return

            self.field = self.VALUE
            return

        # b() raises IndexError when the value does not fit in a word
        try:
            breakpoint = WordValue(self.address, number, self.machine.store.word_length)
        except IndexError:
            self.message = "VALUE DOES NOT FIT IN A WORD"
            return

        self._add(breakpoint)

    def _add(self, breakpoint):
        """Add the breakpoint, unless the same condition is already set"""
        if breakpoint in self.machine.breakpoints:
            self.message = "BREAKPOINT ALREADY SET"
        else:
            self.machine.breakpoints.append(breakpoint)
            # The selection may sit past the end of the list (e.g. after
            # arrow keys on an empty list): keep it on a real line
            self.selected = max(0, min(self.selected, len(self.machine.breakpoints) - 1))
            self.message = ""
        self.field = self.ADDRESS

    def _delete_selected(self):
        """Remove the selected breakpoint from the list"""
        breakpoints = self.machine.breakpoints
        if breakpoints:
            del breakpoints[self.selected]
            self.selected = min(self.selected, len(breakpoints) - 1)
            self.message = ""

    def geometry(self, lines: int, cols: int) -> tuple[int, int, int, int]:
        """Height, width, y and x of the pop-up for a terminal size

        The height carries one line per breakpoint; the pop-up is centered
        and clamped to the terminal, where the list is windowed on the
        selection instead of overflowing.
        """
        breakpoints = self.machine.breakpoints
        content_width = max(
            len(self.TITLE),
            len(self.EXPLANATION),
            len(self.FOOTER),
            len(self.input_line()),
            max((len(bp.description()) for bp in breakpoints), default=0),
        )
        # 2 border columns, one left margin and one spare column before the
        # right border: no text can then reach the last cell of a line
        width = content_width + 4
        # Interior lines: title, explanation, blank, one line per
        # breakpoint, blank, input, message, footer
        height = len(breakpoints) + 9
        return popup_geometry(height, width, lines, cols)

    def input_line(self) -> str:
        """The input line: the fields of the current type, the typed one underlined

        The underscore acts as the typing cursor, the real cursor being
        hidden.
        """
        if self.kind == self.KIND_CI:
            return f"NEW: CI: {self.buffer}_"
        if self.field == self.ADDRESS:
            return f"NEW: WORD: {self.buffer}_  VALUE:"
        return f"NEW: WORD: {self.address}  VALUE: {self.buffer}_"

    def rebuild(self, stdscr):
        """(Re)create the pop-up window and draw its content

        Rebuilt at every frame while open, since its geometry depends on
        the terminal size and on the number of breakpoints: erasing the
        old window first leaves no residue on the virtual screen. The
        window is created here but only composed later, after the pad:
        its rectangle then covers the store like the help pop-up does.
        """
        lines, cols = stdscr.getmaxyx()
        height, width, y, x = self.geometry(lines, cols)

        if self.window is not None:
            self.window.erase()
            self.window.noutrefresh()
        window = curses.newwin(height, width, y, x)
        self.window = window

        draw_box(window)

        def add_line(row, col, text, attributes=None):
            popup_line(window, row, col, text, height, width, attributes)

        add_line(1, max(1, (width - len(self.TITLE)) // 2), self.TITLE, curses.A_BOLD)
        add_line(2, max(1, (width - len(self.EXPLANATION)) // 2), self.EXPLANATION)

        # The list of breakpoints, windowed on the selection when it does
        # not fit: the selected line is highlighted, like the keys of the
        # bottom bar legend
        breakpoints = self.machine.breakpoints
        visible = max(0, height - 9)
        first = min(max(0, self.selected - visible + 1), max(0, len(breakpoints) - visible))
        for i in range(first, min(len(breakpoints), first + visible)):
            attributes = None
            if i == self.selected:
                attributes = curses.A_REVERSE | curses.color_pair(PAIR_UI)
            pointer = ">" if i == self.selected else " "
            add_line(4 + i - first, 1, f"{pointer} {breakpoints[i].description()}", attributes)

        # Input line, validation message and footer
        add_line(height - 4, 1, self.input_line())
        add_line(height - 3, 1, self.message)
        if height > 3:
            add_line(height - 2, 1, self.FOOTER)

    def compose(self):
        """Copy the pop-up to the virtual screen, above the store pad

        The window is rebuilt at every frame (see rebuild), so its refresh
        is always a first one: a fresh window copies all its lines, blank
        ones included, which keeps the pop-up above the pad without a
        touchwin (unlike the help pop-up).
        """
        self.window.noutrefresh()
