from unittest import TestCase

from src.core.words import b
from src.machines.breakpoints import CiValue, WordValue
from src.machines.ssem import Ssem
from src.machines.ssemmodel import SsemModel


class TestWordValue(TestCase):

    def setUp(self):
        self.ssem = Ssem()

    def test_not_met_on_a_different_value(self):
        """The breakpoint does not hold while the word has another value"""
        breakpoint = WordValue(16, 128, SsemModel.word_length)
        self.ssem.store[16] = b(127, SsemModel.word_length)

        self.assertFalse(breakpoint.is_met(self.ssem))

    def test_met_on_the_value(self):
        """The condition holds when the word carries the given value"""
        breakpoint = WordValue(16, 128, SsemModel.word_length)
        self.ssem.store[16] = b(128, SsemModel.word_length)

        self.assertTrue(breakpoint.is_met(self.ssem))

    def test_rising_edge(self):
        """The breakpoint triggers once when the condition turns true, not while it stays true"""
        breakpoint = WordValue(16, 128, SsemModel.word_length)

        self.ssem.store[16] = b(128, SsemModel.word_length)
        self.assertTrue(breakpoint.is_met(self.ssem), "Condition just turned true")

        self.assertFalse(breakpoint.is_met(self.ssem), "Condition still true, no new trigger")

        self.ssem.store[16] = b(0, SsemModel.word_length)
        self.assertFalse(breakpoint.is_met(self.ssem), "Condition turned false")

        self.ssem.store[16] = b(128, SsemModel.word_length)
        self.assertTrue(breakpoint.is_met(self.ssem), "Condition turned true again: the breakpoint is still armed")

    def test_negative_value(self):
        """A negative value is stored as its two's complement word"""
        breakpoint = WordValue(3, -5, SsemModel.word_length)
        self.ssem.store[3] = b(-5, SsemModel.word_length)

        self.assertTrue(breakpoint.is_met(self.ssem))

    def test_value_out_of_word(self):
        """A value that does not fit in a word is rejected at construction"""
        with self.assertRaises(IndexError):
            WordValue(16, 1 << SsemModel.word_length, SsemModel.word_length)

    def test_address_out_of_store(self):
        """Checking a breakpoint addressing a word beyond the store raises"""
        breakpoint = WordValue(50, 0, SsemModel.word_length)
        with self.assertRaises(IndexError):
            breakpoint.is_met(self.ssem)

    def test_description(self):
        """The description shows the address and the signed value"""
        self.assertEqual(WordValue(16, 128, SsemModel.word_length).description(), "WORD 16 = 128")
        self.assertEqual(WordValue(3, -5, SsemModel.word_length).description(), "WORD 03 = -5")

    def test_equality(self):
        """Two breakpoints on the same address and value are the same condition"""
        self.assertEqual(
            WordValue(16, 128, SsemModel.word_length),
            WordValue(16, 128, SsemModel.word_length),
        )
        self.assertNotEqual(
            WordValue(16, 128, SsemModel.word_length),
            WordValue(17, 128, SsemModel.word_length),
        )


class TestCiValue(TestCase):

    def setUp(self):
        self.ssem = Ssem()

    def test_met_when_ci_points_at_the_address(self):
        """The condition holds while CI points at the given word"""
        breakpoint = CiValue(12)
        self.ssem.ci = 12

        self.assertTrue(breakpoint.is_met(self.ssem))

    def test_rising_edge(self):
        """The breakpoint triggers when CI arrives at the address, not while it stays there"""
        breakpoint = CiValue(12)

        self.ssem.ci = 12
        self.assertTrue(breakpoint.is_met(self.ssem), "CI just arrived at the address")
        self.assertFalse(breakpoint.is_met(self.ssem), "CI still there, no new trigger")

        self.ssem.ci = 11
        self.assertFalse(breakpoint.is_met(self.ssem), "CI moved away")

        self.ssem.ci = 12
        self.assertTrue(breakpoint.is_met(self.ssem), "CI arrived again: the breakpoint is still armed")

    def test_description(self):
        """The description shows the watched address"""
        self.assertEqual(CiValue(3).description(), "CI = 03")

    def test_equality(self):
        """Two CI breakpoints on the same address are the same condition, distinct from a word one"""
        self.assertEqual(CiValue(3), CiValue(3))
        self.assertNotEqual(CiValue(3), CiValue(4))
        self.assertNotEqual(CiValue(3), WordValue(3, 0, SsemModel.word_length))
