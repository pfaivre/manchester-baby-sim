
from enum import Enum


class SsemModel:
    """Describes the main characteristics of the original SSEM
    """

    word_length = 32
    """Size of the words"""

    word_count = 32
    """Number of words in the store"""

    address_start = 0
    """Position of the address an instruction"""

    address_length = 5
    """Size of addresses in bits"""

    opcode_start = 13
    """Position of the operation code in the word"""

    opcode_length = 3
    """Operation code size in bits"""

    typical_speed = 700
    """Typical execution speed in intructions per seconds"""

    class Mnemonic(Enum):
        """Instruction set with operation codes
        """
        JMP = 0   # 000
        JRP = 1   # 100
        LDN = 2   # 010
        STO = 3   # 110
        SUB = 4   # 001
        SUB2 = 5  # 101
        CMP = 6   # 011
        STP = 7   # 111
        NUM = None

    instructions_with_data = (
        Mnemonic.JMP,
        Mnemonic.JRP,
        Mnemonic.LDN,
        Mnemonic.STO,
        Mnemonic.SUB,
        Mnemonic.SUB2,
        Mnemonic.NUM
    )
    """Commands that need a data"""

    instructions_data_is_address = (
        Mnemonic.JMP,
        Mnemonic.JRP,
        Mnemonic.LDN,
        Mnemonic.STO,
        Mnemonic.SUB,
        Mnemonic.SUB2
    )
    """Commands of which data must be an address"""

