
from abc import ABC, abstractmethod
from threading import Event
from typing import Optional


class MachineRuntimeError(Exception):
    pass


class AbstractMachine(ABC):
    """Base class for a machine simulator
    """

    @abstractmethod
    def instruction_cycle(self):
        """Perform a full instruction cycle (fetch, decode, execute)
        """
        ...

    @abstractmethod
    def start(self, stop_event: Optional[Event] = None):
        """Start the machine until stop condition is met or stop is requested externally
        """
        ...

    @abstractmethod
    def clear_memory(self):
        """Reset the main memory"""
        ...

    @abstractmethod
    def clear_state(self):
        """Reset the program counter and registries"""
        ...

