
from typing import Iterable


class BitArray(list):
    """Simple implementation of bit array in the form of List of boolean values

    Provides manipulation routines useful for simulating a Manchester-like machine
    """

    def __init__(self, size: int):
        array = [False for _ in range(0, size)]
        super().__init__(array)

    @classmethod
    def from_int(cls, value: int, digits: int):
        """Creates a BitArray from an integer following SSEM binary convention

        Arguments:
            value: integer value to translate
        """
        array = BitArray(digits)

        # Positive value: regular conversion
        if value >= 0:
            # Binary transcription (note it is right-to-left in Python)
            bits = bin(value).split("0b")[1]

            # Padding with zeros
            while len(bits) < digits:
                bits = '0' + bits

            # Reverse bits and write them in a BitArray
            bits = list(bits)
            bits.reverse()
            array.engrave(0, map(lambda b: b != '0', bits))

        # Negative value: two's complement
        else:
            # TODO: test that
            # Compute two's complements
            value = -1 * value
            bits = bin(value - pow(2, digits)).split("0b")[1]

            # Reverse bits and write them in a BitArray
            bits = list(bits)
            bits.reverse()
            array.engrave(0, map(lambda b: b != '0', bits))

        return array

    @classmethod
    def from_iterable(cls, value: Iterable):
        """Creates a BitArray from an iterable

        Arguments:
            value: Iterable containing objects that can be evaluated as boolean
        """
        array = BitArray(len(value))

        for i in range(len(value)):
            array[i] = bool(value[i])

        return array

    @classmethod
    def from_string(cls, value: str):
        """Creates a BitArray from a string containing 0 and 1

        Arguments:
            value: A string with 0 and 1, optionally prefixed with "0b"
        """
        if value.startswith("0b"):
            value = value.split("0b")[1]

        array = BitArray(len(value))

        for i in range(len(value)):
            array[i] = value[i] != "0"

        return array

    def to_int(self) -> int:
        """Get the integer value of the binary in SSEM format (from left to right)"""
        def twos_complement(value, bits):
            """compute the two's complement of integer value"""
            if (value & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
                value = value - (1 << bits)      # compute negative value
            return value                         # return positive value as is

        # Copy the list
        bits = list(self)

        # Reverse bit order
        bits.reverse()

        # Convert to 0 and 1 string
        bits = "0b" + ''.join(['1' if b else '0' for b in bits])

        # Convert to int
        return twos_complement(int(bits, 2), len(self))

    def to_unsigned_int(self) -> int:
        """Get the integer value of the binary in SSEM format (from left to right)"""
        # Copy the list
        bits = list(self)

        # Reverse bit order
        bits.reverse()

        # Convert to 0 and 1 string
        bits = "0b" + ''.join(['1' if b else '0' for b in bits])

        # Convert to int
        return int(bits, 2)

    def engrave(self, index: int, other):
        """Prints the bits of the given array to the current one at the given position

        Example: ::

            array = b("01000000000").engrave(6, b("1101"))
            # array is now b("01000011010")

        Arguments:
            index: Starting position in the current array
            other: Array to print to the current one
        """
        for b in other:
            self[index] = b
            index += 1

        return self

    def __eq__(self, other) -> bool:
        return isinstance(other, self.__class__) and list(self) == list(other)

    def __str__(self) -> str:
        """Visual representation of the array similar to what is found on the SSEM"""
        str_bits = ['_' if b else '.' for b in self]
        return "".join(map(str, str_bits))


def b(value, digits: int=None) -> BitArray:
    """Convert a value to a BitArray"""
    from collections.abc import Iterable

    if isinstance(value, int):
        return BitArray.from_int(value, digits=digits)
    elif isinstance(value, str):
        return BitArray.from_string(value)
    elif isinstance(value, Iterable):
        return BitArray.from_iterable(value)
    else:
        raise ValueError(f"Unsupported type {type(value)}")

