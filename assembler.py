from enum import Enum
from pathlib import Path

from bitarray import BitArray, b
from store import Store


class AssemblerError(Exception):
    pass


class Mnemonic(Enum):
    """Instruction set of the SSEM with operation code
    """
    JMP = b("000")
    JRP = b("100")
    LDN = b("010")
    STO = b("110")
    SUB = b("001")
    SUB2 = b("101")
    CMP = b("011")
    STP = b("111")
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
        Mnemonic.SUB2,
        Mnemonic.NUM
    )
    """Commands that need a data"""

    INSTRUCTIONS_DATA_IS_ADDRESS = (
        Mnemonic.JMP,
        Mnemonic.JRP,
        Mnemonic.LDN,
        Mnemonic.STO,
        Mnemonic.SUB,
        Mnemonic.SUB2
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

                parts = line.split(' ')

                # Address
                try:
                    address = int(parts[0])
                    if address != counter:
                        raise ValueError
                except ValueError as ex:
                    print(line)
                    print(f"Error: invalid address, expected {counter:02d}\n")
                    error = True

                # Mnemonic
                try:
                    mnemonic = Mnemonic[parts[1]]
                except KeyError:
                    print(line)
                    print(f"Error: invalid mnemonic '{parts[1]}'\n")
                    error = True
                except IndexError:
                    print(line)
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
                        print(line)
                        print(f"Error: missing data for '{mnemonic.name}' instruction\n")
                        error = True
                    except ValueError:
                        print(line)
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
                        print(line)
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
                        print(line)
                        print("Error: Not enough space to store binary value\n")
                        error = True

                try:
                    store_tmp[counter] = word
                except IndexError:
                    print(line)
                    print(f"Too many words for this machine (highest address is {store.word_count-1})\n")
                    error = True

                counter += 1

        if error:
            raise AssemblerError("Errors have been found in assembly program")

        # Finally, write the store
        for address, word in enumerate(store_tmp):
            store[address] = word

    @classmethod
    def decode_instruction(cls,
        word: BitArray,
        address_start: int = 0,
        address_length: int = 5,
        opcode_start: int = 13,
        opcode_length: int = 3) -> tuple:
        """Read the given word and parses its components

        Params:
            word: The word to parse
            address_start: The position of the address in the word
            address_length: The address size in bits
            opcode_start: The position of the operation code in the word
            opcode_length: The operation code size in bits

        Returns:
            (command, data)
        """
        # Read operation code (e.g. on SSEM, bits 13, 14 and 15)
        opcode = b(word[opcode_start:opcode_start+opcode_length])
        command = Mnemonic(opcode)

        ## Read data (e.g. on SSEM, bits 0, 1, 2, 3 and 4)
        data = b(word[address_start:address_start+address_length]).to_unsigned_int()

        return (command, data)

    @classmethod
    def disassemble(cls, store: Store) -> str:
        """Produce an assembly string from the given store

        It will try its best efforts to differentiate NUM to instructions, but does not guarranty a perfect result.
        """
        raise NotImplementedError

