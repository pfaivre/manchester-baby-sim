
from assembler import Assembler, AssemblerError
from ssem import Ssem


if __name__ == "__main__":
    try:
        ssem = Ssem()

        Assembler.load_file("samples/fibonacci.asm", ssem.store)

        print(ssem.store)

    except AssemblerError as ex:
        print(ex)
