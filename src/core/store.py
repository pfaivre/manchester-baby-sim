from src.core.words import to_string


class Store:
    """Main memory of a Manchester-like machine

    It is a collection of words of a given size.
    For example, the SSEM had 32 words of 32 bits each, for a total of 1024 bits.

    Words are plain ints (bit 0 = least significant bit, two's complement for
    negative values); see src/core/words.py.
    """

    def __init__(self, word_length: int, word_count: int):
        self._word_length = word_length
        self._word_count = word_count
        self._word_mask = (1 << word_length) - 1
        self._store = [0] * word_count

    @property
    def word_length(self) -> int:
        """The size of a word in bits"""
        return self._word_length

    @property
    def word_count(self) -> int:
        """The number of words contained in the store"""
        return self._word_count

    def __getitem__(self, address: int) -> int:
        """Get the word at the given address"""
        return self._store[address]

    def __setitem__(self, address: int, word: int):
        """Replace the word at the given address"""
        self._store[address] = word & self._word_mask

    def clear(self):
        """Fill the entire store with zeros"""
        # In place, so references taken by the machine's run loop stay valid
        self._store[:] = [0] * self._word_count

    def __str__(self) -> str:
        """Get a visual representation of the store"""
        return "\n".join(to_string(word, self._word_length) for word in self._store)
