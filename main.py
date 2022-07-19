
import sys

from assembler import Assembler, AssemblerError
from ssem import Ssem


if __name__ == "__main__":
    try:
        ssem = Ssem()

        Assembler.load_file(sys.argv[1], ssem.store)

        ssem.start()
    except AssemblerError as ex:
        print(ex)
    except KeyboardInterrupt:
        pass
