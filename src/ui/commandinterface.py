
import curses
from curses import wrapper
from math import exp
from threading import Event
from time import sleep
from timeit import default_timer as timer

from src.core.bitarray import BitArray
from src.machines.abstractmachine import AbstractMachine
from src.machines.assembler import AssemblerError


class InterfaceError(Exception):
    pass


class CommandInterface:

    BIT_REPRESENTATIONS = (
        {True: "#", False: "."},  # High contrast ASCII characters
        {True: "−", False: "·"},  # Fancy characters for more accurate display
        {True: "_", False: "."},  # ASCII compatible characters
        {True: "1", False: "0"},  # 0s and 1s
    )

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
        ("H", "HELP", "Toggle this help pop-up"),
    )

    HELP_TITLE = "SSEM SIMULATOR"
    HELP_FOOTER = "Press H to close"

    SPEED_DISPLAY_PERIOD = 0.5  # seconds between updates of the displayed speed

    PAIR_STORE = 1  # Bits and registers (green)
    PAIR_UI = 2  # Top bar and key legend (blue)

    def __init__(self, machine: AbstractMachine, stop_event: Event):
        self.machine = machine
        self.stop_event = stop_event
        self.current_bit_representation = 0
        self.store_scroll = 0
        self.main_panel_height = 0
        self.terminal_too_small = False
        self.current_speed = 0.0
        self.displayed_speed = 0
        self.last_speed_refresh = timer()
        self.last_cycles = 0
        self.last_refresh_time = timer()
        self.dirty = True  # The first frame must be drawn
        self.last_drawn_cycle = 0
        self.help_window = None  # The help pop-up window, None while closed

    def _add_text(self, window, position: int, text: str, attributes = None) -> int:
        """Helper to chain multiple string prints to a window
        """
        if attributes:
            window.addstr(0, position, text, attributes)
        else:
            window.addstr(0, position, text)
        return position + len(text)

    def _handle_input(self, stdscr):
        """Scan the inputs and performs according actions
        """
        c = stdscr.getch()

        if c == -1:  # No key pressed (getch is in nodelay mode)
            return

        # Any key press may have changed the display
        self.dirty = True

        # //// RESIZE ////
        # Handled before flushinp, so that a resize event queued together
        # with other keys cannot be discarded
        if c == curses.KEY_RESIZE:
            self._on_resize(stdscr)
            return

        curses.flushinp()  # Avoid queuing key presses

        # //// QUIT ////
        if c == ord('q') or c == 27:  # 27 is Esc, for which curses defines no KEY_ constant
            self.stop_event.set()

        # //// SPEED DOWN ////
        elif c == ord("k"):
            if self.machine.speed <= 10:
                if self.machine.speed - 1 > 0:
                    self.machine.speed -= 1
            elif self.machine.speed <= 100:
                self.machine.speed -= 10
            else:
                self.machine.speed -= 100

        # //// SPEED UP ////
        elif c == ord("i"):
            if self.machine.speed < 10:
                self.machine.speed += 1
            elif self.machine.speed < 100:
                self.machine.speed += 10
            elif self.machine.speed < 10000000:
                self.machine.speed += 100

        # //// RUN/STOP ////
        elif c == ord('p'):
            self.machine.stop_flag = not self.machine.stop_flag

        # //// SCROLL UP ////
        elif c == curses.KEY_UP:
            if self.store_scroll > 0:
                self.store_scroll -= 1

        # //// SCROLL DOWN ////
        elif c == curses.KEY_DOWN:
            lines, _ = stdscr.getmaxyx()
            if self.main_panel_height - self.store_scroll >= lines:
                self.store_scroll += 1

        # //// STEP ////
        elif c == curses.KEY_F10:
            self.machine.stop_flag = True
            self.machine.instruction_cycle()

        # //// DISPLAY ////
        elif c == ord("d"):
            self.current_bit_representation = (self.current_bit_representation + 1) % len(self.BIT_REPRESENTATIONS)

        # //// HELP ////
        elif c == ord("h"):
            if self.help_window is None:
                self._create_help_window(stdscr)
            else:
                self._close_help_window()

    def _word_str(self, word: BitArray) -> str:
        """Represents a word according to the current style

        Args:
            word (BitArray): Word to represent

        Returns:
            str: Visual representation of the word
        """
        str_word = [self.BIT_REPRESENTATIONS[self.current_bit_representation][b] for b in word]
        return "".join(map(str, str_word))

    def _word_interpretation(self, word: BitArray) -> str:
        """Decodes the word as an instruction for the display

        Every word is shown as an instruction, as on the real machine: data
        words are decoded too (e.g. a negative number reads as STP).

        Args:
            word (BitArray): Word to decode

        Returns:
            str: Mnemonic and data, or "?" if the word holds no valid opcode
        """
        try:
            command, data = self.machine.assembler.decode_instruction(word)
        except AssemblerError:
            return "?"
        return f"{command.name:4} {data:02d}"

    def _on_resize(self, stdscr):
        """Adapt the interface to a resized terminal
        """
        # The KEY_RESIZE event can lag behind the newest terminal size while
        # dragging: take the size ncurses has actually applied to stdscr as
        # the source of truth and sync the module-level constants to match.
        # (curses.resizeterm must not be used for this: it queues a fresh
        # KEY_RESIZE event, which would loop on itself forever)
        curses.LINES, curses.COLS = stdscr.getmaxyx()
        self._setup_windows(stdscr)
        self._draw_screen(stdscr)

    def _minimum_width(self) -> int:
        """The terminal width needed to display the store in its full width

        After the bits and the pointer, the display carries the index, the
        value and the interpretation (1 separator + 25 characters), plus
        one spare column: the text of the last store line must stay away
        from the last cell of the pad, where addstr would return an error.
        """
        return self.machine.store.word_length + 27

    def _setup_windows(self, stdscr):
        """(Re)create the windows to fit the current terminal size

        Called once at startup and again on every terminal resize.
        """
        # Erase, not clear: clear sets clearok, which makes ncurses
        # physically clear the screen on the next update and flicker
        stdscr.erase()
        stdscr.noutrefresh()

        # Sizes come from stdscr, never from the curses.LINES/COLS constants:
        # while dragging, a resize is applied to stdscr before the matching
        # KEY_RESIZE event reaches us, and writing outside the real window
        # makes the addstr/refresh calls return an error
        lines, cols = stdscr.getmaxyx()

        # The top bar is a single line: a full-screen window would wipe the
        # store area from the virtual screen on its first refresh, since a
        # fresh window copies all its blank lines, not only the written ones
        self.top_bar = curses.newwin(1, 0, 0, 0)
        self.bottom_bar = curses.newwin(1, 0, lines - 1, 0)

        self.main_panel_height = self.machine.store.word_count + 4  # The store height + CI + A + empty line
        self.main_panel_width = self._minimum_width()
        self.terminal_too_small = lines < 12 or cols < self.main_panel_width
        self.pad = curses.newpad(self.main_panel_height, self.main_panel_width)

        # Keep the visible part of the store within its content
        max_scroll = max(0, self.main_panel_height - lines)
        self.store_scroll = max(0, min(self.store_scroll, max_scroll))

        # The help pop-up depends on the terminal size: rebuild it if open
        if self.help_window is not None:
            self._create_help_window(stdscr)

        if not self.terminal_too_small:
            self._draw_bottom_bar()

    def _legend_segments(self):
        """The bottom bar segments built from KEYMAP: (text, highlighted)

        Single-character keys are padded like " Q ", longer ones ("F10")
        are drawn as-is.
        """
        segments = []
        for key, legend, _ in self.KEYMAP:
            if legend is None:
                continue
            key_text = f" {key} " if len(key) == 1 else key
            segments.append((key_text, True))
            segments.append((f" {legend}  ", False))
        return segments

    def _draw_bottom_bar(self):
        """Draw the key legend on the bottom bar

        The legend is built from KEYMAP, the same table as the help pop-up.
        Legend segments that do not fit in the terminal width are skipped
        entirely: drawing them anyway would make addstr error.
        """
        _, cols = self.bottom_bar.getmaxyx()
        position = 0
        for text, highlighted in self._legend_segments():
            # The last cell of the window's single line makes addstr error,
            # so a segment must end at least one column short of the edge
            if position + len(text) > cols - 1:
                break
            if highlighted:
                position = self._add_text(
                    self.bottom_bar, position, text, curses.A_REVERSE | curses.color_pair(self.PAIR_UI)
                )
            else:
                position = self._add_text(self.bottom_bar, position, text)

    def _help_key_column(self) -> int:
        """Width of the highlighted key column in the help pop-up

        The widest key plus one space on each side, so every label sits
        centered in its reverse box, away from the description.
        """
        return max(len(key) for key, _, _ in self.KEYMAP) + 2

    def _help_window_geometry(self, lines: int, cols: int) -> tuple[int, int, int, int]:
        """Height, width, y and x of the help pop-up for a terminal size

        The pop-up is centered, and clamped to the terminal: on a small
        terminal its drawing is truncated rather than overflowing.
        """
        key_column = self._help_key_column()
        content_width = max(
            len(self.HELP_TITLE),
            len(self.HELP_FOOTER),
            key_column + 1 + max(len(description) for _, _, description in self.KEYMAP),
        )
        # 2 border columns, one left margin and one spare column before the
        # right border: no text can then reach the last cell of a line
        width = content_width + 4
        # Interior lines: title, blank, one line per key, blank, footer
        height = len(self.KEYMAP) + 6
        height, width = min(height, lines), min(width, cols)
        return height, width, max(0, (lines - height) // 2), max(0, (cols - width) // 2)

    def _create_help_window(self, stdscr):
        """(Re)create the help pop-up window, centered on the terminal

        Called when the pop-up opens and again on every resize while it is
        open, since its size and position depend on the terminal. The
        window is built from KEYMAP, the same table as the bottom bar
        legend, and truncated when the terminal cannot fit it.
        """
        lines, cols = stdscr.getmaxyx()
        height, width, y, x = self._help_window_geometry(lines, cols)
        key_column = self._help_key_column()
        window = curses.newwin(height, width, y, x)
        self.help_window = window

        # The window can fill the whole terminal when clamped: its
        # bottom-right corner is then the last cell of the last line, where
        # writing makes addstr error, so box() is guarded like every write
        try:
            window.box()
        except curses.error:
            pass  # Degenerated terminal: keep whatever border was drawn

        def add_line(row, col, text, attributes=None):
            """Write one line of the pop-up, clipped to the interior"""
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

        # Title, centered on the window
        add_line(1, max(1, (width - len(self.HELP_TITLE)) // 2), self.HELP_TITLE, curses.A_BOLD)

        # One line per key: the key centered in its box, the description
        # following
        for i, (key, _, description) in enumerate(self.KEYMAP):
            if 3 + i >= height - 2:
                break  # No interior room left: the rest is truncated away
            add_line(3 + i, 1, f"{key:^{key_column}}", curses.A_REVERSE | curses.color_pair(self.PAIR_UI))
            add_line(3 + i, 2 + key_column, description)

        if height > 3:
            add_line(height - 2, 1, self.HELP_FOOTER)

    def _close_help_window(self):
        """Erase the pop-up from the virtual screen and drop it

        The pop-up can extend beyond the store pad — to its right, and over
        the bottom bar — and no other window repaints those regions, so its
        rectangle must be blanked by the window itself. The bottom bar is
        only touched at setup: it needs a touchwin to copy its legend back
        over the blanked row. The dirty flag set by the key press makes the
        next frame redraw the store over the rest of the erased area.
        """
        self.help_window.erase()
        self.help_window.noutrefresh()
        self.help_window = None
        self.bottom_bar.touchwin()

    def _update_displayed_speed(self):
        """Exponentially smooth the execution speed shown in the top bar

        The smoothed value is computed at every refresh, but only copied to
        the display every SPEED_DISPLAY_PERIOD seconds, so the counter does
        not jitter. When the machine stops, the display drops to 0 at once.
        """
        speed_smoothing = 0.5  # seconds of memory of the displayed speed

        now = timer()
        elapsed = now - self.last_refresh_time
        if self.machine.is_running:
            measured = (self.machine.last_cycle - self.last_cycles) / elapsed
            alpha = 1 - exp(-elapsed / speed_smoothing)
            self.current_speed += alpha * (measured - self.current_speed)

            if now - self.last_speed_refresh >= self.SPEED_DISPLAY_PERIOD:
                self.displayed_speed = int(self.current_speed)
                self.last_speed_refresh = now
        else:
            self.current_speed = 0.0
            self.displayed_speed = 0
        self.last_cycles = self.machine.last_cycle
        self.last_refresh_time = now

    def _needs_redraw(self) -> bool:
        """Tell whether the current frame must be drawn

        The display only changes when a key was pressed or when the machine
        moved: every state change goes through an instruction cycle, which
        bumps last_cycle. While the machine is stopped and idle, frames are
        skipped entirely.
        """
        return self.dirty or self.machine.last_cycle != self.last_drawn_cycle

    def _draw_screen(self, stdscr):
        """Draw the whole interface in a single pass

        Called on every refresh and right after a terminal resize, so that a
        resize appears as one atomic screen update instead of a blank frame.
        """
        # Snapshot the state this frame is drawn from: anything changing
        # after this point (e.g. the machine executing one more instruction
        # mid-draw) triggers a redraw on the next frame
        self.dirty = False
        self.last_drawn_cycle = self.machine.last_cycle

        if self.terminal_too_small:
            # Below the minimum size, only tell the user instead of
            # crashing on overflowing addstr calls
            lines, cols = stdscr.getmaxyx()
            try:
                # cols - 1: writing the very last cell of the last line
                # makes addstr return an error
                stdscr.addstr(0, 0, f"Terminal too small: {cols}x{lines}, needs {self.main_panel_width}x12"[:cols - 1])
            except curses.error:
                pass  # The terminal is too small even for the message
            stdscr.refresh()
            return

        # Sizes come from stdscr, not from the curses.LINES/COLS constants
        # (see _setup_windows)
        lines, cols = stdscr.getmaxyx()

        # //// TOP BAR ////
        status = "RUNNING" if self.machine.is_running else "STOPPED"
        s = (
            f"[ STATUS: {status} ]  [ CYCLES: {self.last_cycles} ]  "
            f"[ {self.machine.last_instruction} ]  "
            f"[ SPEED: {self.displayed_speed:2d}/{self.machine.speed} ips ] "
        )
        # cols - 1: the top bar is a single-line window, and writing the
        # very last cell of the last line makes addstr return an error
        self.top_bar.addstr(0, 0, s[:cols - 1], curses.color_pair(self.PAIR_UI))

        # //// THE STORE ////
        ci_int = self.machine.ci.to_unsigned_int()
        a_int = self.machine.a.to_int()
        self.pad.addstr(1, 0, f" {self._word_str(self.machine.ci)}", curses.A_BOLD | curses.color_pair(self.PAIR_STORE))
        self.pad.addstr(1, self.machine.model.word_length+2, f"CI: {ci_int:11}")
        self.pad.addstr(2, 0, f" {self._word_str(self.machine.a)}", curses.A_BOLD | curses.color_pair(self.PAIR_STORE))
        self.pad.addstr(2, self.machine.model.word_length+2, f"A : {a_int:11}")

        for i, word in enumerate(self.machine.store):
            pointer = ">" if i == ci_int else " "
            # The bits keep their color (green, or highlighted on the CI
            # line); the pointer and the interpretation are drawn in the
            # default terminal color, in three passes
            if i == ci_int:
                bits_color = 0
            else:
                bits_color = curses.color_pair(self.PAIR_STORE)
            self.pad.addstr(i+4, 0, pointer, curses.A_BOLD)
            self.pad.addstr(i+4, 1, self._word_str(word), curses.A_BOLD | bits_color)
            self.pad.addstr(
                i+4,
                1 + self.machine.model.word_length,
                f" {i:02d}: {word.to_int():11}  {self._word_interpretation(word)}"
            )

        # Compose the whole frame in the virtual screen, then flush it with a
        # single physical update: the pad is displayed from screen row 0 and
        # therefore overlaps the top bar (its first blank line sits under the
        # bar). With one refresh() per window, each would trigger its own
        # physical update, blanking and repainting the bar's row every frame
        self.pad.noutrefresh(self.store_scroll,0, 0,0, lines-2,cols-1 )
        self.top_bar.noutrefresh()
        self.bottom_bar.noutrefresh()
        # The pop-up is composed last: the pad covers the whole store area,
        # and a window refresh copies its entire rectangle to the virtual
        # screen, so composing it earlier would leave it painted over.
        # A refresh only copies the lines touched since the window's last
        # refresh, and the pad repaints its own lines at every frame:
        # touchwin forces the full copy, keeping the pop-up on top
        if self.help_window is not None:
            self.help_window.touchwin()
            self.help_window.noutrefresh()
        curses.doupdate()

    def _go(self, stdscr):
        """Function to be passed to Curses wrapper function

        Args:
            stdscr: Screen instanciated by Curses
        """
        if curses.LINES < 12 or curses.COLS < self._minimum_width():
            self.stop_event.set()
            raise InterfaceError(f"Terminal size is too small. Need minimum {self._minimum_width()}x12.")

        stdscr.nodelay(True)
        curses.curs_set(0)

        curses.use_default_colors()
        curses.init_pair(self.PAIR_STORE, curses.COLOR_GREEN, -1)
        curses.init_pair(self.PAIR_UI, curses.COLOR_BLUE, -1)

        self._setup_windows(stdscr)

        refresh_frequency = 30  # refreshs per seconds

        while True:
            self._handle_input(stdscr)

            self._update_displayed_speed()

            if self._needs_redraw():
                self._draw_screen(stdscr)

            if self.stop_event.is_set():
                break

            sleep(1 / refresh_frequency)

    def run_interface(self):
        # With keypad mode on, ncurses holds a lone Esc for the escape
        # sequence completion delay (ESCDELAY, 1s by default) before
        # returning it as a key press, and that wait ignores nodelay: the
        # interface would freeze for a second on Esc, with the Esc finally
        # delivered on the next key press. A short delay keeps Esc snappy
        # while leaving arrow-key sequences (written by the terminal in one
        # piece) unaffected
        curses.set_escdelay(25)
        try:
            wrapper(self._go)
        except InterfaceError as ex:
            self.stop_event.set()
            print(ex)
        except:
            self.stop_event.set()
            raise
