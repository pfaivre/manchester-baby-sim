
from pathlib import Path
import re

from src.core.bitarray import BitArray, b
from src.core.store import Store


class AssemblerError(Exception):
    pass


class Assembler:
    """Assembler for Manchester-like machines
    """

    def __init__(self, model):
        self.model = model

    def load_file(self, file: Path, store: Store):
        """Load an assembly file into the given store
        """
        try:
            format = self._guess_file_format(file)
        except FileNotFoundError:
            raise AssemblerError(f"File {file} not found")

        match format:
            case "asm":
                self.load_asm(file, store)
            case "snp":
                self.load_snp(file, store)
            case _:
                raise AssemblerError("File format not recognized")

    def load_asm(self, file: Path, store: Store):
        """Load assembly file
        """
        store_tmp = Store(
            word_length=store.word_length,
            word_count=store.word_count
        )

        counter = 0

        with open(file, "r") as file:
            for line in file:
                # Cleaning
                line = line.rstrip('\n').split(';')[0].strip()
                if not line:
                    continue

                parts = line.split()

                # Address
                try:
                    address = int(parts[0])
                    if address != counter:
                        raise ValueError
                except ValueError as ex:
                    raise AssemblerError(f"Error: invalid address, expected {counter:02d}\n")

                # Mnemonic
                try:
                    mnemonic = self.model.Mnemonic[parts[1]]
                except KeyError:
                    raise AssemblerError(f"Error: invalid mnemonic '{parts[1]}'\n")
                except IndexError:
                    raise AssemblerError(f"Error: missing mnemonic\n")

                # Data
                data = 0
                if mnemonic in self.model.instructions_with_data:
                    try:
                        data = int(parts[2])

                        if mnemonic in self.model.instructions_data_is_address:
                            if not 0 <= data < store_tmp.word_count:
                                raise AssemblerError(f"Error: '{mnemonic.name}' instruction requires a valid address (from 0 to {store.word_count-1})\n")

                    except IndexError:
                        raise AssemblerError(f"Error: missing data for '{mnemonic.name}' instruction\n")
                    except ValueError:
                        raise AssemblerError(f"Error: '{mnemonic.name}' instruction requires a numeric value\n")

                # Write the line to the store
                word = BitArray(store_tmp.word_length)
                if mnemonic == self.model.Mnemonic.NUM:
                    # Write numerical value
                    try:
                        data_bits = BitArray.from_int(data, store_tmp.word_length)
                        word.engrave(0, data_bits)
                    except IndexError:
                        raise AssemblerError("Error: Number is too large, not enough space to store binary value\n")
                else:
                    # Write data
                    data_bits = BitArray.from_int(data, self.model.address_length)
                    try:
                        word.engrave(self.model.address_start, data_bits)

                        # Write op code
                        word.engrave(self.model.opcode_start, BitArray.from_int(mnemonic.value, self.model.opcode_length))
                    except IndexError:
                        raise AssemblerError("Error: Number is too large, not enough space to store binary value\n")

                try:
                    store_tmp[counter] = word
                except IndexError:
                    raise AssemblerError(f"Too many words for this machine (highest address is {store.word_count-1})\n")

                counter += 1

        # Finally, write the store
        for address, word in enumerate(store_tmp):
            store[address] = word

    def load_snp(self, file: Path, store: Store):
        """Load binary file
        """
        store_tmp = Store(
            word_length=store.word_length,
            word_count=store.word_count
        )

        counter = 0

        with open(file, "r") as file:
            for line in file:
                # Cleaning
                line = line.rstrip('\n').split(';')[0].strip()
                if not line:
                    continue

                parts = line.split(": ")

                # Address
                try:
                    address = int(parts[0])
                    if address != counter:
                        raise ValueError
                except ValueError:
                    raise AssemblerError(f"Error: invalid address, expected {counter:02d}\n")

                # Word
                try:
                    word = b(parts[1])
                except IndexError:
                    raise AssemblerError(f"Error: missing word\n")

                if len(word) != store.word_length:
                    raise AssemblerError(f"Error: word has a wrong length (got {len(word)}, expected {store.word_length}\n")

                try:
                    store_tmp[counter] = word
                except IndexError:
                    raise AssemblerError(f"Too many words for this machine (highest address is {store.word_count-1})\n")

                counter += 1

        # Finally, write the store
        for address, word in enumerate(store_tmp):
            store[address] = word

    def _guess_file_format(self, file: Path) -> str:
        """Open the file and try to guess its format from its content

        Can distinguish binary representation (.snp file) from assembly (.asm file)

        Return:
            "asm", "snp", "directory" or None
        """
        if Path(file).is_dir():
            return "directory"

        with open(file, "r") as file:
            for line in file:
                # Cleaning
                line = line.rstrip('\n').split(';')[0].strip()
                if not line:
                    continue

                if re.match(r"^\d+: [01]+$", line):
                    return "snp"

                if re.match(r"^\d+ \w+( \d+)?$", line):
                    return "asm"

        return None

    def decode_instruction(self, word: BitArray) -> tuple:
        """Read the given word and parses its components

        Params:
            word: The word to parse

        Returns:
            (command, data)
        """
        # Check the word is long enough to contain an instruction
        if len(word) < max(
            self.model.opcode_start + self.model.opcode_length,
            self.model.address_start + self.model.address_length
        ):
            raise AssemblerError(f"Error: Cannot read instruction, the given word is too short")

        # Read operation code (e.g. on SSEM, bits 13, 14 and 15)
        opcode = b(word[self.model.opcode_start:self.model.opcode_start+self.model.opcode_length]).to_unsigned_int()

        ## Read data (e.g. on SSEM, bits 0, 1, 2, 3 and 4)
        data = b(word[self.model.address_start:self.model.address_start+self.model.address_length]).to_unsigned_int()

        try:
            command = self.model.Mnemonic(opcode)
        except ValueError:
            raise AssemblerError(f"Error: Opcode '{opcode}' not recognized")


        return (command, data)

    def disassemble(self, store: Store) -> str:
        """Produce an assembly string from the given store

        It will try its best efforts to differentiate NUM to instructions, but does not guarranty a perfect result.
        """
        raise NotImplementedError

