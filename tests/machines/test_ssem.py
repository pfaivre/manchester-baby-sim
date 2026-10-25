import tempfile
from pathlib import Path
from threading import Event, Thread
from time import sleep, time
from unittest import TestCase

from src.core.store import Store
from src.core.words import b, sign_extend
from src.machines.abstractmachine import MachineRuntimeError
from src.machines.breakpoints import CiValue, WordValue
from src.machines.ssem import Ssem
from src.machines.ssemmodel import SsemModel


class TestSsem(TestCase):

    def setUp(self):
        self.ssem = Ssem()

    def _temp_file(self, content: str, suffix: str = ".asm") -> Path:
        """Write the given content to a temporary file and return its path"""
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name) / f"program{suffix}"
        path.write_text(content)
        return path

    def _instruction(self, mnemonic_name: str, data: int) -> int:
        """Build a word containing the given instruction"""
        mnemonic = SsemModel.Mnemonic[mnemonic_name]
        return (
            (data << SsemModel.address_start)
            | (mnemonic.value << SsemModel.opcode_start)
        )

    def test___init__(self):
        """A fresh machine is stopped, with zeroed store, CI and accumulator"""
        self.assertFalse(self.ssem.is_running)
        self.assertEqual(self.ssem.ci, b("0" * 32), "CI")
        self.assertEqual(self.ssem.a, b("0" * 32), "Accumulator")
        self.assertEqual(self.ssem.store[17], b("0" * 32), "Store")
        self.assertEqual(self.ssem.last_cycle, 0)
        self.assertEqual(self.ssem.last_instruction, "")

    def test___init___with_file(self):
        """A program file given at construction is loaded into the store"""
        program = (
            "00 NUM 0\n"
            "01 LDN 04    ; A = -X\n"
            "02 STP\n"
            "03 NUM 0\n"
            "04 NUM 5"
        )
        ssem = Ssem(file=self._temp_file(program))

        self.assertEqual(ssem.store[1], b("00100000000000100000000000000000"), "01 LDN 04")
        self.assertEqual(ssem.store[4], b("10100000000000000000000000000000"), "04 NUM 5")
        self.assertEqual(ssem.store[0], b("0" * 32), "00 NUM 0")

    def test_instruction_cycle(self):
        """A cycle increments CI, then fetches and executes the instruction at the new CI"""
        self.ssem.store[1] = self._instruction("LDN", 4)
        self.ssem.store[2] = self._instruction("STP", 0)
        self.ssem.store[4] = b(5, SsemModel.word_length)

        instruction = self.ssem.instruction_cycle()

        self.assertEqual(sign_extend(self.ssem.ci, SsemModel.word_length), 1, "CI incremented to the executed address")
        self.assertEqual(sign_extend(self.ssem.a, SsemModel.word_length), -5, "LDN loads the negated value")
        self.assertEqual(instruction, "01 LDN 04")
        self.assertEqual(self.ssem.last_instruction, "01 LDN 04")
        self.assertEqual(self.ssem.last_cycle, 1)

        self.ssem.instruction_cycle()  # STP

        self.assertFalse(self.ssem.is_running, "STP stops the machine")

    def test_instruction_cycle_out_of_bound(self):
        """An instruction addressing a word beyond the store boundaries raises a runtime error"""
        self.ssem.store = Store(SsemModel.word_length, 4)
        self.ssem.store[1] = self._instruction("LDN", 8)

        with self.assertRaises(MachineRuntimeError):
            self.ssem.instruction_cycle()

    def test_execute_unsupported_command(self):
        """A word decoding to a non-instruction mnemonic cannot be executed"""
        # Defensive branch: unreachable through instruction_cycle, since every
        # opcode of the model matches a cased instruction
        with self.assertRaises(MachineRuntimeError):
            self.ssem._execute(SsemModel.Mnemonic.NUM, 0)

    def test_start_stopped(self):
        """A machine started in stopped state idles until its stop event is set"""
        stop_event = Event()
        thread = Thread(target=self.ssem.start, kwargs={"stop_event": stop_event, "stopped": True})
        thread.start()

        sleep(0.3)
        self.assertFalse(self.ssem.is_running)
        self.assertEqual(self.ssem.last_cycle, 0, "No instruction executed while stopped")

        stop_event.set()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

    def test_start_stops_on_stp_instruction(self):
        """The machine runs by itself until it meets a STP instruction"""
        program = (
            "00 NUM 0\n"
            "01 LDN 04\n"
            "02 STP\n"
            "03 NUM 0\n"
            "04 NUM 5"
        )
        ssem = Ssem(file=self._temp_file(program))
        stop_event = Event()
        thread = Thread(target=ssem.start, kwargs={"stop_event": stop_event})
        thread.start()

        # The program ends on its own
        deadline = time() + 5
        while not ssem.stop_flag and time() < deadline:
            sleep(0.01)
        self.assertTrue(ssem.stop_flag, "The STP instruction stopped the machine")
        self.assertEqual(ssem.last_instruction, "02 STP 00")
        self.assertEqual(sign_extend(ssem.a, SsemModel.word_length), -5, "The accumulator holds the LDN result")

        stop_event.set()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

    def test_start_stop_event_interrupts(self):
        """An external stop event interrupts a machine running an endless program"""
        program = (
            "00 NUM 0\n"
            "01 JRP 03\n"
            "02 STP\n"
            "03 NUM -1"
        )
        ssem = Ssem(file=self._temp_file(program))
        stop_event = Event()
        thread = Thread(target=ssem.start, kwargs={"stop_event": stop_event})
        thread.start()

        sleep(0.3)  # The machine is looping on the JRP instruction
        self.assertGreater(ssem.last_cycle, 1, "The machine is running")
        stop_event.set()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive(), "The stop event interrupted the machine")
        self.assertFalse(ssem.stop_flag, "The STP instruction was never reached")

    def test_clear_memory_and_state(self):
        """clear_memory and clear_state reset the store and the registers"""
        self.ssem.store[5] = b(123, SsemModel.word_length)
        self.ssem.ci = b(7, SsemModel.word_length)
        self.ssem.a = b(-9, SsemModel.word_length)

        self.ssem.clear_memory()
        self.assertEqual(self.ssem.store[5], b("0" * 32), "Store cleared")

        self.ssem.clear_state()
        self.assertEqual(sign_extend(self.ssem.ci, SsemModel.word_length), 0, "CI cleared")
        self.assertEqual(sign_extend(self.ssem.a, SsemModel.word_length), 0, "Accumulator cleared")

    def test_breakpoint_pauses_the_machine(self):
        """A breakpoint pauses the machine on the cycle that makes its condition true"""
        # LDN 05: A = 128, STO 16: word 16 = 128, JRP 06: jump back to 01
        program = (
            "00 NUM 0\n"
            "01 LDN 05\n"
            "02 STO 16\n"
            "03 JRP 06\n"
            "04 NUM 0\n"
            "05 NUM -128\n"
            "06 NUM -2"
        )
        ssem = Ssem(file=self._temp_file(program))
        ssem.breakpoints.append(WordValue(16, 128, SsemModel.word_length))

        ssem.stop_flag = False  # Simulate a running machine
        ssem.instruction_cycle()  # 01 LDN 05
        ssem.instruction_cycle()  # 02 STO 16

        self.assertEqual(sign_extend(ssem.store[16], SsemModel.word_length), 128, "The store was written")
        self.assertTrue(ssem.stop_flag, "The breakpoint paused the machine")
        self.assertEqual(ssem.last_instruction, "02 STO 16")

    def test_breakpoint_stays_armed_without_retriggering(self):
        """Resuming does not pause again while the condition still holds"""
        # LDN 05: A = 128, STO 16: word 16 = 128, JRP 06: jump back to 01
        program = (
            "00 NUM 0\n"
            "01 LDN 05\n"
            "02 STO 16\n"
            "03 JRP 06\n"
            "04 NUM 0\n"
            "05 NUM -128\n"
            "06 NUM -2"
        )
        ssem = Ssem(file=self._temp_file(program))
        ssem.breakpoints.append(WordValue(16, 128, SsemModel.word_length))

        ssem.stop_flag = False
        ssem.instruction_cycle()  # 01 LDN 05
        ssem.instruction_cycle()  # 02 STO 16: the breakpoint pauses the machine
        self.assertTrue(ssem.stop_flag)

        # Resuming: the machine loops, writing 128 again to word 16, which
        # never left its value: the breakpoint must not pause it again
        ssem.stop_flag = False
        for _ in range(9):
            ssem.instruction_cycle()

        self.assertFalse(ssem.stop_flag, "No new pause while the condition still holds")
        self.assertGreater(ssem.last_cycle, 10, "The machine kept running")

    def test_breakpoint_set_on_a_true_condition(self):
        """A breakpoint whose condition already holds pauses on the next cycle"""
        self.ssem.store[16] = b(128, SsemModel.word_length)
        self.ssem.store[1] = self._instruction("STP", 0)
        self.ssem.breakpoints.append(WordValue(16, 128, SsemModel.word_length))

        self.ssem.stop_flag = False
        self.ssem.instruction_cycle()  # 01 STP

        self.assertTrue(self.ssem.stop_flag, "The breakpoint paused the machine")
        self.assertEqual(sign_extend(self.ssem.store[16], SsemModel.word_length), 128)

    def test_ci_breakpoint_pauses_when_ci_arrives(self):
        """A CI breakpoint pauses the machine when CI takes the given value

        CI is read at the end of a cycle, where it holds the address of
        the word just executed: the pause happens after that word ran,
        and resuming executes the word after it.
        """
        program = (
            "00 NUM 0\n"
            "01 LDN 05\n"
            "02 STO 06\n"
            "03 STP\n"
            "04 NUM 0\n"
            "05 NUM -128\n"
            "06 NUM 0\n"
        )
        ssem = Ssem(file=self._temp_file(program))
        ssem.breakpoints.append(CiValue(2))

        ssem.stop_flag = False  # Simulate a running machine
        ssem.instruction_cycle()  # 01 LDN 05
        ssem.instruction_cycle()  # 02 STO 06

        self.assertTrue(ssem.stop_flag, "The breakpoint paused the machine")
        self.assertEqual(sign_extend(ssem.ci, SsemModel.word_length), 2, "CI points at word 2")
        self.assertEqual(ssem.last_instruction, "02 STO 06", "The pause follows the execution of word 2")

        # The STP at word 3 has not run: resuming executes it
        ssem.stop_flag = False
        ssem.instruction_cycle()  # 03 STP
        self.assertEqual(ssem.last_instruction, "03 STP 00")
