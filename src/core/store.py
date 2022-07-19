
from src.core.bitarray import BitArray


class Store:
    """Main memory of a Manchester-like machine

    It is a collection of words of a given size.
    For example, the SSEM had 32 words of 32 bits each, for a total of 1024 bits.
    """

    def __init__(self, word_length: int, word_count: int):
        self._word_length = word_length
        self._word_count = word_count
        self.clear()

    @property
    def word_length(self) -> int:
        """The size of a word in bits"""
        return self._word_length

    @property
    def word_count(self) -> int:
        """The number of words contained in the store"""
        return self._word_count

    def __getitem__(self, address: int) -> BitArray:
        """Get the word at the given address"""
        return self._store[address]

    def __setitem__(self, address: int, word: BitArray):
        """Replace the word at the given address"""
        self._store[address] = word

    def clear(self):
        """Fill the entire store with zeros"""
        empty_line = BitArray(self._word_length)
        self._store = [
            empty_line for _ in range(0, self._word_count)
        ]

    def __str__(self) -> str:
        """Get a visual representation of the store"""
        lines = [str(line) for line in self._store]
        return "\n".join(lines)
