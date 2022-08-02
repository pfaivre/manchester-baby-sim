
from threading import Event
from time import sleep
from timeit import default_timer as timer
from curses import wrapper
import curses

from src.machines.abstractmachine import AbstractMachine


class CommandInterface:

    def __init__(self, machine: AbstractMachine, stop_event: Event):
        self.machine = machine
        self.stop_event = stop_event


    def _handle_input(self, stdscr):
        c = stdscr.getch()
        curses.flushinp()  # Avoid queuing key presses

        if c == ord('q'):
            self.stop_event.set()
        elif c == curses.KEY_DOWN:
            if self.machine.speed - 100 > 0:
                self.machine.speed -= 100
        elif c == curses.KEY_UP:
            if self.machine.speed < 10000000:
                self.machine.speed += 100
        elif c == ord('p'):
            self.machine.stop_flag = not self.machine.stop_flag
        elif c == curses.KEY_F10:
            if self.machine.stop_flag:
                self.machine.instruction_cycle()

    def _go(self, stdscr):
        stdscr.clear()
        stdscr.nodelay(True)
        curses.curs_set(0)

        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i, i, -1)

        pad = curses.newpad(self.machine.store.word_count + 4, stdscr.getmaxyx()[1])

        refresh_frequency = 30  # refreshs per seconds
        last_cycles = 0
        last_refresh_time = timer()

        while True:
            self._handle_input(stdscr)

            status = "RUNNING" if self.machine.is_running else "STOPPED"
            s = f"[ STATUS: {status} ]  [ CYCLES: {self.machine.last_cycle} ]  [ {self.machine.last_instruction} ] [ SPEED: {int((self.machine.last_cycle - last_cycles) / (timer() - last_refresh_time))}/{self.machine.speed} ips ]"
            last_cycles = self.machine.last_cycle
            last_refresh_time = timer()
            stdscr.addstr(0, 0, s, curses.color_pair(4))

            ci_int = self.machine.ci.to_unsigned_int()
            a_int = self.machine.a.to_int()

            pad.addstr(1, 0, f"{self.machine.ci}", curses.A_BOLD | curses.color_pair(2))
            pad.addstr(1, self.machine.model.word_length, f"  CI = {ci_int:11}")
            pad.addstr(2, 0, f"{self.machine.a}", curses.A_BOLD | curses.color_pair(2))
            pad.addstr(2, self.machine.model.word_length, f"  A  = {a_int:11}")

            for i, word in enumerate(self.machine.store):
                if i == ci_int:
                    pad.addstr(i+4, 0, str(word), curses.A_BOLD | curses.color_pair(7))
                else:
                    pad.addstr(i+4, 0, str(word), curses.A_BOLD | curses.color_pair(2))

            pad.refresh( 0,0, 0,0, *stdscr.getmaxyx())

            stdscr.refresh()

            if self.stop_event.is_set():
                break

            sleep(1 / refresh_frequency)

    def run_interface(self):
        wrapper(self._go)
