
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
        if c == ord('q'):
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

        if not self.terminal_too_small:
            self._draw_bottom_bar()

    def _draw_bottom_bar(self):
        """Draw the key legend on the bottom bar

        Legend segments that do not fit in the terminal width are skipped
        entirely: drawing them anyway would make addstr error.
        """
        keys = (
            (" Q ", True),
            (" QUIT  ", False),
            (" P ", True),
            (" RUN/STOP  ", False),
            ("F10", True),
            (" STEP  ", False),
            (" I ", True),
            (" SPEED UP  ", False),
            (" K ", True),
            (" SPEED DOWN  ", False),
            (" D ", True),
            (" DISPLAY  ", False),
        )
        _, cols = self.bottom_bar.getmaxyx()
        position = 0
        for text, highlighted in keys:
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
        try:
            wrapper(self._go)
        except InterfaceError as ex:
            self.stop_event.set()
            print(ex)
        except:
            self.stop_event.set()
            raise
