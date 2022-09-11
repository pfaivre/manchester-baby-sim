
from threading import Event
from time import sleep
from timeit import default_timer as timer
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

    def __init__(self, machine: AbstractMachine, stop_event: Event):
        self.machine = machine
        self.stop_event = stop_event
        self.current_bit_representation = 0
        self.store_scroll = 0
        self.main_panel_height = 0

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

        if not c:
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
            if self.main_panel_height - self.store_scroll >= curses.LINES:
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

    def _go(self, stdscr):
        """Function to be passed to Curses wrapper function

        Args:
            stdscr: Screen instanciated by Curses
        """
        if curses.LINES < 24 or curses.COLS < 80:
            self.stop_event.set()
            raise InterfaceError("Terminal size is too small. Need minimum 80x24.")

        stdscr.clear()
        stdscr.nodelay(True)
        curses.curs_set(0)

        # TODO: better color indexing
        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i, i, -1)

        top_bar = curses.newwin( 0,0, 0,0)
        self.main_panel_height = self.machine.store.word_count + 4  # The store height + CI + A + empty line
        self.main_panel_width = self.machine.store.word_length + 25  # The store width + margin
        pad = curses.newpad(self.main_panel_height, self.main_panel_width)
        bottom_bar = curses.newwin( 0,0, curses.LINES-1,0)

        position = 0
        position = self._add_text(bottom_bar, position, " Q ", curses.A_REVERSE | curses.color_pair(4))
        position = self._add_text(bottom_bar, position, " QUIT  ")
        position = self._add_text(bottom_bar, position, " P ", curses.A_REVERSE | curses.color_pair(4))
        position = self._add_text(bottom_bar, position, " RUN/STOP  ")
        position = self._add_text(bottom_bar, position, "F10", curses.A_REVERSE | curses.color_pair(4))
        position = self._add_text(bottom_bar, position, " STEP  ")
        position = self._add_text(bottom_bar, position, " I ", curses.A_REVERSE | curses.color_pair(4))
        position = self._add_text(bottom_bar, position, " SPEED UP  ")
        position = self._add_text(bottom_bar, position, " K ", curses.A_REVERSE | curses.color_pair(4))
        position = self._add_text(bottom_bar, position, " SPEED DOWN  ")
        position = self._add_text(bottom_bar, position, " D ", curses.A_REVERSE | curses.color_pair(4))
        position = self._add_text(bottom_bar, position, " DISPLAY  ")

        refresh_frequency = 30  # refreshs per seconds
        last_cycles = 0
        last_refresh_time = timer()

        while True:
            self._handle_input(stdscr)

            # //// TOP BAR ////
            status = "RUNNING" if self.machine.is_running else "STOPPED"
            current_speed = int((self.machine.last_cycle - last_cycles) / (timer() - last_refresh_time))
            last_cycles = self.machine.last_cycle
            last_refresh_time = timer()
            s = f"[ STATUS: {status} ]  [ CYCLES: {last_cycles} ]  [ {self.machine.last_instruction} ]  [ SPEED: {current_speed:2d}/{self.machine.speed} ips ] "
            top_bar.addstr(0, 0, s, curses.color_pair(4))

            # //// THE STORE ////
            ci_int = self.machine.ci.to_unsigned_int()
            a_int = self.machine.a.to_int()
            pad.addstr(1, 0, f" {self._word_str(self.machine.ci)}", curses.A_BOLD | curses.color_pair(2))
            pad.addstr(1, self.machine.model.word_length+2, f"CI = {ci_int:11}")
            pad.addstr(2, 0, f" {self._word_str(self.machine.a)}", curses.A_BOLD | curses.color_pair(2))
            pad.addstr(2, self.machine.model.word_length+2, f"A  = {a_int:11}")

            for i, word in enumerate(self.machine.store):
                if i == ci_int:
                    pad.addstr(i+4, 0, f">{self._word_str(word)}", curses.A_BOLD | curses.color_pair(7))
                else:
                    pad.addstr(i+4, 0, f" {self._word_str(word)}", curses.A_BOLD | curses.color_pair(2))

            pad.refresh( self.store_scroll,0, 0,0, curses.LINES-2,curses.COLS-1 )
            top_bar.refresh()
            bottom_bar.refresh()

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
