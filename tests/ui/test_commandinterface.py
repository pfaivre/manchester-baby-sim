from threading import Event
from unittest import TestCase

from src.core.bitarray import BitArray
from src.machines.ssem import Ssem
from src.machines.ssemmodel import SsemModel
from src.ui.commandinterface import CommandInterface


class TestCommandInterface(TestCase):

    def setUp(self):
        self.machine = Ssem()
        self.interface = CommandInterface(self.machine, Event())

    def _instruction(self, mnemonic_name: str, data: int) -> BitArray:
        """Build a word containing the given instruction"""
        mnemonic = SsemModel.Mnemonic[mnemonic_name]
        word = BitArray(SsemModel.word_length)
        word.engrave(SsemModel.address_start, BitArray.from_int(data, SsemModel.address_length))
        word.engrave(SsemModel.opcode_start, BitArray.from_int(mnemonic.value, SsemModel.opcode_length))
        return word

    def test_interpretation_of_instruction_word(self):
        self.assertEqual(self.interface._word_interpretation(self._instruction("LDN", 29)), "LDN  29")

    def test_interpretation_of_instruction_sub2(self):
        self.assertEqual(self.interface._word_interpretation(self._instruction("SUB2", 29)), "SUB2 29")


    def test_interpretation_of_zero_word(self):
        self.assertEqual(self.interface._word_interpretation(BitArray(SsemModel.word_length)), "JMP  00")

    def test_interpretation_of_negative_data_word(self):
        # A negative number read as an instruction: -8192 has its opcode bits
        # all set (STP) and its address bits cleared (00)
        word = BitArray.from_int(-8192, SsemModel.word_length)
        self.assertEqual(self.interface._word_interpretation(word), "STP  00")

    def test_minimum_width(self):
        """The minimum width is the store's full display width"""
        # 1 pointer + 32 bits, then index, value and interpretation, plus
        # one spare column away from the last cell of the pad
        self.assertEqual(self.interface._minimum_width(), SsemModel.word_length + 27)

    def test_needs_redraw(self):
        """Redraw is needed after a key press or an instruction cycle, not while idle"""
        self.interface.dirty = False
        self.interface.last_drawn_cycle = self.machine.last_cycle
        self.assertFalse(self.interface._needs_redraw(), "Idle machine, no input")

        self.machine.instruction_cycle()
        self.assertTrue(self.interface._needs_redraw(), "The machine moved")

        # A drawn frame clears the need, until the next key press
        self.interface.dirty = False
        self.interface.last_drawn_cycle = self.machine.last_cycle
        self.assertFalse(self.interface._needs_redraw(), "Frame drawn")

        self.interface.dirty = True
        self.assertTrue(self.interface._needs_redraw(), "A key was pressed")
