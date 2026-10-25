from unittest import TestCase

from src.core.words import b, sign_extend, to_string


class TestWords(TestCase):

    def setUp(self):
        pass

    def test_b_from_int(self):
        self.assertEqual(b(123, 10), 123, "From positive integer")
        self.assertEqual(b(-123, 10), 901, "From negative integer (two's complement)")
        self.assertEqual(b(30, 5), 30, "30 in 5 digits")
        self.assertEqual(b(0, 10), 0, "Zero")
        self.assertEqual(b(-1, 10), 1023, "Minus one")

        with self.assertRaises(IndexError):
            b(1024, 10)  # Does not fit

        with self.assertRaises(IndexError):
            b(-1025, 10)  # Does not fit

        with self.assertRaises(TypeError):
            b(123)  # An integer requires a number of digits

    def test_b_from_string(self):
        self.assertEqual(b("0000000000"), 0, "All zeroes")
        self.assertEqual(b("1100000000"), 3, "Least significant bit first")
        self.assertEqual(b("0101"), 10, "Least significant bit first")
        self.assertEqual(b("0b0101"), 10, "Binary prefix")
        self.assertEqual(b(""), 0, "Empty string")

    def test_b_from_iterable(self):
        self.assertEqual(b([True, False, True]), 5, "Least significant bit first")
        self.assertEqual(b([1, 0, 0]), 1, "Values evaluated as boolean")
        self.assertEqual(b([]), 0, "Empty iterable")

        with self.assertRaises(TypeError):
            b(None)

    def test_sign_extend(self):
        self.assertEqual(sign_extend(0b011, 3), 3, "Positive value")
        self.assertEqual(sign_extend(0b111, 3), -1, "Negative value")
        self.assertEqual(sign_extend(0, 32), 0, "Zero")
        self.assertEqual(sign_extend(1 << 31, 32), -(1 << 31), "Most negative value")
        self.assertEqual(sign_extend((1 << 31) - 1, 32), (1 << 31) - 1, "Most positive value")

    def test_to_string(self):
        self.assertEqual(to_string(0, 4), "....", "Zero")
        self.assertEqual(to_string(0b101, 8), "_._.....", "Least significant bit first")
        self.assertEqual(to_string(0b11, 4, on="1", off="0"), "1100", "Custom characters")
        self.assertEqual(to_string(-1 & 0xFF, 8), "________", "All bits set")
