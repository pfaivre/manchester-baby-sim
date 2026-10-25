from src.core.words import b, sign_extend


class Breakpoint:
    """A condition that pauses the machine when it becomes true

    Breakpoints trigger on a rising edge: the machine pauses when the
    condition turns true, and the breakpoint stays armed — it triggers
    again only after the condition has turned false at least once. A
    level-triggered breakpoint would pause the machine again right after
    every resume, since its condition would still hold. As a corollary, a
    breakpoint set on a condition that already holds pauses the machine on
    its next instruction cycle.

    The machine checks its breakpoints after every instruction cycle; the
    condition classes only assume the machine exposes a Store as
    `machine.store` and its program counter as `machine.ci`.
    """

    def __init__(self):
        self._was_met = False

    def is_met(self, machine) -> bool:
        """Tell whether the machine must pause on this cycle, updating the edge state"""
        met = self._check(machine)
        triggered = met and not self._was_met
        self._was_met = met
        return triggered

    def _check(self, machine) -> bool:
        """Tell whether the condition currently holds"""
        raise NotImplementedError

    def description(self) -> str:
        """Human-readable condition, shown in the interface"""
        raise NotImplementedError


class WordValue(Breakpoint):
    """Breakpoint met while the word at an address holds a given value

    The value is given as a signed number and stored as a raw word.
    """

    def __init__(self, address: int, value: int, word_length: int):
        super().__init__()
        self.address = address
        self.value = b(value, word_length)  # Raises IndexError when the value does not fit
        self._word_length = word_length

    def _check(self, machine) -> bool:
        return machine.store[self.address] == self.value

    def description(self) -> str:
        return f"WORD {self.address:02d} = {sign_extend(self.value, self._word_length)}"

    def __eq__(self, other):
        return (
            isinstance(other, WordValue)
            and other.address == self.address
            and other.value == self.value
        )


class CiValue(Breakpoint):
    """Breakpoint met while the program counter (CI) holds a given value

    CI is read at the end of each instruction cycle, where it holds the
    address of the word the cycle just executed — or the target a jump
    (JMP, JRP, CMP) wrote into it: the machine pauses with its pointer on
    the given word, and the next cycle executes the word after it (the
    SSEM increments CI before fetching every instruction).
    """

    def __init__(self, address: int):
        super().__init__()
        self.address = address

    def _check(self, machine) -> bool:
        return machine.ci == self.address

    def description(self) -> str:
        return f"CI = {self.address:02d}"

    def __eq__(self, other):
        return isinstance(other, CiValue) and other.address == self.address
