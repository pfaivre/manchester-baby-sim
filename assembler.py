from enum import Enum
from pathlib import Path

from bitarray import BitArray
from store import Store


class AssemblerError(Exception):
    pass


class Mnemonic(Enum):
    """Instruction set of the SSEM with operation code
    """
    JMP = BitArray.from_iterable([False, False, False])
    JRP = BitArray.from_iterable([True,  False, False])
    LDN = BitArray.from_iterable([False, True,  False])
    STO = BitArray.from_iterable([True,  True,  False])
    SUB = BitArray.from_iterable([False, False, True])
    CMP = BitArray.from_iterable([False, True,  True])
    STP = BitArray.from_iterable([True,  True,  True])
    NUM = None


class Assembler:
    """Assembler for Manchester-like machines (currently only SSEM)
    """

    INSTRUCTIONS_WITH_DATA = (
        Mnemonic.JMP,
        Mnemonic.JRP,
        Mnemonic.LDN,
        Mnemonic.STO,
        Mnemonic.SUB,
        Mnemonic.NUM
    )
    """Commands that need a data"""

    INSTRUCTIONS_DATA_IS_ADDRESS = (
        Mnemonic.JMP,
        Mnemonic.JRP,
        Mnemonic.LDN,
        Mnemonic.STO,
        Mnemonic.SUB
    )
    """Commands of which data must be an address"""

    ADDRESS_SIZE = 13
    """Size of an address value in bits"""

    @classmethod
    def load_file(cls, file: Path, store: Store):
        """Load an assembly file into the given store
        """
        store_tmp = Store(
            word_length=store.word_length,
            word_count=store.word_count
        )

        counter = 0
        error = False

        with open(file, "r") as file:
            for line in file:
                # Cleaning
                line = line[:-1].split(';')[0].strip()
                if not line:
                    continue

                # TODO: remove this temporary print
                print(line)

                parts = line.split(' ')

                # Address
                try:
                    address = int(parts[0])
                    if address != counter:
                        raise ValueError
                except ValueError as ex:
                    print(f"Error: invalid address, expected {counter:02d}\n")
                    error = True

                # Mnemonic
                try:
                    mnemonic = Mnemonic[parts[1]]
                except KeyError:
                    print(f"Error: invalid mnemonic '{parts[1]}'\n")
                    error = True
                except IndexError:
                    print(f"Error: missing mnemonic\n")
                    error = True

                # Data
                data = 0
                if mnemonic in cls.INSTRUCTIONS_WITH_DATA:
                    try:
                        data = int(parts[2])

                        if mnemonic in cls.INSTRUCTIONS_DATA_IS_ADDRESS:
                            if not 0 <= data < store_tmp.word_count:
                                raise ValueError()
                    except IndexError:
                        print(f"Error: missing data for '{mnemonic.name}' instruction\n")
                        error = True
                    except ValueError:
                        print(f"Error: '{mnemonic.name}' instruction requires a valid address (from 0 to {store.word_count-1})\n")
                        error = True

                # Write the line to the store
                word = BitArray(store_tmp.word_length)
                if mnemonic == Mnemonic.NUM:
                    # Write numerical value
                    data_bits = BitArray.from_int(data, store_tmp.word_length)
                    try:
                        word.engrave(0, data_bits)
                    except IndexError:
                        print("Error: Not enough space to store binary value\n")
                        error = True
                else:
                    # Write data
                    data_bits = BitArray.from_int(data, cls.ADDRESS_SIZE)
                    try:
                        word.engrave(0, data_bits)

                        # Write op code
                        word.engrave(cls.ADDRESS_SIZE, mnemonic.value)
                    except IndexError:
                        print("Error: Not enough space to store binary value\n")
                        error = True

                try:
                    store_tmp[counter] = word
                except IndexError:
                    print(f"Too many words for this machine (highest address is {store.word_count-1})\n")
                    error = True

                counter += 1

        if error:
            raise AssemblerError("Errors have been found in assembly program")

        # Finally, write the store
        for address, word in enumerate(store_tmp):
            store[address] = word

    @classmethod
    def disassemble(cls, store: Store) -> str:
        """Produce an assembly string from the given store

        It will try its best efforts to differentiate NUM to instructions, but does not guarranty a perfect result.
        """
        raise NotImplementedError

