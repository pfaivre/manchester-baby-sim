import curses
from curses import wrapper
from math import exp
from threading import Event
from time import sleep
from timeit import default_timer as timer

from src.core.words import sign_extend, to_string
from src.machines.abstractmachine import AbstractMachine
from src.machines.assembler import AssemblerError
from src.ui.breakpointpopup import BreakpointPopup
from src.ui.helppopup import HelpPopup
from src.ui.keymap import legend_segments
from src.ui.theme import BIT_REPRESENTATIONS, PAIR_STORE, PAIR_UI


class InterfaceError(Exception):
    pass


class CommandInterface:
    """Curses interface: main loop, input dispatch, store display, bars and speed meter

    The pop-ups are separate classes owning their windows (HelpPopup,
    BreakpointPopup); this class opens, closes and composes them, and
    keeps the cross-window invariants: the compose order in _draw_screen,
    and the touchwin of the bottom bar when a pop-up closes.
    """

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
        self.dirty = True  # The first frame must be drawn
        self.last_drawn_cycle = 0
        self.help_popup = HelpPopup()
        self.breakpoint_popup = BreakpointPopup(machine)

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

        # While the breakpoint pop-up is open, the keys edit the pop-up
        # instead of driving the machine. The close keys are handled here:
        # closing the pop-up erases its rectangle, and the bottom bar needs
        # a touchwin to recover its legend (see _close_breakpoint_popup)
        if self.breakpoint_popup.is_open:
            if c == 27 or c == ord("b"):  # 27 is Esc, for which curses defines no KEY_ constant
                self._close_breakpoint_popup()
            else:
                self.breakpoint_popup.handle_key(c)
            return

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
            self.current_bit_representation = (self.current_bit_representation + 1) % len(BIT_REPRESENTATIONS)

        # //// BREAKPOINTS ////
        elif c == ord("b"):
            if self.breakpoint_popup.is_open:
                self._close_breakpoint_popup()
            else:
                self.breakpoint_popup.open()

        # //// HELP ////
        elif c == ord("h"):
            if self.help_popup.is_open:
                self._close_help_popup()
            else:
                self.help_popup.open(stdscr)

    def _close_breakpoint_popup(self):
        """Close the breakpoint pop-up and restore the bottom bar

        The pop-up blanks its own rectangle (see BreakpointPopup.close),
        but the bottom bar is only touched at setup: it needs a touchwin
        to copy its legend back over the blanked row. The dirty flag set
        by the key press makes the next frame redraw the store over the
        rest of the erased area.
        """
        self.breakpoint_popup.close()
        self.bottom_bar.touchwin()

    def _close_help_popup(self):
        """Close the help pop-up and restore the bottom bar

        Same rationale as _close_breakpoint_popup.
        """
        self.help_popup.close()
        self.bottom_bar.touchwin()

    def _word_str(self, word: int) -> str:
        """Represents a word according to the current style

        Args:
            word (int): Word to represent

        Returns:
            str: Visual representation of the word
        """
        on, off = BIT_REPRESENTATIONS[self.current_bit_representation]
        return to_string(word, self.machine.store.word_length, on=on, off=off)

    def _word_interpretation(self, word: int) -> str:
        """Decodes the word as an instruction for the display

        Every word is shown as an instruction, as on the real machine: data
        words are decoded too (e.g. a negative number reads as STP).

        Args:
            word (int): Word to decode

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
        if self.help_popup.is_open:
            self.help_popup.open(stdscr)

        if not self.terminal_too_small:
            self._draw_bottom_bar()

    def _draw_bottom_bar(self):
        """Draw the key legend on the bottom bar

        The legend is built from KEYMAP (see src/ui/keymap.py), the same
        table as the help pop-up. Legend segments that do not fit in the
        terminal width are skipped entirely: drawing them anyway would
        make addstr error.
        """
        _, cols = self.bottom_bar.getmaxyx()
        position = 0
        for text, highlighted in legend_segments():
            # The last cell of the window's single line makes addstr error,
            # so a segment must end at least one column short of the edge
            if position + len(text) > cols - 1:
                break
            if highlighted:
                position = self._add_text(
                    self.bottom_bar, position, text, curses.A_REVERSE | curses.color_pair(PAIR_UI)
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
        if self.machine.breakpoints:
            s += f" [ BREAKPOINTS: {len(self.machine.breakpoints)} ] "
        # cols - 1: the top bar is a single-line window, and writing the
        # very last cell of the last line makes addstr return an error
        self.top_bar.addstr(0, 0, s[:cols - 1], curses.color_pair(PAIR_UI))

        # //// THE STORE ////
        ci_int = self.machine.ci
        a_int = sign_extend(self.machine.a, self.machine.model.word_length)
        self.pad.addstr(1, 0, f" {self._word_str(self.machine.ci)}", curses.A_BOLD | curses.color_pair(PAIR_STORE))
        self.pad.addstr(1, self.machine.model.word_length+2, f"CI: {ci_int:11}")
        self.pad.addstr(2, 0, f" {self._word_str(self.machine.a)}", curses.A_BOLD | curses.color_pair(PAIR_STORE))
        self.pad.addstr(2, self.machine.model.word_length+2, f"A : {a_int:11}")

        for i, word in enumerate(self.machine.store):
            pointer = ">" if i == ci_int else " "
            # The bits keep their color (green, or highlighted on the CI
            # line); the pointer and the interpretation are drawn in the
            # default terminal color, in three passes
            if i == ci_int:
                bits_color = 0
            else:
                bits_color = curses.color_pair(PAIR_STORE)
            self.pad.addstr(i+4, 0, pointer, curses.A_BOLD)
            self.pad.addstr(i+4, 1, self._word_str(word), curses.A_BOLD | bits_color)
            self.pad.addstr(
                i+4,
                1 + self.machine.model.word_length,
                f" {i:02d}: {sign_extend(word, self.machine.model.word_length):11}  {self._word_interpretation(word)}"
            )

        # (Re)build the breakpoint pop-up before composing: erasing its
        # previous rectangle can blank store lines, which the pad's refresh
        # below repaints in the same composed frame
        if self.breakpoint_popup.is_open:
            self.breakpoint_popup.rebuild(stdscr)

        # Compose the whole frame in the virtual screen, then flush it with a
        # single physical update: the pad is displayed from screen row 0 and
        # therefore overlaps the top bar (its first blank line sits under the
        # bar). With one refresh() per window, each would trigger its own
        # physical update, blanking and repainting the bar's row every frame
        self.pad.noutrefresh(self.store_scroll,0, 0,0, lines-2,cols-1 )
        self.top_bar.noutrefresh()
        self.bottom_bar.noutrefresh()
        # The pop-ups are composed last: the pad covers the whole store area,
        # and a window refresh copies its entire rectangle to the virtual
        # screen, so composing them earlier would leave them painted over
        if self.help_popup.is_open:
            self.help_popup.compose()
        if self.breakpoint_popup.is_open:
            self.breakpoint_popup.compose()
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
        curses.init_pair(PAIR_STORE, curses.COLOR_GREEN, -1)
        curses.init_pair(PAIR_UI, curses.COLOR_BLUE, -1)

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
