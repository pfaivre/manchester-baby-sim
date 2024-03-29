
import sys
from threading import Event, Thread

from src.machines.assembler import AssemblerError
from src.machines.ssem import Ssem
from src.ui.commandinterface import CommandInterface


if __name__ == "__main__":
    stop_event = Event()

    try:
        if len(sys.argv) > 1:
            ssem = Ssem(file=sys.argv[1])
        else:
            ssem = Ssem()
        interface = CommandInterface(ssem, stop_event)

        thread_interface = Thread(target=interface.run_interface)
        thread_machine = Thread(target=ssem.start, kwargs={"stop_event": stop_event, "stopped": True})

    except AssemblerError as ex:
        print(ex)

    try:
        thread_interface.start()
        thread_machine.start()

        thread_interface.join()
        thread_machine.join()

    except KeyboardInterrupt:
        stop_event.set()
        thread_machine.join()
        thread_interface.join()

    except Exception as ex:
        print(ex, file=sys.stderr)
        stop_event.set()
        thread_machine.join()
        thread_interface.join()
