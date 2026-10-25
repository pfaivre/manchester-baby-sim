
from threading import Event
from time import sleep
from timeit import default_timer as timer
from math import exp
from curses import wrapper
import curses

from src.core.bitarray import BitArray
from src.machines.abstractmachine import AbstractMachine


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
        self.terminal_too_small = lines < 24 or cols < 80

        self.top_bar = curses.newwin(0, 0, 0, 0)
        self.bottom_bar = curses.newwin(0, 0, lines - 1, 0)

        self.main_panel_height = self.machine.store.word_count + 4  # The store height + CI + A + empty line
        self.main_panel_width = self.machine.store.word_length + 25  # The store width + margin
        self.pad = curses.newpad(self.main_panel_height, self.main_panel_width)

        # Keep the visible part of the store within its content
        max_scroll = max(0, self.main_panel_height - lines)
        self.store_scroll = max(0, min(self.store_scroll, max_scroll))

        if not self.terminal_too_small:
            self._draw_bottom_bar()

    def _draw_bottom_bar(self):
        """Draw the key legend on the bottom bar
        """
        position = 0
        position = self._add_text(self.bottom_bar, position, " Q ", curses.A_REVERSE | curses.color_pair(4))
        position = self._add_text(self.bottom_bar, position, " QUIT  ")
        position = self._add_text(self.bottom_bar, position, " P ", curses.A_REVERSE | curses.color_pair(4))
        position = self._add_text(self.bottom_bar, position, " RUN/STOP  ")
        position = self._add_text(self.bottom_bar, position, "F10", curses.A_REVERSE | curses.color_pair(4))
        position = self._add_text(self.bottom_bar, position, " STEP  ")
        position = self._add_text(self.bottom_bar, position, " I ", curses.A_REVERSE | curses.color_pair(4))
        position = self._add_text(self.bottom_bar, position, " SPEED UP  ")
        position = self._add_text(self.bottom_bar, position, " K ", curses.A_REVERSE | curses.color_pair(4))
        position = self._add_text(self.bottom_bar, position, " SPEED DOWN  ")
        position = self._add_text(self.bottom_bar, position, " D ", curses.A_REVERSE | curses.color_pair(4))
        position = self._add_text(self.bottom_bar, position, " DISPLAY  ")

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

    def _draw_screen(self, stdscr):
        """Draw the whole interface in a single pass

        Called on every refresh and right after a terminal resize, so that a
        resize appears as one atomic screen update instead of a blank frame.
        """
        if self.terminal_too_small:
            # Below the minimum size, only tell the user instead of
            # crashing on overflowing addstr calls
            lines, cols = stdscr.getmaxyx()
            try:
                # cols - 1: writing the very last cell of the last line
                # makes addstr return an error
                stdscr.addstr(0, 0, f"Terminal too small: {cols}x{lines}, needs 80x24"[:cols - 1])
            except curses.error:
                pass  # The terminal is too small even for the message
            stdscr.refresh()
            return

        # Sizes come from stdscr, not from the curses.LINES/COLS constants
        # (see _setup_windows)
        lines, cols = stdscr.getmaxyx()

        # //// TOP BAR ////
        status = "RUNNING" if self.machine.is_running else "STOPPED"
        s = f"[ STATUS: {status} ]  [ CYCLES: {self.last_cycles} ]  [ {self.machine.last_instruction} ]  [ SPEED: {self.displayed_speed:2d}/{self.machine.speed} ips ] "
        self.top_bar.addstr(0, 0, s[:cols], curses.color_pair(4))

        # //// THE STORE ////
        ci_int = self.machine.ci.to_unsigned_int()
        a_int = self.machine.a.to_int()
        self.pad.addstr(1, 0, f" {self._word_str(self.machine.ci)}", curses.A_BOLD | curses.color_pair(2))
        self.pad.addstr(1, self.machine.model.word_length+2, f"CI = {ci_int:11}")
        self.pad.addstr(2, 0, f" {self._word_str(self.machine.a)}", curses.A_BOLD | curses.color_pair(2))
        self.pad.addstr(2, self.machine.model.word_length+2, f"A  = {a_int:11}")

        for i, word in enumerate(self.machine.store):
            if i == ci_int:
                self.pad.addstr(i+4, 0, f">{self._word_str(word)}", curses.A_BOLD | curses.color_pair(7))
            else:
                self.pad.addstr(i+4, 0, f" {self._word_str(word)}", curses.A_BOLD | curses.color_pair(2))

        self.pad.refresh( self.store_scroll,0, 0,0, lines-2,cols-1 )
        self.top_bar.refresh()
        self.bottom_bar.refresh()

    def _go(self, stdscr):
        """Function to be passed to Curses wrapper function

        Args:
            stdscr: Screen instanciated by Curses
        """
        if curses.LINES < 24 or curses.COLS < 80:
            self.stop_event.set()
            raise InterfaceError("Terminal size is too small. Need minimum 80x24.")

        stdscr.nodelay(True)
        curses.curs_set(0)

        # TODO: better color indexing
        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i, i, -1)

        self._setup_windows(stdscr)

        refresh_frequency = 30  # refreshs per seconds

        while True:
            self._handle_input(stdscr)

            self._update_displayed_speed()
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
