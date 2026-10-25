from threading import Event
from unittest import TestCase, mock

from src.core.words import b
from src.machines.ssem import Ssem
from src.machines.ssemmodel import SsemModel
from src.ui.commandinterface import CommandInterface


class TestCommandInterface(TestCase):

    def setUp(self):
        self.machine = Ssem()
        self.interface = CommandInterface(self.machine, Event())

    def _instruction(self, mnemonic_name: str, data: int) -> int:
        """Build a word containing the given instruction"""
        mnemonic = SsemModel.Mnemonic[mnemonic_name]
        return (
            (data << SsemModel.address_start)
            | (mnemonic.value << SsemModel.opcode_start)
        )

    def test_interpretation_of_instruction_word(self):
        self.assertEqual(self.interface._word_interpretation(self._instruction("LDN", 29)), "LDN  29")

    def test_interpretation_of_instruction_sub2(self):
        self.assertEqual(self.interface._word_interpretation(self._instruction("SUB2", 29)), "SUB2 29")


    def test_interpretation_of_zero_word(self):
        self.assertEqual(self.interface._word_interpretation(0), "JMP  00")

    def test_interpretation_of_negative_data_word(self):
        # A negative number read as an instruction: -8192 has its opcode bits
        # all set (STP) and its address bits cleared (00)
        word = b(-8192, SsemModel.word_length)
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

    def test_legend_segments_follow_keymap(self):
        """The bottom bar legend is built from KEYMAP, without the pop-up-only keys"""
        keys = [text for text, highlighted in self.interface._legend_segments() if highlighted]
        expected = [
            f" {key} " if len(key) == 1 else key
            for key, legend, _ in CommandInterface.KEYMAP
            if legend is not None
        ]
        self.assertEqual(keys, expected)

    def test_help_window_geometry(self):
        """The pop-up is sized from KEYMAP, centered, and clamped to the terminal"""
        height, width, y, x = self.interface._help_window_geometry(50, 120)
        self.assertEqual(height, len(CommandInterface.KEYMAP) + 6)
        self.assertEqual(y, (50 - height) // 2)
        self.assertEqual(x, (120 - width) // 2)
        # The widest help line fits with its margins and borders
        widest = max(len(description) for _, _, description in CommandInterface.KEYMAP)
        self.assertGreaterEqual(width, widest + 8)

        # A small terminal clamps the pop-up instead of overflowing it
        self.assertEqual(self.interface._help_window_geometry(10, 20), (10, 20, 0, 0))

    def test_escape_quits(self):
        """Esc quits the application, like Q"""
        class FakeScreen:
            def getch(self):
                return 27  # Esc

        # flushinp needs an initialized curses screen, unavailable in a test
        with mock.patch("curses.flushinp"):
            self.interface._handle_input(FakeScreen())
        self.assertTrue(self.interface.stop_event.is_set())
