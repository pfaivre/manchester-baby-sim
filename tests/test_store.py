from unittest import TestCase

from bitarray import b
from store import Store


class TestStore(TestCase):

    def setUp(self):
        pass

    def test___init__(self):
        store = Store(23, 42)
        self.assertEqual(42, len(store._store), "Number of words")
        self.assertEqual(23, len(store._store[0]), "Size of words")

        store = Store(6, 4)
        self.assertEqual(b("000000"), store[0])
        self.assertEqual(b("000000"), store[1])
        self.assertEqual(b("000000"), store[2])
        self.assertEqual(b("000000"), store[3])

    def test_word_length(self):
        store = Store(10, 11)

        self.assertEqual(10, store.word_length, "Word length property")

    def test_word_length(self):
        store = Store(12, 13)

        self.assertEqual(13, store.word_count, "Word count property")

    def test_bracket_operator(self):
        store = Store(8, 3)

        self.assertEqual(b("00000000"), store[0])
        self.assertEqual(b("00000000"), store[1])
        self.assertEqual(b("00000000"), store[2])

        store[1] = b("10101010")

        self.assertEqual(b("00000000"), store[0])
        self.assertEqual(b("10101010"), store[1])
        self.assertEqual(b("00000000"), store[2])

    def test_clear(self):
        store = Store(8, 3)

        self.assertEqual(b("00000000"), store[0])
        self.assertEqual(b("00000000"), store[1])
        self.assertEqual(b("00000000"), store[2])

        store[0] = b("10101010")
        store[1] = b("11111111")
        store[2] = b("11110000")

        self.assertEqual(b("10101010"), store[0])
        self.assertEqual(b("11111111"), store[1])
        self.assertEqual(b("11110000"), store[2])

        store.clear()

        self.assertEqual(b("00000000"), store[0])
        self.assertEqual(b("00000000"), store[1])
        self.assertEqual(b("00000000"), store[2])

    def test___str__(self):
        store = Store(8, 3)

        store[0] = b("10101010")
        store[1] = b("11111111")
        store[2] = b("11110000")

        expected_result = """_._._._.
________
____...."""

        self.assertEqual(expected_result, str(store))

