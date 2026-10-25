from collections.abc import Iterable


def b(value, digits: int | None = None) -> int:
    """Convert a value to a machine word (an int)

    A word is a plain int whose bits follow the SSEM convention: bit 0 is the
    least significant one, and negative values are stored in two's complement.

    Arguments:
        value: int, string of 0 and 1 (least significant bit first, optionally
            prefixed with "0b"), or iterable of booleans
        digits: number of bits of the word, required for an int value

    Raises:
        IndexError: when an int value does not fit in the given number of bits
    """
    if isinstance(value, int):
        if digits is None:
            raise TypeError("An integer value requires a number of digits")
        limit = 1 << digits
        if not -limit <= value < limit:
            raise IndexError(f"Value {value} does not fit in {digits} bits")

        # Negative values are stored in two's complement form
        return value & (limit - 1)

    elif isinstance(value, str):
        value = value.removeprefix("0b")

        # Write the bits, least significant one first
        word = 0
        for i, char in enumerate(value):
            word |= (char != "0") << i

        return word

    elif isinstance(value, Iterable):
        word = 0
        for i, bit in enumerate(value):
            word |= bool(bit) << i

        return word

    else:
        raise TypeError(f"Unsupported type {type(value)}")


def sign_extend(word: int, digits: int) -> int:
    """Get the signed value of a two's complement word of the given size"""
    if word & (1 << (digits - 1)):
        return word - (1 << digits)

    return word


def to_string(word: int, digits: int, on: str = "_", off: str = ".") -> str:
    """Visual representation of a word, similar to what is found on the SSEM

    Bits are written least significant one first, as `on`/`off` characters.
    """
    return format(word, f"0{digits}b")[::-1].translate(str.maketrans("01", off + on))