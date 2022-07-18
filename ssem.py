
from bitarray import BitArray
from store import Store


class Ssem:
    """Simulator of the Small-Scale Experimental Machine (SSEM), a.k.a. Manchester Baby

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
        - Typically performs at around 700 instructions per seconds
    """

    WORD_LENGTH = 32
    """Size of the words in the original SSEM (Manchester Baby)"""

    WORD_COUNT = 32
    """Number of words in the original SSEM (Manchester Baby)"""

    TYPICAL_SPEED = 700
    """Typical execution speed in intructions per seconds"""

    def __init__(self):
        self.store = Store(word_length=self.WORD_LENGTH, word_count=self.WORD_COUNT)
        self.ci = BitArray(self.WORD_LENGTH)
        self.a = BitArray(self.WORD_LENGTH)

    def next_step():
        """Execute the next instruction"""
        raise NotImplementedError

    def start():
        """Start the machine until stop instruction is met"""
        raise NotImplementedError

    def clear_store(self):
        """Reset the store to zero"""
        self.store.clear()

    def clear_state(self):
        """Reset the program counter and the accumulator to zero"""
        self.ci = BitArray(self.WORD_LENGTH)
        self.a = BitArray(self.WORD_LENGTH)

