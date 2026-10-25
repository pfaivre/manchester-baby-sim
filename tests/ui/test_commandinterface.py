from threading import Event
from unittest import TestCase, mock

from src.core.words import b
from src.machines.breakpoints import CiValue, WordValue
from src.machines.ssem import Ssem
from src.machines.ssemmodel import SsemModel
from src.ui.breakpointpopup import BreakpointPopup
from src.ui.commandinterface import CommandInterface
from src.ui.helppopup import HelpPopup
from src.ui.keymap import KEYMAP, legend_segments


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

    def _popup_keys(self, *keys):
        """Feed the keys to the interface, one per getch, as if typed

        flushinp needs an initialized curses screen, unavailable in a test,
        so it is mocked.
        """
        class FakeScreen:
            def __init__(self):
                self.keys = list(keys)

            def getch(self):
                return self.keys.pop(0)

        screen = FakeScreen()
        with mock.patch("curses.flushinp"):
            while screen.keys:
                self.interface._handle_input(screen)

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
        keys = [text for text, highlighted in legend_segments() if highlighted]
        expected = [
            f" {key} " if len(key) == 1 else key
            for key, legend, _ in KEYMAP
            if legend is not None
        ]
        self.assertEqual(keys, expected)

    def test_help_window_geometry(self):
        """The pop-up is sized from KEYMAP, centered, and clamped to the terminal"""
        popup = HelpPopup()
        height, width, y, x = popup.geometry(50, 120)
        self.assertEqual(height, len(KEYMAP) + 6)
        self.assertEqual(y, (50 - height) // 2)
        self.assertEqual(x, (120 - width) // 2)
        # The widest help line fits with its margins and borders
        widest = max(len(description) for _, _, description in KEYMAP)
        self.assertGreaterEqual(width, widest + 8)

        # A small terminal clamps the pop-up instead of overflowing it
        self.assertEqual(popup.geometry(10, 20), (10, 20, 0, 0))

    def test_escape_quits(self):
        """Esc quits the application, like Q"""
        self._popup_keys(27)  # Esc
        self.assertTrue(self.interface.stop_event.is_set())

    def test_breakpoint_typing_adds_a_breakpoint(self):
        """Keys typed while the pop-up is open build and add a breakpoint"""
        self.interface.breakpoint_popup.open()
        self._popup_keys(
            ord("1"), ord("6"), 10,  # WORD: 16
            ord("1"), ord("2"), ord("8"), 10,  # VALUE: 128
        )

        self.assertEqual(
            self.machine.breakpoints,
            [WordValue(16, 128, SsemModel.word_length)],
        )
        self.assertEqual(
            self.interface.breakpoint_popup.field,
            BreakpointPopup.ADDRESS,
            "Fields reset for the next input",
        )

    def test_breakpoint_typing_negative_value(self):
        """The minus sign is accepted in the value field, not in the address field"""
        self.interface.breakpoint_popup.open()
        self._popup_keys(ord("-"), 10)  # Minus in the address field, then validate

        popup = self.interface.breakpoint_popup
        self.assertEqual(popup.buffer, "", "Minus rejected in the address field")
        self.assertEqual(popup.message, "TYPE A NUMBER", "An incomplete field is rejected")

        self._popup_keys(ord("3"), 10, ord("-"), ord("5"), 10)

        self.assertEqual(
            self.machine.breakpoints,
            [WordValue(3, -5, SsemModel.word_length)],
        )

    def test_breakpoint_typing_ci_condition(self):
        """T cycles the condition type: the CI condition takes one field only"""
        self.interface.breakpoint_popup.open()
        self._popup_keys(ord("t"), ord("3"), 10)

        self.assertEqual(self.machine.breakpoints, [CiValue(3)])
        self.assertEqual(
            self.interface.breakpoint_popup.field,
            BreakpointPopup.ADDRESS,
            "Fields reset for the next input",
        )

    def test_breakpoint_typing_rejects_bad_fields(self):
        """An out-of-range address or value is rejected with a message"""
        self.interface.breakpoint_popup.open()
        self._popup_keys(ord("9"), ord("9"), 10)

        popup = self.interface.breakpoint_popup
        self.assertEqual(popup.message, "ADDRESS MUST BE 0 TO 31")
        self.assertEqual(popup.field, BreakpointPopup.ADDRESS, "The field is kept for correction")

        self._popup_keys(ord("1"), 10, ord("5"), 10)  # WORD 1, VALUE 5: valid, added
        self.assertEqual(self.machine.breakpoints, [WordValue(1, 5, SsemModel.word_length)])

    def test_breakpoint_delete_key(self):
        """X removes the selected breakpoint"""
        self.interface.breakpoint_popup.open()
        self.machine.breakpoints.append(WordValue(16, 128, SsemModel.word_length))
        self.machine.breakpoints.append(WordValue(17, 256, SsemModel.word_length))

        self._popup_keys(ord("x"))

        self.assertEqual(self.machine.breakpoints, [WordValue(17, 256, SsemModel.word_length)])

    def test_breakpoint_popup_captures_machine_keys(self):
        """While the pop-up is open, machine keys do not reach the machine"""
        self.interface.breakpoint_popup.open()
        self.machine.stop_flag = False

        self._popup_keys(ord("p"))

        self.assertFalse(self.machine.stop_flag, "P was captured by the pop-up, the machine keeps running")

    def test_breakpoint_window_geometry(self):
        """The pop-up carries one line per breakpoint, and is clamped to the terminal"""
        self.machine.breakpoints = [
            WordValue(16, 128, SsemModel.word_length),
            WordValue(17, 256, SsemModel.word_length),
        ]
        popup = self.interface.breakpoint_popup
        height, width, y, x = popup.geometry(50, 120)
        self.assertEqual(height, 11, "2 breakpoints + 9 fixed lines")
        self.assertEqual(y, (50 - height) // 2)
        self.assertEqual(x, (120 - width) // 2)

        # The footer and the explanation fit in the width, with margins
        self.assertGreaterEqual(width, len(popup.FOOTER) + 4)
        self.assertGreaterEqual(width, len(popup.EXPLANATION) + 4)

        # A small terminal clamps the pop-up instead of overflowing it
        self.assertEqual(popup.geometry(10, 20), (10, 20, 0, 0))

    def test_breakpoint_input_line(self):
        """The input line shows the fields of the current type, the typed one underlined"""
        popup = self.interface.breakpoint_popup
        popup.field = BreakpointPopup.ADDRESS
        popup.buffer = "12"
        self.assertEqual(popup.input_line(), "NEW: WORD: 12_  VALUE:")

        popup.field = BreakpointPopup.VALUE
        popup.address = 12
        popup.buffer = "-5"
        self.assertEqual(popup.input_line(), "NEW: WORD: 12  VALUE: -5_")

        popup.kind = BreakpointPopup.KIND_CI
        popup.field = BreakpointPopup.ADDRESS
        popup.buffer = "3"
        self.assertEqual(popup.input_line(), "NEW: CI: 3_")
