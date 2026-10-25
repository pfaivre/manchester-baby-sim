from pathlib import Path
from threading import Event
from time import perf_counter, sleep

from src.core.store import Store
from src.core.words import sign_extend
from src.machines.abstractmachine import AbstractMachine, MachineRuntimeError
from src.machines.assembler import Assembler
from src.machines.ssemmodel import SsemModel

# Instructions are grouped in batches lasting at least this long, so the
# overshoot of sleep() (in the same order of magnitude as the period of a
# single instruction) is amortized over the batch
BATCH_DURATION = 0.02  # seconds


class Ssem(AbstractMachine):
    """Simulator for the original Small-Scale Experimental Machine (SSEM), a.k.a. Manchester Baby built in 1948

    It features:
        - A store of 32 words of 32 bits each (1024 bits total)
        - A program counter (CI) of 32 bits
        - An accumulator (A) of 32 bits
        - 7 instructions:
            - JMP S: Jump to the address specified at the address S
            - JRP S: Jump to the instruction at address CI + value of S
            - LDN S: Load the negative value of address S to the accumulator
            - STO S: Stores the value of the accumulator to address S
            - SUB S: Substract the value in address S from the accumulator
            - CMP: Skip next instruction if the accumulator contains a negative value
            - STP: Stop the execution
        - Address size: 5 bits
        - Typically performs at around 700 instructions per seconds

    Words are plain ints (bit 0 = least significant bit, two's complement for
    negative values); see src/core/words.py.
    """

    def __init__(self, file: Path | None = None):
        self.model = SsemModel()
        self.speed = self.model.typical_speed
        self.assembler = Assembler(model=self.model)

        self.store = Store(self.model.word_length, self.model.word_count)
        self.ci = 0
        self.a = 0
        self.stop_flag = True

        self._last_cycle = 0

        # Values derived from the model, kept flat in the run loop's hot path
        self._word_length = self.model.word_length
        self._word_mask = (1 << self._word_length) - 1
        self._word_size = 1 << self._word_length
        self._sign_bit = 1 << (self._word_length - 1)
        self._word_count = self.model.word_count
        self._opcode_shift = self.model.opcode_start
        self._opcode_mask = (1 << self.model.opcode_length) - 1
        self._address_mask = (1 << self.model.address_length) - 1

        # Dispatch table: one handler per opcode of the model, in the run loop
        # where matching on the mnemonic would cost an Enum construction per
        # cycle. Opcodes with no handler (gaps in the model) raise at run time.
        handlers = {
            "JMP": self._exec_jmp,
            "JRP": self._exec_jrp,
            "LDN": self._exec_ldn,
            "STO": self._exec_sto,
            "SUB": self._exec_sub,
            "SUB2": self._exec_sub,
            "CMP": self._exec_cmp,
            "STP": self._exec_stp,
        }
        self._dispatch = []
        self._mnemonic_names = []
        for opcode in range(1 << self.model.opcode_length):
            try:
                mnemonic = self.model.Mnemonic(opcode)
            except ValueError:
                self._dispatch.append(None)
                self._mnemonic_names.append(str(opcode))
                continue
            self._dispatch.append(handlers.get(mnemonic.name))
            self._mnemonic_names.append(mnemonic.name)

        # Last executed instruction, kept as raw values: building the display
        # string on every cycle would dominate the run loop
        self._last_address = 0
        self._last_opcode = None
        self._last_data = 0

        if file:
            self.assembler.load_file(file, self.store)

    @property
    def last_cycle(self):
        return self._last_cycle

    @property
    def last_instruction(self) -> str:
        if self._last_opcode is None:
            return ""
        return f"{self._last_address:02d} {self._mnemonic_names[self._last_opcode]} {self._last_data:02d}"

    @property
    def is_running(self):
        return not self.stop_flag

    def instruction_cycle(self) -> str:
        """Performs one instruction cycle

        It first increments the program counter, then decodes the next instruction and executes it.
        """
        self._cycle()
        return self.last_instruction

    def _cycle(self):
        """Fetch, decode and execute one instruction: the machine's hot path

        Kept separate from instruction_cycle() so the run loop can execute
        batches of cycles without building the display string each time.
        """
        # Fetch: the program counter loops back to the beginning when it
        # exceeds the store
        ci = (self.ci + 1) % self._word_count
        self.ci = ci
        word = self.store[ci]

        # Decode: e.g. on the SSEM, bits 0-4 hold the operand and bits 13-15
        # the opcode
        opcode = (word >> self._opcode_shift) & self._opcode_mask
        data = word & self._address_mask

        # Execute
        handler = self._dispatch[opcode]
        if handler is None:
            raise MachineRuntimeError(f"Unsupported command '{opcode}'")

        try:
            handler(data)
        except IndexError:
            raise MachineRuntimeError("Error: Out of bound memory access")

        self._last_address = ci
        self._last_opcode = opcode
        self._last_data = data
        self._last_cycle += 1

    def _execute(self, command, data: int):
        """Execute an instruction from its mnemonic

        The run loop dispatches directly on the opcode; this is the mnemonic
        level entry point, used to execute an isolated instruction.
        """
        if command.value is None or command.value >= len(self._dispatch) or self._dispatch[command.value] is None:
            raise MachineRuntimeError(f"Unsupported command '{command.value}'")

        try:
            self._dispatch[command.value](data)
        except IndexError:
            raise MachineRuntimeError("Error: Out of bound memory access")

    def _exec_jmp(self, data: int):
        """JMP S: jump to the address held at the address S (indirect jump)"""
        self.ci = self.store[data]

    def _exec_jrp(self, data: int):
        """JRP S: jump to the instruction at address CI + value of S"""
        self.ci = (self.store[data] + self.ci) & self._word_mask

    def _exec_ldn(self, data: int):
        """LDN S: load the negated value of the address S to the accumulator"""
        self.a = -sign_extend(self.store[data], self._word_length) & self._word_mask

    def _exec_sto(self, data: int):
        """STO S: store the value of the accumulator to the address S"""
        self.store[data] = self.a

    def _exec_sub(self, data: int):
        """SUB S: subtract the value in address S from the accumulator"""
        s = self.store[data]
        if s & self._sign_bit:
            s -= self._word_size

        self.a = (self.a - s) & self._word_mask

    def _exec_cmp(self, data: int):
        """CMP: skip the next instruction if the accumulator is negative"""
        if self.a & self._sign_bit:
            self.ci = (self.ci + 1) & self._word_mask

    def _exec_stp(self, data: int):
        """STP: stop the execution"""
        self.stop_flag = True

    def start(self, stop_event: Event, stopped: bool = False):
        """Start the machine until stop instruction is met
        """
        self.stop_flag = stopped

        while not stop_event.is_set():
            next_deadline = perf_counter()

            while not self.stop_flag:
                period = 1 / self.speed
                batch_size = max(1, int(BATCH_DURATION / period))
                deadline = next_deadline + batch_size * period

                cycle = self._cycle
                stop_requested = stop_event.is_set
                for _ in range(batch_size):
                    cycle()

                    if stop_requested():
                        return
                    if self.stop_flag:
                        break

                if self.stop_flag:
                    break

                # Wait until the absolute deadline of the batch, so that
                # sleep() overshoot does not accumulate over time
                now = perf_counter()
                if deadline < now:
                    # Execution fell behind schedule (e.g. speed set beyond
                    # what the machine can deliver): resynchronize instead
                    # of drifting further or catching up in a burst
                    next_deadline = now + batch_size * period
                else:
                    sleep(deadline - now)
                    next_deadline = deadline

            sleep(0.1)

    def clear_memory(self):
        """Reset the store to zero"""
        self.store.clear()

    def clear_state(self):
        """Reset the program counter and the accumulator to zero"""
        self.ci = 0
        self.a = 0
