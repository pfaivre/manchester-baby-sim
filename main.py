
import sys

from src.machines.abstractmachine import MachineRuntimeError
from src.machines.assembler import AssemblerError
from src.machines.ssem import Ssem


if __name__ == "__main__":
    try:
        ssem = Ssem(asm_file_path=sys.argv[1])

        try:
            ssem.start()
        except MachineRuntimeError as ex:
            print(ex)

    except AssemblerError as ex:
        print(ex)
    except KeyboardInterrupt:
        pass
