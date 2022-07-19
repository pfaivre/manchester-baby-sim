
from abc import ABC, abstractmethod


class AbstractMachine(ABC):
    """Base class for a machine simulator
    """

    @abstractmethod
    def instruction_cycle(self):
        """Perform a full instruction cycle (fetch, decode, execute)
        """
        ...

    @abstractmethod
    def start(self):
        """Start the machine until stop condition is met
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

