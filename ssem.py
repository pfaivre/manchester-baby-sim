
from time import sleep
from abstractmachine import AbstractMachine
from assembler import Assembler, Mnemonic

from bitarray import BitArray, b
from store import Store


class Ssem(AbstractMachine):
    """Simulator for the original Small-Scale Experimental Machine (SSEM), a.k.a. Manchester Baby built in 1948

    It features:
        - A store of 32 words of 32 bits each (1024 bits total)
        - A program counter (CI) of 32 bits
        - An accumulator (A) of 32 bits
        - 7 instructions:
            - JMP S: Jump to the address specified at the address S
            - JRP S: Jump to the instruction at address CI + value of S
            - LDN S: Load the negative value of address S to the accumulator
            - STO S: Stores the value of the accumulator to address S
            - SUB S: Substract the value in address S from the accumulator
            - CMP: Skip next instruction if the accumulator contains a negative value
            - STP: Stop the execution
        - Address size: 5 bits
        - Typically performs at around 700 instructions per seconds
    """

    WORD_LENGTH = 32
    """Size of the words in the original SSEM (Manchester Baby)"""

    WORD_COUNT = 32
    """Number of words in the original SSEM (Manchester Baby)"""

    ADDRESS_LENGTH = 5
    """Size of addresses in bits"""

    TYPICAL_SPEED = 700
    """Typical execution speed in intructions per seconds"""

    def __init__(self):
        self.store = Store(word_length=self.WORD_LENGTH, word_count=self.WORD_COUNT)
        self.ci = BitArray(self.WORD_LENGTH)
        self.a = BitArray(self.WORD_LENGTH)
        self.stop_flag = True

    def instruction_cycle(self):
        """Performs one instruction cycle

        It first increments the program counter, then decodes the next instruction and executes it.
        """
        # Fetch
        ci_int = self.ci.to_int()
        ci_int += 1
        self.ci = b(ci_int, self.WORD_LENGTH)

        # Decode
        word = self.store[ci_int]
        command, data = Assembler.decode_instruction(
            word,
            address_start=0,
            address_length=self.ADDRESS_LENGTH,
            opcode_start=13,
            opcode_length=3
        )
        print(f"{ci_int} {command.name} {data}")

        # Execute
        match command:
            case Mnemonic.JMP:
                # Change the next address to execute
                self.ci = b(self.store[data])  # Copy the array

            case Mnemonic.JRP:
                # Jump to the instruction at address CI + value of S
                value = self.store[data].to_int()
                ci_int = self.ci.to_int()
                self.ci = b(value + ci_int, self.WORD_LENGTH)

            case Mnemonic.LDN:
                # Fetch the negated value
                value = -self.store[data].to_int()
                # Save it to the accumulator
                self.a = b(value, self.WORD_LENGTH)

            case Mnemonic.STO:
                # Save the value of the accumulator to the given address
                self.store[data] = b(self.a)

            case Mnemonic.SUB | Mnemonic.SUB2:
                s_int = self.store[data].to_int()
                a_int = self.a.to_int()
                # Save (accumulator - S) to the accumulator
                self.a = b(a_int - s_int, self.WORD_LENGTH)

            case Mnemonic.CMP:
                # Skip next line if accumulator is negative
                if self.a.to_int() < 0:
                    ci_int = self.ci.to_int() + 1
                    self.ci = b(ci_int, self.WORD_LENGTH)

            case Mnemonic.STP:
                self.stop_flag = True

            case _:
                raise Exception(f"Unsuported command '{command.value}'")

    def start(self):
        """Start the machine until stop instruction is met
        """

        self.stop_flag = False

        while not self.stop_flag:
            # TODO: make a proper interface
            print(f"{self.ci}  CI")
            print(f"{self.a}  A")
            print()
            store_str = str(self.store).split("\n")
            ci_int = self.ci.to_unsigned_int()
            store_str[ci_int] = "\033[1m" + store_str[ci_int] + "\033[0m"
            print("\n".join(store_str))
            self.instruction_cycle()
            sleep(1 / self.TYPICAL_SPEED)

    def clear_memory(self):
        """Reset the store to zero"""
        self.store.clear()

    def clear_state(self):
        """Reset the program counter and the accumulator to zero"""
        self.ci = BitArray(self.WORD_LENGTH)
        self.a = BitArray(self.WORD_LENGTH)

