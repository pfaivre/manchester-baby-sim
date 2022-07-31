
import sys
from threading import Event, Thread
from time import sleep
from timeit import default_timer as timer

from src.machines.abstractmachine import AbstractMachine
from src.machines.assembler import AssemblerError
from src.machines.ssem import Ssem


def run_machine(machine: AbstractMachine, stop_event: Event):
    machine.start(stop_event)


def run_interface(machine: AbstractMachine, stop_event: Event):
    # TODO: create an interface module

    refresh_frequency = 30  # refreshs per seconds
    last_cycles = 0
    last_refresh_time = timer()

    while True:
        status = "RUNNING" if machine.is_running else "STOPPED"
        print(f"[ STATUS: {status} ]  [ CYCLES: {machine.last_cycle} ]  [ {machine.last_instruction} ] [ SPEED: {int((machine.last_cycle - last_cycles) / (timer() - last_refresh_time))} ips ]") #  [ TIME: {datetime.utcnow() - overall_start} ]  [ SPEED: {int(round(1 / last_cycle_time, 0))} ips ]")
        last_cycles = machine.last_cycle
        last_refresh_time = timer()
        print(f"{machine.ci}  CI")
        print(f"{machine.a}  A")
        print()
        store_str = str(machine.store).split("\n")
        ci_int = machine.ci.to_unsigned_int()
        store_str[ci_int] = "\033[1m" + store_str[ci_int] + "\033[0m"
        print("\n".join(store_str))

        if stop_event.is_set():
            break

        sleep(1 / refresh_frequency)


if __name__ == "__main__":
    stop_event = Event()

    try:
        ssem = Ssem(file=sys.argv[1])

        thread_machine = Thread(target=run_machine, args=(ssem, stop_event))
        thread_interface = Thread(target=run_interface, args=(ssem, stop_event))
    except AssemblerError as ex:
        print(ex)

    try:
        thread_interface.start()
        thread_machine.start()

        thread_machine.join()
        thread_interface.join()

    except KeyboardInterrupt:
        stop_event.set()
        thread_machine.join()
        thread_interface.join()
