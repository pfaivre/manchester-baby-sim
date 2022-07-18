
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

    def engrave(self, index: int, other):
        """Prints the bits of the given array to the current one at the given position

        Example:
            Let's consider:
                - self: '01000000000'
                - index: 6
                - other: '1101'
            Then self with eventually be: '01000011010'

        Arguments:
            index: Starting position in the current array
            other: Array to print to the current one
        """
        for b in other:
            self[index] = b
            index += 1

    def __eq__(self, other) -> bool:
        return isinstance(other, self.__class__) and list(self) == list(other)

    def __str__(self) -> str:
        """Visual representation of the array similar to what is found on the SSEM"""
        str_bits = ['_' if b else '.' for b in self]
        return "".join(map(str, str_bits))

