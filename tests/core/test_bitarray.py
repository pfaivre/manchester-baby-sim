from unittest import TestCase

from src.core.bitarray import BitArray, b


class TestBitArray(TestCase):

    def setUp(self):
        pass

    def test___init__(self):
        self.assertEqual(
            list(BitArray(10)),
            [False, False, False, False, False, False, False, False, False, False]
        )

        self.assertEqual(
            list(BitArray(0)),
            []
        )

        with self.assertRaises(TypeError):
            # Missing size
            BitArray()

    def test_from_int(self):
        self.assertEqual(
            list(BitArray.from_int(123, 10)),
            [True, True, False, True, True, True, True, False, False, False],
            "From positive integer"
        )

        self.assertEqual(
            list(BitArray.from_int(-123, 10)),
            [True, False, True, False, False, False, False, True, True, True],
            "From negative integer"
        )

        self.assertEqual(
            list(b(30, 5)),
            [False, True, True, True, True],
            "30 in 5 digits"
        )

        self.assertEqual(
            list(b(0, 10)),
            [False, False, False, False, False, False, False, False, False, False],
            "zero"
        )

        self.assertEqual(
            list(b(-1, 10)),
            [True, True, True, True, True, True, True, True, True, True],
            "minus one"
        )

        self.assertEqual(
            list(b(-2, 10)),
            [False, True, True, True, True, True, True, True, True, True],
            "minus two"
        )

        with self.assertRaises(TypeError):
            # Missing digits
            BitArray.from_int(-123)

    def test_from_iterable(self):
        self.assertEqual(
            list(BitArray.from_iterable([True, False, True, True, True])),
            [True, False, True, True, True],
            "From iterable"
        )

    def test_from_string(self):
        self.assertEqual(
            list(BitArray.from_string("0b01101")),
            [False, True, True, False, True],
            "From string with prefix"
        )

        self.assertEqual(
            list(BitArray.from_string("10100")),
            [True, False, True, False, False],
            "From string without prefix"
        )

    def test_to_int(self):
        self.assertEqual(b(   123, 16).to_int(),   123, "Positive integer")
        self.assertEqual(b(  -123, 16).to_int(),  -123, "Negative integer")
        self.assertEqual(b(     0, 16).to_int(),     0, "zero")
        self.assertEqual(b(    -1, 16).to_int(),    -1, "minus one")
        self.assertEqual(b(-75637, 32).to_int(),-75637, "Negative integer")
        self.assertEqual(b(    30, 32).to_int(),    30, "30 in 32 digits")
        self.assertEqual(b(    30,  5).to_int(),    -2, "30 in 5 signed digits actually looks like -2")

    def test_to_unsigned_int(self):
        self.assertEqual(b(    30,  5).to_unsigned_int(),    30, "30 in 5 unsigned digits")

    def test_engrave(self):
        x = b("01000000000")
        y = b("1101")
        self.assertEqual(x.engrave(6, y), b("01000011010"))

        x = b("111111111111")
        y = b("0101")
        self.assertEqual(x.engrave(6, y), b("111111010111"))

        x = b("111111111111")
        y = b("0101")
        self.assertEqual(x.engrave(0, y), b("010111111111"))

        x = b("111111111111")
        y = b("0101")
        with self.assertRaises(IndexError):
            # outside boundaries
            x.engrave(10, y)

        x = b("111111111111")
        y = b("0000")
        self.assertEqual(x.engrave(-1, y), b("000111111110"), "Negative start index")

    def test_b(self):
        self.assertEqual(
            [True, True, False, True, True, True, True, False, False, False],
            list(b(123, 10)),
            "From positive integer"
        )

        self.assertEqual(
            [True, False, True, False, False, False, False, True, True, True],
            list(b(-123, 10)),
            "From negative integer"
        )

        with self.assertRaises(TypeError):
            # Missing digits
            b(-123)

        self.assertEqual(
            [True, True, True, False, True],
            list(b("0b11101")),
            "From string with prefix"
        )

        self.assertEqual(
            [True, False, True, False, True],
            list(b("10101")),
            "From string without prefix"
        )

        self.assertEqual(
            [True, False, True, True, True],
            list(b([True, False, True, True, True])),
            "From iterable"
        )

        with self.assertRaises(ValueError):
            # FLoat is unsuported
            b(1.1)

    def test___str__(self):
        self.assertEqual("........", str(BitArray(8)))
        self.assertEqual("_._._._.", str(b("10101010")))
        self.assertEqual("._._._._", str(b("01010101")))
        self.assertEqual("________", str(b("11111111")))
        self.assertEqual("........", str(b("00000000")))
        self.assertEqual("____....", str(b("11110000")))
        self.assertEqual("....____", str(b("00001111")))

        self.assertEqual("", str(b("")))
        self.assertEqual("_", str(b("1")))
        self.assertEqual(".", str(b("0")))

        self.assertEqual("___...___...___...", str(b("111000111000111000")))

