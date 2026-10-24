
from collections.abc import Iterable


class BitArray(list):
    """Simple implementation of bit array in the form of List of boolean values

    Provides manipulation routines useful for simulating a Manchester-like machine
    """

    def __init__(self, size: int):
        array = [False] * size
        super().__init__(array)

    @classmethod
    def from_int(cls, value: int, digits: int):
        """Creates a BitArray from an integer following SSEM binary convention

        Arguments:
            value: integer value to translate
            digits: number of bits of the resulting array

        Raises:
            IndexError: when the value does not fit in the given number of bits
        """
        if not -pow(2, digits) <= value < pow(2, digits):
            raise IndexError(f"Value {value} does not fit in {digits} bits")

        # Negative values are stored in two's complement form
        if value < 0:
            value += pow(2, digits)

        # Write the bits, least significant one first
        array = cls(digits)
        for i in range(digits):
            array[i] = bool(value & (1 << i))

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
        """Get the signed value of the binary in SSEM format (from left to right)"""
        value = self.to_unsigned_int()

        # Interpret the most significant bit as a sign (two's complement)
        if value & (1 << (len(self) - 1)):
            value -= 1 << len(self)

        return value

    def to_unsigned_int(self) -> int:
        """Get the unsigned value of the binary in SSEM format (from left to right)"""
        # The first bit of the array is the least significant one
        return sum(bit << i for i, bit in enumerate(self))

    def engrave(self, index: int, other):
        """Prints the bits of the given array to the current one at the given position

        Example: ::

            array = b("01000000000").engrave(6, b("1101"))
            # array is now b("01000011010")

        Arguments:
            index: Starting position in the current array
            other: Array to print to the current one

        Raises:
            IndexError: when writing outside of the original BitArray
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

    def __repr__(self) -> str:
        # Not a regular use of repr, but simplifies a lot the debugging
        return str(self)


def b(value, digits: int=None) -> BitArray:
    """Convert a value to a BitArray"""
    if isinstance(value, int):
        return BitArray.from_int(value, digits=digits)
    elif isinstance(value, str):
        return BitArray.from_string(value)
    elif isinstance(value, Iterable):
        return BitArray.from_iterable(value)
    else:
        raise ValueError(f"Unsupported type {type(value)}")

